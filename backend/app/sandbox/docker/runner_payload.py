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
}


class SecurityError(Exception):
    pass


def validate(code: str) -> list[dict]:
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return [{"rule": "syntax", "message": exc.msg, "line": exc.lineno, "symbol": exc.text}]
    violations = []
    for node in ast.walk(tree):
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

_original_import = builtins.__import__
_original_open = builtins.open
_original_compile = builtins.compile
builtins.__import__ = restricted_import
builtins.open = blocked_call("open")
builtins.input = blocked_call("input")
builtins.eval = blocked_call("eval")
builtins.compile = blocked_call("compile")
for name in ("breakpoint", "getattr", "setattr", "delattr", "globals", "locals", "vars"):
    if hasattr(builtins, name):
        setattr(builtins, name, blocked_call(name))

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
        globals_dict = {"__name__": "__main__", "__builtins__": builtins.__dict__}
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
