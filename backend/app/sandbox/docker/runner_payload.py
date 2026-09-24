from __future__ import annotations

import ast
import builtins
import contextlib
import io
import json
import os
import resource
import signal
import time
import traceback


DENIED_IMPORT_ROOTS = {
    "asyncio",
    "builtins",
    "concurrent",
    "ctypes",
    "ftplib",
    "http",
    "importlib",
    "multiprocessing",
    "os",
    "pathlib",
    "requests",
    "resource",
    "shutil",
    "signal",
    "socket",
    "ssl",
    "subprocess",
    "sys",
    "threading",
    "urllib",
}
DENIED_CALLS = {
    "__import__",
    "breakpoint",
    "compile",
    "delattr",
    "eval",
    "exec",
    "getattr",
    "globals",
    "input",
    "locals",
    "open",
    "setattr",
    "vars",
}
DENIED_ATTRIBUTES = {
    ("builtins", "__import__"),
    ("builtins", "compile"),
    ("builtins", "eval"),
    ("builtins", "exec"),
    ("builtins", "open"),
    ("multiprocessing", "Process"),
    ("os", "execv"),
    ("os", "execve"),
    ("os", "fork"),
    ("os", "popen"),
    ("os", "spawn"),
    ("os", "system"),
    ("pathlib", "Path"),
    ("shutil", "rmtree"),
    ("socket", "socket"),
    ("subprocess", "Popen"),
    ("subprocess", "run"),
    ("io", "open"),
    ("os", "chdir"),
    ("os", "chmod"),
    ("os", "chown"),
    ("os", "kill"),
    ("os", "remove"),
    ("os", "unlink"),
    ("os", "rmdir"),
    ("os", "rename"),
}


class SecurityError(Exception):
    pass


def _recorrer_arbol(tree: ast.AST):
    """Reimplementación mínima de `ast.walk()` — MISMO problema que el
    de `compile` (docstring de `validate()` más abajo), un segundo caso
    real encontrado del mismo patrón, no uno nuevo ni distinto: la
    implementación real de `ast.walk()` (vía `ast.iter_child_nodes` →
    `ast.iter_fields`) llama a `getattr(nodo, campo)` — resuelto contra
    `builtins` en cada llamada, igual que `compile` — y `builtins.
    getattr` también queda bloqueado (más abajo) antes de invocar
    `validate()`. Evita depender del stdlib `ast.walk` por completo:
    usa `_original_getattr` (capturada más abajo, mismo patrón que
    `_original_compile`/`_original_setattr`) para leer los campos de
    cada nodo — nunca expuesta al código del estudiante, que sigue
    viendo `builtins.getattr` bloqueado exactamente igual que antes."""
    pendientes = [tree]
    while pendientes:
        nodo = pendientes.pop()
        yield nodo
        for campo in nodo._fields:
            valor = _original_getattr(nodo, campo, None)
            if isinstance(valor, ast.AST):
                pendientes.append(valor)
            elif isinstance(valor, list):
                pendientes.extend(v for v in valor if isinstance(v, ast.AST))


def validate(code: str) -> list[dict]:
    try:
        # Bug real corregido (verificado con evidencia ejecutada, Podman
        # real): `ast.parse()` es, literalmente,
        # `compile(source, filename, mode, flags=ast.PyCF_ONLY_AST)` —
        # resuelve `compile` contra `builtins` en CADA llamada, dinámicamente,
        # no contra una referencia capturada al importar `ast`. Como
        # `builtins.compile` ya queda bloqueado (más abajo, antes de
        # invocar `validate()`) para el código del ESTUDIANTE, la propia
        # validación interna del sandbox —que corre ANTES de ejecutar ese
        # código, para poder rechazarlo— se autobloqueaba: la
        # infraestructura del sandbox nunca podía analizar nada, ni
        # siquiera código trivial. Fix mínimo: usar `_original_compile`
        # (ya capturada más abajo — MISMA referencia que ya usa la
        # ejecución real del código del estudiante en la línea del
        # `exec()`, mismo patrón que `_original_open`/`_original_setattr`)
        # en vez de `ast.parse()`, que evita por completo depender del
        # `builtins.compile` ya bloqueado. El código del estudiante NUNCA
        # ve `_original_compile` — vive en el namespace de este módulo,
        # inaccesible desde `globals_dict` (un diccionario nuevo y
        # aislado que el `exec()` de más abajo usa para el estudiante) —
        # y `builtins.compile` sigue siendo la versión bloqueada para
        # cualquier llamada a `compile(...)` que el código del estudiante
        # intente, exactamente igual que antes.
        tree = _original_compile(code, "<student_code>", "exec", ast.PyCF_ONLY_AST)
    except SyntaxError as exc:
        return [{"rule": "syntax", "message": exc.msg, "line": exc.lineno, "symbol": exc.text}]
    violations = []
    for node in _recorrer_arbol(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".", 1)[0]
                if root in DENIED_IMPORT_ROOTS:
                    violations.append({"rule": "restricted_import", "message": f"Import '{root}' is not allowed", "line": node.lineno, "symbol": root})
        elif isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".", 1)[0]
            if root in DENIED_IMPORT_ROOTS:
                violations.append({"rule": "restricted_import", "message": f"Import '{root}' is not allowed", "line": node.lineno, "symbol": root})
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in DENIED_CALLS:
                violations.append({"rule": "restricted_call", "message": f"Call '{node.func.id}' is not allowed", "line": node.lineno, "symbol": node.func.id})
            dotted = dotted_call(node.func)
            if dotted:
                root, attr = dotted
                if (root, attr) in DENIED_ATTRIBUTES or root in DENIED_IMPORT_ROOTS:
                    symbol = f"{root}.{attr}"
                    violations.append({"rule": "restricted_call", "message": f"Call '{symbol}' is not allowed", "line": node.lineno, "symbol": symbol})
    return violations


def dotted_call(func: ast.expr) -> tuple[str, str] | None:
    if not isinstance(func, ast.Attribute):
        return None
    parts = [func.attr]
    current = func.value
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        parts.append(current.id)
    if len(parts) < 2:
        return None
    parts.reverse()
    return parts[0], parts[-1]


def restricted_import(name, globals=None, locals=None, fromlist=(), level=0):
    root = name.split(".", 1)[0]
    if root in DENIED_IMPORT_ROOTS:
        raise SecurityError(f"Import '{root}' is blocked in the educational sandbox")
    return _original_import(name, globals, locals, fromlist, level)


def blocked_call(name):
    def _blocked(*args, **kwargs):
        raise SecurityError(f"Call '{name}' is blocked in the educational sandbox")
    return _blocked


def memory_mb() -> float:
    usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return round(usage / 1024, 3)


def emit(payload: dict) -> None:
    print("===SANDBOX_RESULT===" + json.dumps(payload, ensure_ascii=False), flush=True)


def timeout_handler(signum, frame):
    raise TimeoutError("Sandbox execution timed out")


timeout = int(os.environ.get("SANDBOX_TIMEOUT", "10"))
memory_limit_mb = int(os.environ.get("SANDBOX_MEMORY_MB", "512"))
stdout_limit = int(os.environ.get("SANDBOX_STDOUT_LIMIT", "20000"))
stderr_limit = int(os.environ.get("SANDBOX_STDERR_LIMIT", "20000"))
code_path = "/sandbox/input/code.py"
tests_path = "/sandbox/input/tests.py"
stdin_path = "/sandbox/input/stdin.txt"

# Bug real corregido (verificado con evidencia ejecutada, Podman real):
# las rondas anteriores parcheaban `builtins.compile`/`builtins.getattr`/
# `builtins.setattr` IN-PLACE, mutando el módulo `builtins` real del
# proceso — compartido por TODO el intérprete, no solo por el código del
# estudiante. Cada vez que aparecía infraestructura interna que también
# dependía de uno de esos nombres (el propio `validate()` vía
# `ast.parse`→`compile`, el recorrido AST vía `ast.walk`→`getattr`, y
# ahora `contextlib.redirect_stdout().__enter__()` vía
# `getattr(sys, "stdout")`, y hasta `traceback.format_exc()` — que
# también usa `getattr` internamente y por eso el manejo de la propia
# `SecurityError` volvía a fallar en cascada) se autobloqueaba, porque
# no hay forma de distinguir "esto lo pidió el estudiante" de "esto lo
# pidió el runtime del sandbox" una vez que `builtins` global ya no
# tiene la función real. Parchear un builtin más (`redirect_stdout`)
# habría sido el cuarto caso del mismo patrón, no uno distinto.
#
# Fix estructural (no otro parche puntual): el módulo `builtins` real
# del proceso NUNCA se modifica. En su lugar se construye un dict de
# builtins RESTRINGIDO, exclusivo para el código del estudiante, y se
# instala únicamente como `globals_dict["__builtins__"]` del `exec()`
# más abajo — nunca como `builtins.__dict__`. `import`/`compile`/
# `getattr`/`setattr`/etc. dentro del código del estudiante resuelven
# esos nombres contra los builtins de SU frame (`globals_dict
# ["__builtins__"]`, fijado por `exec()`), no contra el módulo real —
# es la misma resolución dinámica que causó los tres bugs anteriores,
# pero usada aquí a favor: la infraestructura del sandbox (este
# módulo, `contextlib`, `traceback`, `ast`, etc.) sigue viendo el
# `builtins` real, intacto, exactamente como en cualquier proceso
# Python normal.
_original_import = builtins.__import__
_original_open = builtins.open
_original_compile = builtins.compile
_original_getattr = builtins.getattr  # usada solo por _recorrer_arbol() — ver su docstring


def _build_student_builtins() -> dict:
    """Namespace de builtins restringido para el `exec()` del código del
    estudiante — una copia de `builtins.__dict__`, nunca el módulo real.
    Ninguna referencia privilegiada (`_original_*`) se incluye aquí: el
    estudiante solo ve las versiones bloqueadas."""
    student_builtins = dict(builtins.__dict__)
    student_builtins["__import__"] = restricted_import
    student_builtins["open"] = blocked_call("open")
    student_builtins["input"] = blocked_call("input")
    student_builtins["eval"] = blocked_call("eval")
    student_builtins["compile"] = blocked_call("compile")
    for name in ("breakpoint", "getattr", "setattr", "delattr", "globals", "locals", "vars"):
        if name in student_builtins:
            student_builtins[name] = blocked_call(name)
    return student_builtins


# `io.open` (distinto de `builtins.open`) se mantiene bloqueado de forma
# directa e incondicional: es el único punto por el que el código del
# estudiante podría recuperar una referencia utilizable a `open` sin
# pasar por el nombre libre `open` (p. ej. `from io import open as o`,
# que el chequeo estático de `validate()` no rastrea por alias). Ninguna
# infraestructura interna de este módulo llama a `io.open`, así que este
# parche puntual —a diferencia de los de `builtins`— no rompe nada
# propio del runtime del sandbox.
import io as _io
_io.open = blocked_call("open")

try:
    memory_bytes = memory_limit_mb * 1024 * 1024
    resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))
except (ValueError, OSError):
    pass

start = time.perf_counter()
stdout_buffer = io.StringIO()
stderr_buffer = io.StringIO()
trace = ""
status = "success"
success = True

try:
    # The runner itself reads mounted input before user code executes; user code cannot call open.
    with _original_open(code_path, "r", encoding="utf-8") as fh:
        user_code = fh.read()
    with _original_open(tests_path, "r", encoding="utf-8") as fh:
        test_code = fh.read()
    combined = user_code + ("\n\n" + test_code if test_code.strip() else "")
    violations = validate(combined)
    if violations:
        status = "security_violation"
        success = False
        trace = json.dumps(violations, ensure_ascii=False)
    else:
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout)
        globals_dict = {"__name__": "__main__", "__builtins__": _build_student_builtins()}
        with contextlib.redirect_stdout(stdout_buffer), contextlib.redirect_stderr(stderr_buffer):
            exec(_original_compile(combined, "student_code.py", "exec"), globals_dict, globals_dict)
        signal.alarm(0)
except TimeoutError:
    status = "timeout"
    success = False
    trace = traceback.format_exc()
except MemoryError:
    status = "memory_limit"
    success = False
    trace = traceback.format_exc()
except BaseException:
    status = "runtime_error"
    success = False
    trace = traceback.format_exc()

emit(
    {
        "status": status,
        "success": success,
        "stdout": stdout_buffer.getvalue()[:stdout_limit],
        "stderr": stderr_buffer.getvalue()[:stderr_limit],
        "traceback": trace,
        "execution_time_ms": round((time.perf_counter() - start) * 1000, 2),
        "memory_usage_mb": memory_mb(),
        "metrics": {
            "timeout_seconds": timeout,
            "memory_limit_mb": memory_limit_mb,
            "stdout_truncated": len(stdout_buffer.getvalue()) > stdout_limit,
            "stderr_truncated": len(stderr_buffer.getvalue()) > stderr_limit,
        },
    }
)
