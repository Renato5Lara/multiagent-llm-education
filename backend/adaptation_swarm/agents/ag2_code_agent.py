"""AG2 — Code-Agent (asesoría §3.3.1): extrae, valida y formatea fragmentos de código ejecutable
según el nivel algorítmico solicitado.

Dos modos, ambos reales:
  · GENERACIÓN (offline, construye la biblioteca M1): el LLM redacta cada variante de código a
    partir del ConceptAnchor y de la ESPECIFICACIÓN DE COMPORTAMIENTO (firmas y asserts de
    referencia del catálogo); el código se valida EJECUTÁNDOLO en el sandbox contra esos asserts.
    No se copia código existente: se rechaza cualquier salida estructuralmente idéntica a la de
    referencia. Lenguaje: Python (C++ no implementado — ver README).
  · REALIZACIÓN (online, por el bus): CODE_REQUEST → selecciona la variante de la biblioteca
    versionada y responde CODE_READY con hash y trazabilidad. Si falta → ERROR explícito.

Variantes (costo/profundidad crecientes): 0 mínima · 1 explicada · 2 con casos límite y ejemplo de uso.
"""

from __future__ import annotations

import ast
import re
import time
from dataclasses import dataclass
from typing import Any

from app.sandbox.runner import SandboxRunner
from app.sandbox.schemas import SandboxRequest, SandboxStatus

from adaptation_swarm.agents.base import SwarmAgent
from adaptation_swarm.config import SETTINGS
from adaptation_swarm.multimodal.anchor import ConceptAnchor
from adaptation_swarm.multimodal.library import LibraryStore
from adaptation_swarm.multimodal.llm import LLMClient
from adaptation_swarm.multimodal.semantic import code_covers_concept, code_hygiene, required_constructs
from adaptation_swarm.sandbox_cpp import CppSandbox, policy_violations
from adaptation_swarm.schemas.errors import GenerationError, SwarmError
from adaptation_swarm.schemas.messages import AgentId, BusMessage, MessageType

CPP_PROMPT_VERSION = "ag2-cpp-v1"
PROMPT_VERSION = "ag2-code-v3"   # v3: exige higiene (sin asserts/llamadas en el módulo) y cobertura de la construcción del concepto
_PROMPT_HISTORY = "ag2-code-v2"   # v2: la especificación añade descripción del comportamiento y estado global inicial
MAX_ATTEMPTS = 6
STRONG_MODEL = "gpt-4o"          # respaldo: los últimos intentos usan un modelo más capaz (queda registrado en `provider.model`)
STRONG_FROM_ATTEMPT = 4

_SYSTEM = (
    "Eres Code-Agent, un agente que escribe código Python educativo, correcto y ejecutable, para un "
    "curso universitario de Fundamentos de la Programación. Devuelve ÚNICAMENTE el código Python, "
    "sin markdown, sin explicaciones fuera del código, sin `input()`, sin importar módulos. Solo definiciones "
    "y el estado inicial a nivel de módulo que se indique: NO llames funciones, NO imprimas y NO escribas `assert` a nivel de módulo."
)

_VARIANT_RULES = {
    0: "Implementación MÍNIMA y compacta: solo las funciones requeridas, SIN comentarios y SIN docstrings.",
    1: ("Implementación EXPLICADA: cada función lleva un docstring breve en español y comentarios de una "
        "línea (con #) que explican los pasos clave. Sin funciones adicionales."),
    2: ("Implementación PROFUNDA: docstrings en español, comentarios de cada paso clave (con #), manejo "
        "explícito de casos límite (entrada vacía, cero o valores extremos) y UNA función adicional "
        "`ejemplo_uso()` que ilustra el uso con `print`. No la invoques a nivel de módulo."),
}

_FENCE = re.compile(r"```(?:python|py)?\s*\n(.*?)```", re.DOTALL)


def extract_code(raw: str) -> str:
    m = _FENCE.search(raw)
    return (m.group(1) if m else raw).strip("\n") + "\n"


def _signatures(reference_code: str) -> list[str]:
    tree = ast.parse(reference_code)
    return [f"def {n.name}({ast.unparse(n.args)})" for n in tree.body if isinstance(n, ast.FunctionDef)]


def verbose_tests(tests: str) -> str:
    """Reescribe los asserts de referencia para que el sandbox informe CUÁL falló y qué valor se obtuvo (mismo criterio: todos
    deben cumplirse). Sirve de retroalimentación precisa para el agente; la semántica de aprobación no cambia."""
    tree = ast.parse(tests)
    out = ["_fails = []"]
    for n in tree.body:
        if isinstance(n, ast.Assert):
            src = ast.unparse(n.test)
            got = ast.unparse(n.test.left) if isinstance(n.test, ast.Compare) else "None"
            out.append(f"try:\n    assert {src}\nexcept AssertionError:\n    _fails.append(({src!r}, repr({got})))\n"
                       f"except Exception as _e:\n    _fails.append(({src!r}, type(_e).__name__ + ': ' + str(_e)))")
        else:
            out.append(ast.unparse(n))
    out.append("if _fails:\n    raise AssertionError('; '.join(f'FALLA {a} (obtuvo {b})' for a, b in _fails))")
    return "\n".join(out) + "\n"


def _module_state(reference_code: str) -> list[str]:
    """Estado a nivel de módulo que los asserts suponen (p. ej. `contador_global = 0`): forma parte de la
    ESPECIFICACIÓN de comportamiento (nombre y valor inicial), no de la implementación."""
    tree = ast.parse(reference_code)
    return [ast.unparse(n) for n in tree.body if isinstance(n, ast.Assign)]


def _structure(code: str) -> str:
    """AST sin docstrings ni comentarios (para detectar copias del código de referencia)."""
    tree = ast.parse(code)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.Module)) and node.body and isinstance(node.body[0], ast.Expr) \
                and isinstance(getattr(node.body[0], "value", None), ast.Constant) \
                and isinstance(node.body[0].value.value, str):
            node.body = node.body[1:] or [ast.Pass()]
    return ast.dump(tree)


_CPP_SYSTEM = (
    "Eres Code-Agent. Traduces código Python educativo a C++17 correcto, idiomático y compilable con g++ -Wall -Wextra. "
    "Devuelve ÚNICAMENTE el archivo C++ (sin markdown ni explicaciones). Solo cabeceras estándar permitidas "
    "(iostream, vector, string, algorithm, cassert, cmath, numeric, map, set, unordered_map, sstream, utility, limits). "
    "Sin llamadas al sistema, sin archivos ni red.")
_CPP_VARIANT_RULES = {
    0: "MÍNIMO: solo las funciones y `main`; sin comentarios (como máximo UNO, si un valor centinela lo exige).",
    1: "EXPLICADO: comentarios de una línea (//) que expliquen el propósito y los pasos clave.",
    2: "PROFUNDO: comentarios, manejo de casos límite y UNA función adicional `ejemplo_uso()` que muestre el uso con std::cout "
       "(no la llames en los asserts).",
}
_CPP_FENCE = re.compile(r"```(?:cpp|c\+\+|cc)?\s*\n(.*?)```", re.DOTALL)


def _assert_macro_unsafe(cpp: str) -> bool:
    """`assert(expr)` es una MACRO: una coma fuera de paréntesis (p. ej. dentro de `{1, 2}`) parte sus argumentos.
    Solo `assert((expr))` (paréntesis dobles) es seguro cuando la expresión tiene llaves o comas de nivel superior."""
    for m in re.finditer(r"\bassert\s*\(", cpp):
        i = m.end()
        if cpp[i:i + 1] == "(":
            continue
        depth, brace = 1, 0
        for ch in cpp[i:]:
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    break
            elif ch == "{":
                brace += 1
            elif ch == "," and depth == 1:
                return True
        if brace:
            return True
    return False


def _extract_cpp(raw: str) -> str:
    m = _CPP_FENCE.search(raw)
    return (m.group(1) if m else raw).strip("\n") + "\n"


@dataclass(frozen=True)
class GeneratedCpp:
    code: str
    variant: int
    generation_ms: float
    attempts: int
    model: str
    tokens_total: int
    sandbox_status: str
    sandbox_ms: float
    warnings: int
    stdout: str


@dataclass(frozen=True)
class GeneratedCode:
    code: str
    variant: int
    generation_ms: float
    attempts: int
    model: str
    tokens_total: int
    sandbox_status: str
    sandbox_exec_ms: float
    metadata: dict[str, Any]


class CodeAgent(SwarmAgent):
    agent_id = AgentId.AG2

    def __init__(self, bus=None, store: LibraryStore | None = None, *, llm: LLMClient | None = None,
                 sandbox: SandboxRunner | None = None, consumer: str | None = None):
        super().__init__(bus, consumer)
        self.store = store
        self._llm = llm
        self._sandbox = sandbox

    @property
    def llm(self) -> LLMClient:
        if self._llm is None:
            self._llm = LLMClient()
        return self._llm

    @property
    def strong_llm(self) -> LLMClient:
        if getattr(self, "_strong", None) is None:
            self._strong = LLMClient(STRONG_MODEL)
        return self._strong

    @property
    def sandbox(self) -> SandboxRunner:
        if self._sandbox is None:
            self._sandbox = SandboxRunner(docker_bin=SETTINGS.sandbox_bin)
        return self._sandbox

    # ── validación ───────────────────────────────────────────────────────
    def check_variant_shape(self, code: str, variant: int) -> str | None:
        top_calls = [n for n in ast.parse(code).body if isinstance(n, ast.Expr) and isinstance(n.value, ast.Call)]
        if top_calls:
            return "no llames funciones a nivel de módulo (solo definiciones y estado inicial)"
        has_comment = "#" in code
        has_doc = '"""' in code or "'''" in code
        if variant == 0 and (has_comment or has_doc):
            return "la variante 0 no debe tener comentarios ni docstrings"
        if variant == 1 and not (has_comment or has_doc):
            return "la variante 1 requiere docstrings y comentarios"
        if variant == 2:
            if not (has_comment and has_doc):
                return "la variante 2 requiere docstrings y comentarios"
            if "def ejemplo_uso" not in code:
                return "la variante 2 requiere la función ejemplo_uso()"
        return None

    async def validate_in_sandbox(self, code: str, tests: str) -> tuple[str, float, str]:
        res = await self.sandbox.run(SandboxRequest(code=code, test_code=verbose_tests(tests), metadata={"agent": "AG2"}))
        detail = (res.stderr or res.traceback or "")
        if "AssertionError:" in detail:
            detail = detail[detail.rindex("AssertionError:"):]
        detail = detail[-400:]
        if res.violations:
            detail = "; ".join(f"{v.rule}: {v.message}" for v in res.violations)[:400]
        return res.status.value, res.execution_time_ms, detail

    # ── generación (offline) ─────────────────────────────────────────────
    async def generate_variant(
        self, anchor: ConceptAnchor, reference_code: str, reference_tests: str, variant: int,
        behavior_description: str = "",
    ) -> GeneratedCode:
        sigs = _signatures(reference_code)
        state = _module_state(reference_code)
        required = required_constructs(anchor)
        ref_structure = _structure(reference_code)
        feedback = ""
        tokens = 0
        t0 = time.perf_counter()
        identical_ok: tuple[str, Any, int] | None = None     # válido y validado, pero estructuralmente igual a la referencia
        for attempt in range(1, MAX_ATTEMPTS + 1):
            user = (
                f"CONCEPTO: {anchor.concept_title}\nOBJETIVO DE APRENDIZAJE: {anchor.learning_objective_title}\n"
                f"FUNCIONES REQUERIDAS (nombre y parámetros EXACTOS):\n" + "\n".join(f"- {s}" for s in sigs) + "\n"
                + (f"ESTADO A NIVEL DE MÓDULO (defínelo exactamente así, fuera de las funciones):\n" + "\n".join(state) + "\n" if state else "")
                + (f"DESCRIPCIÓN DEL COMPORTAMIENTO: {behavior_description}\n" if behavior_description else "")
                + (f"CONSTRUCCIONES OBLIGATORIAS (deben aparecer explícitamente en el código): {', '.join(sorted(required))}\n" if required else "")
                + f"COMPORTAMIENTO ESPERADO (tu código debe cumplir estos asserts):\n{reference_tests}\n"
                f"NIVEL: {_VARIANT_RULES[variant]}\n"
                "Escribe una implementación propia y devuélvela completa."
                + (f"\nCORRIGE: {feedback}" if feedback else "")
            )
            res = await (self.strong_llm if attempt >= STRONG_FROM_ATTEMPT else self.llm).complete(_SYSTEM, user)
            tokens += res.tokens_total
            code = extract_code(res.text)
            problem = None
            identical = False
            try:
                tree = ast.parse(code)
                defined = {n.name.lower() for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
                missing = [f for f in anchor.function_names if f not in defined]
                if missing:
                    problem = f"faltan las funciones {missing}"
                else:
                    problem = self.check_variant_shape(code, variant)
                    if problem is None:
                        hyg, cov = code_hygiene(code), code_covers_concept(anchor, code)
                        problem = next((v["message"] for r in (hyg, cov) for v in r.violations), None)
                    identical = _structure(code) == ref_structure
            except SyntaxError as exc:
                problem = f"error de sintaxis: {exc}"
            if problem is None:
                status, exec_ms, detail = await self.validate_in_sandbox(code, reference_tests)
                if status != SandboxStatus.SUCCESS.value:
                    problem = f"el sandbox rechazó el código ({status}): {detail}"
                elif identical and attempt < MAX_ATTEMPTS:
                    # Se pide una forma distinta; si el LLM (que NO recibe el código de referencia, solo firmas y
                    # asserts) vuelve a converger, se acepta al final marcándolo explícitamente.
                    identical_ok = (code, res, exec_ms)
                    problem = "es idéntico a la implementación de referencia; escribe una forma equivalente distinta"
                else:
                    return self._accepted(code, variant, t0, attempt, res, tokens, status, exec_ms, sigs, identical)
            feedback = problem
        if identical_ok is not None:      # convergió a la forma canónica en todos los intentos: es válido y verificado
            code, res, exec_ms = identical_ok
            return self._accepted(code, variant, t0, MAX_ATTEMPTS, res, tokens, SandboxStatus.SUCCESS.value, exec_ms, sigs, True)
        raise GenerationError(
            f"AG2 no logró código válido para {anchor.concept_title!r} variante {variant}: {feedback}")

    # ── C++ (contraparte real del código Python) ─────────────────────────
    @property
    def cpp_sandbox(self) -> CppSandbox:
        if getattr(self, "_cpp_sandbox", None) is None:
            self._cpp_sandbox = CppSandbox()
        return self._cpp_sandbox

    @staticmethod
    def check_cpp(cpp: str, anchor: ConceptAnchor, py_tests: str, variant: int) -> str | None:
        """Comprobaciones estáticas de un C++ generado (la compilación/ejecución las hace el sandbox)."""
        if "int main" not in cpp:
            return "falta `int main`"
        if re.search(r"^\s*(def |print\(|import )", cpp, re.M):
            return "parece Python, no C++"
        viol = policy_violations(cpp)
        if viol:
            return "; ".join(viol)
        for f in anchor.function_names:
            if not re.search(rf"\b{re.escape(f)}\s*\(", cpp, re.I):
                return f"falta la función {f}"
        n_py = sum(1 for n in ast.walk(ast.parse(py_tests)) if isinstance(n, ast.Assert))
        if cpp.count("assert(") + cpp.count("assert (") < n_py:
            return f"el `main` debe traducir los {n_py} asserts de Python con `assert(...)`"
        lits = {str(n.value) for n in ast.walk(ast.parse(py_tests)) if isinstance(n, ast.Constant)
                and isinstance(n.value, (int, str)) and not isinstance(n.value, bool)}
        missing = [l for l in lits if l not in cpp]
        if lits and len(missing) / len(lits) > 0.2:
            return f"los asserts no reflejan los valores esperados (faltan {sorted(missing)[:4]})"
        if "assert" in cpp and "<cassert>" not in cpp:
            return "usa assert sin `#include <cassert>`"
        if _assert_macro_unsafe(cpp):
            return "usa `assert((expresión))` con paréntesis dobles cuando la expresión tenga llaves o comas (macro assert)"
        n_comments = len(re.findall(r"//|/\*", cpp))
        if variant == 0 and n_comments > 1:
            return "la variante 0 admite como máximo un comentario (p. ej. en un valor centinela)"
        if variant >= 1 and n_comments < 2:
            return f"la variante {variant} requiere comentarios (al menos 2)"
        if variant == 2 and "ejemplo_uso" not in cpp:
            return "la variante 2 requiere la función ejemplo_uso()"
        return None

    async def generate_cpp(self, anchor: ConceptAnchor, python_code: str, py_tests: str, variant: int,
                           behavior_description: str = "") -> "GeneratedCpp":
        """Traduce a C++17 REAL la variante Python `variant` (mismo comportamiento y nivel) y la valida COMPILANDO Y
        EJECUTANDO en el sandbox de C++ (contenedor sin red). Reintenta con la retroalimentación del error."""
        feedback, tokens = "", 0
        t0 = time.perf_counter()
        for attempt in range(1, MAX_ATTEMPTS + 1):
            user = (
                f"CONCEPTO: {anchor.concept_title}\n"
                + (f"COMPORTAMIENTO: {behavior_description}\n" if behavior_description else "")
                + f"CÓDIGO PYTHON A TRADUCIR (mismo nivel y estructura):\n{python_code}\n"
                f"ASSERTS DE PYTHON QUE DEBES TRADUCIR A `assert(...)` EN `main` (mismos valores):\n{py_tests}\n"
                f"NIVEL: {_CPP_VARIANT_RULES[variant]}\n"
                "IMPORTANTE: incluye SIEMPRE `#include <cassert>` y escribe cada assert con paréntesis dobles, p. ej. `assert((f(3) == std::vector<int>{1, 2, 3}));`, para que las "
                "comas y llaves no rompan la macro. Si la función Python acepta valores de TIPOS distintos (int, float, str, bool…), modela el parámetro con "
                "`std::variant<int, double, std::string, bool>` y clasifícalo con `std::holds_alternative` (NO uses sobrecargas: un literal de texto "
                "elegiría la sobrecarga `bool`); en los asserts construye explícitamente `std::string(\"…\")` y `double`. "
                "Devuelve un archivo C++17 COMPLETO y compilable (cabeceras estándar, funciones con los MISMOS nombres, "
                "tipos adecuados como std::vector/std::string, y un `int main()` que ejecute los asserts e imprima OK)."
                + (f"\nCORRIGE: {feedback}" if feedback else ""))
            res = await (self.strong_llm if attempt >= STRONG_FROM_ATTEMPT else self.llm).complete(_CPP_SYSTEM, user)
            tokens += res.tokens_total
            cpp = _extract_cpp(res.text)
            problem = self.check_cpp(cpp, anchor, py_tests, variant)
            if problem is None:
                r = await self.cpp_sandbox.run(cpp)
                if r.success:
                    return GeneratedCpp(cpp, variant, (time.perf_counter() - t0) * 1000.0, attempt, res.model, tokens,
                                        r.status, r.total_ms, r.warnings, r.stdout.strip()[:80])
                problem = f"el sandbox de C++ dio {r.status}: {r.stderr[:300]}"
            feedback = problem
        raise GenerationError(f"AG2 no logró C++ válido para {anchor.concept_title!r} variante {variant}: {feedback}")

    def _accepted(self, code, variant, t0, attempts, res, tokens, status, exec_ms, sigs, identical) -> GeneratedCode:
        return GeneratedCode(
            code=code, variant=variant, generation_ms=(time.perf_counter() - t0) * 1000.0, attempts=attempts,
            model=res.model, tokens_total=tokens, sandbox_status=status, sandbox_exec_ms=exec_ms,
            metadata={"reference_used_as": "behavior_spec_only", "identical_to_reference": identical,
                      "independent_generation": True, "signatures": sigs})

    # ── realización (online, por el bus) ─────────────────────────────────
    async def handle(self, msg: BusMessage) -> list[BusMessage]:
        if msg.message_type is not MessageType.CODE_REQUEST:
            raise SwarmError(f"AG2 no maneja {msg.message_type.value}")
        if self.store is None:
            raise SwarmError("AG2 sin biblioteca: no puede realizar candidatos")
        concept_id, v = msg.payload["concept_id"], int(msg.payload["variant"])
        art = self.store.code(concept_id, v)
        e = art.entry
        cpp_art = self.store.cpp(concept_id, v)
        cpp = None if cpp_art is None else {
            "content_id": cpp_art.content_id, "sha256": cpp_art.sha256, "source": cpp_art.text,
            "validation": cpp_art.entry["validation"], "path": cpp_art.entry["path"]}
        return [self.reply(msg, MessageType.CODE_READY, {"cpp": cpp,
            "concept_id": concept_id, "variant": v, "content_id": e["content_id"], "sha256": e["sha256"],
            "code": art.text, "generation_ms": e["generation_ms"], "validation": e["validation"],
            "library_version": self.store.version, "agent": self.agent_id.value,
            "agent_version": self.version,
        })]
