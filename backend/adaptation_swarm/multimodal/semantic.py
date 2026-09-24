"""Validación SEMÁNTICA objetiva de los artefactos (sin LLM): estructura del código (AST) frente a lo que dicen
el texto y el diagrama. Detecta contradicciones básicas; NO sustituye ni modifica el gold/F1 (auxiliar).

Reglas (todas deterministas):
  T1  construcción principal: el concepto define una construcción (while, for, if, recursión, break/continue…);
      el código DEBE usarla y el texto DEBE mencionarla.
  T2  menciones sin respaldo: el texto nombra una construcción (bucle while, bucle for, condicional, recursión,
      break, continue) que el código NO usa (salvo frase de contraste: "a diferencia de", "en lugar de"…).
  T3  valor inicial: "desde/empieza en/inicia en X" debe coincidir con un valor inicial real de un bucle del código.
  T4  identificadores: el texto menciona las funciones del código.
  D1  el diagrama contiene un nodo por cada construcción de control y cada `return` del AST (ni faltantes ni
      extras) y el nombre de las funciones; cada etiqueta de sentencia corresponde a una sentencia real.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field

from adaptation_swarm.fitness.coher import diagram_labels
from adaptation_swarm.fitness.text_utils import identifiers, normalize
from adaptation_swarm.multimodal.anchor import ConceptAnchor
from adaptation_swarm.multimodal.flowchart import _label

# construcción → (qué mira en el AST, patrones que la mencionan en el texto (sin acentos, minúsculas))
CONSTRUCTS: dict[str, tuple[re.Pattern, re.Pattern]] = {
    "while": (re.compile(r"$^"), re.compile(r"\b(bucle while|while|ciclo while|bucle mientras|instruccion while)\b")),
    "for": (re.compile(r"$^"), re.compile(r"\b(bucle for|ciclo for|for|bucle para cada|instruccion for)\b")),
    "if": (re.compile(r"$^"), re.compile(r"\b(condicional|sentencia if|instruccion if|estructura condicional)\b")),
    "break": (re.compile(r"$^"), re.compile(r"\b(break)\b")),
    "continue": (re.compile(r"$^"), re.compile(r"\b(continue)\b")),
    "recursion": (re.compile(r"$^"), re.compile(r"\b(recursivid\w*|recursiv\w*|llamada recursiva)\b")),
}
_CONTRAST = re.compile(r"\b(a diferencia de|en lugar de|en vez de|no como|distinto de|frente a|comparado con)\b")
_START = re.compile(r"\b(?:desde|empieza en|inicia en|comienza en|parte de)\s+(cero|uno|dos|tres|\d+)\b")
_WORDNUM = {"cero": 0, "uno": 1, "dos": 2, "tres": 3}

# concepto (términos del ancla) → construcción que DEBE verse en código y texto
_CONCEPT_CONSTRUCT = [(re.compile(r"\bwhile\b"), "while"), (re.compile(r"\bfor\b"), "for"),
                      (re.compile(r"\bcondicional"), "if"), (re.compile(r"\brecursiv"), "recursion"),
                      (re.compile(r"\bbreak\b"), "break"), (re.compile(r"\bcontinue\b"), "continue")]
# Menciones AMPLIAS (T1: ¿el texto habla de la construcción?) frente a las ESTRICTAS de CONSTRUCTS (T2: ¿la afirma?)
_BROAD = {"if": re.compile(r"\b(condicional\w*|if|condicion|decision|se cumple|verdader\w*|falso)\b")}


def code_constructs(code: str) -> set[str]:
    tree = ast.parse(code)
    found: set[str] = set()
    fnames = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    for n in ast.walk(tree):
        if isinstance(n, ast.While):
            found.add("while")
        elif isinstance(n, ast.For):
            found.add("for")
        elif isinstance(n, ast.If):
            found.add("if")
        elif isinstance(n, ast.Break):
            found.add("break")
        elif isinstance(n, ast.Continue):
            found.add("continue")
        elif isinstance(n, ast.FunctionDef):
            for c in ast.walk(n):
                if isinstance(c, ast.Call) and isinstance(c.func, ast.Name) and c.func.id == n.name:
                    found.add("recursion")
    return found


def loop_start_values(code: str) -> set[int]:
    """Valores iniciales reales de los bucles: `range(a, …)` → a (0 por defecto); `while cond` → constante asignada a
    la variable de la condición justo antes del bucle."""
    tree = ast.parse(code)
    starts: set[int] = set()

    def const(node) -> int | None:
        return node.value if isinstance(node, ast.Constant) and isinstance(node.value, int) else None

    for fn in [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.Module))]:
        assigned: dict[str, int] = {}
        for st in fn.body:
            if isinstance(st, ast.Assign) and len(st.targets) == 1 and isinstance(st.targets[0], ast.Name):
                c = const(st.value)
                if c is not None:
                    assigned[st.targets[0].id] = c
            elif isinstance(st, ast.While):
                for nm in [n.id for n in ast.walk(st.test) if isinstance(n, ast.Name)]:
                    if nm in assigned:
                        starts.add(assigned[nm])
            elif isinstance(st, ast.For) and isinstance(st.iter, ast.Call) and getattr(st.iter.func, "id", "") == "range":
                a = st.iter.args
                starts.add(const(a[0]) if len(a) >= 2 and const(a[0]) is not None else 0)
    return starts


@dataclass
class SemanticReport:
    ok: bool = True
    violations: list[dict] = field(default_factory=list)
    checks: dict[str, bool] = field(default_factory=dict)

    def fail(self, rule: str, message: str) -> None:
        self.ok = False
        self.violations.append({"rule": rule, "message": message})
        self.checks[rule] = False

    def passed(self, rule: str) -> None:
        self.checks.setdefault(rule, True)

    def to_dict(self) -> dict:
        return {"ok": self.ok, "violations": self.violations, "checks": self.checks}


def _mentions(text_norm: str, construct: str, broad: bool = False) -> bool:
    pat = _BROAD.get(construct) if broad else None
    return bool((pat or CONSTRUCTS[construct][1]).search(text_norm))


def validate_text_against_code(anchor: ConceptAnchor, code: str, text: str) -> SemanticReport:
    rep = SemanticReport()
    used = code_constructs(code)
    tnorm = normalize(text)
    sentences = re.split(r"(?<=[.!?])\s+", tnorm)
    # T1
    title = normalize(anchor.concept_title)
    for pat, construct in _CONCEPT_CONSTRUCT:
        if pat.search(title) and construct:
            if construct not in used:
                rep.fail("T1", f"el concepto es «{anchor.concept_title}» pero el código no usa `{construct}`")
            elif not _mentions(tnorm, construct, broad=True):
                rep.fail("T1", f"el texto no menciona la construcción principal `{construct}`")
            else:
                rep.passed("T1")
    # T2
    for construct in CONSTRUCTS:
        if construct in used:
            continue
        for s in sentences:
            if _mentions(s, construct) and not _CONTRAST.search(s):
                rep.fail("T2", f"el texto menciona `{construct}` pero el código no lo usa")
                break
    rep.passed("T2")
    # T3
    starts = loop_start_values(code)
    for m in _START.finditer(tnorm):
        raw = m.group(1)
        val = _WORDNUM.get(raw, int(raw) if raw.isdigit() else None)
        if val is not None and starts and val not in starts:
            rep.fail("T3", f"el texto dice «{m.group(0)}» pero los bucles del código empiezan en {sorted(starts)}")
    rep.passed("T3")
    # T4
    idents = set(identifiers(text))
    missing = [f for f in anchor.function_names if f not in idents]
    if missing:
        rep.fail("T4", f"el texto no menciona las funciones {missing}")
    rep.passed("T4")
    return rep


def required_constructs(anchor: ConceptAnchor) -> set[str]:
    """Construcciones que el código DEBE usar según el concepto (p. ej. «Flujo de bucles (break/continue)» ⇒ break y continue)."""
    title = normalize(anchor.concept_title)
    return {c for pat, c in _CONCEPT_CONSTRUCT if pat.search(title) and c}


def code_hygiene(code: str) -> SemanticReport:
    """C1: el código entregable contiene definiciones y estado inicial, NO pruebas (`assert`), llamadas ni `print`
    a nivel de módulo (las pruebas viven aparte, en la validación del sandbox)."""
    rep = SemanticReport()
    tree = ast.parse(code)
    for n in tree.body:
        if isinstance(n, ast.Assert):
            rep.fail("C1", "el código incluye `assert` a nivel de módulo (las pruebas no forman parte del artefacto)")
        elif isinstance(n, ast.Expr) and isinstance(n.value, ast.Call):
            rep.fail("C1", "el código ejecuta una llamada a nivel de módulo")
    rep.passed("C1")
    return rep


def code_covers_concept(anchor: ConceptAnchor, code: str) -> SemanticReport:
    """C2: el código usa las construcciones que define el concepto."""
    rep = SemanticReport()
    used = code_constructs(code)
    for c in sorted(required_constructs(anchor)):
        if c not in used:
            rep.fail("C2", f"el concepto «{anchor.concept_title}» exige `{c}` y el código no lo usa")
    rep.passed("C2")
    return rep


def _expected_diagram_labels(code: str) -> tuple[set[str], dict[str, int]]:
    """Etiquetas de sentencia esperadas (como las produce el builder: `_label(ast.unparse(...))`) y conteo de
    construcciones de control/return del AST."""
    tree = ast.parse(code)
    labels: set[str] = set()
    counts = {"while": 0, "for": 0, "if": 0, "return": 0, "break": 0, "continue": 0, "def": 0}
    for n in ast.walk(tree):
        if isinstance(n, ast.While):
            counts["while"] += 1
            labels.add(_label(f"while {ast.unparse(n.test)}"))
        elif isinstance(n, ast.For):
            counts["for"] += 1
            labels.add(_label(f"for {ast.unparse(n.target)} in {ast.unparse(n.iter)}"))
        elif isinstance(n, ast.If):
            counts["if"] += 1
            labels.add(_label(ast.unparse(n.test), "?"))
        elif isinstance(n, ast.Return):
            counts["return"] += 1
            labels.add(_label("return " + (ast.unparse(n.value) if n.value else "")))
        elif isinstance(n, ast.Break):
            counts["break"] += 1
            labels.add("break")
        elif isinstance(n, ast.Continue):
            counts["continue"] += 1
            labels.add("continue")
        elif isinstance(n, ast.FunctionDef):
            counts["def"] += 1
            labels.add(_label(f"def {n.name}({ast.unparse(n.args)})"))
        elif isinstance(n, ast.Try):
            labels.add("try")
            for h in n.handlers:
                labels.add(_label(f"except {ast.unparse(h.type) if h.type is not None else 'Exception'}"))
        elif isinstance(n, ast.stmt) and not isinstance(n, (ast.Pass, ast.Import, ast.ImportFrom)) \
                and not (isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant)) \
                and not isinstance(n, (ast.If, ast.For, ast.While, ast.FunctionDef, ast.Return, ast.Try, ast.With)):
            labels.add(_label(ast.unparse(n)))
    return labels, counts


_STRUCTURAL = {"Inicio", "Fin", "Sí", "No", "cada iteración", "siguiente", "fin del bucle", "excepción", "sin break"}


def validate_diagram_against_code(code: str, mermaid: str) -> SemanticReport:
    rep = SemanticReport()
    expected, counts = _expected_diagram_labels(code)
    labels = [l.strip().strip('"') for l in diagram_labels(mermaid)]     # las aristas vienen entre comillas
    node_labels = [l for l in labels if l not in _STRUCTURAL]
    kinds = {"while": 0, "for": 0, "if": 0, "return": 0, "break": 0, "continue": 0, "def": 0}
    for l in node_labels:
        if l.startswith("while "):
            kinds["while"] += 1
        elif l.startswith("for "):
            kinds["for"] += 1
        elif l.endswith("?"):
            kinds["if"] += 1
        elif l.startswith("return"):
            kinds["return"] += 1
        elif l in ("break", "continue"):
            kinds[l] += 1
        elif l.startswith("def "):
            kinds["def"] += 1
    variant2 = "subgraph" in mermaid
    for k, n in counts.items():
        got = kinds[k] if not (k == "def" and variant2) else counts["def"]
        if k == "def" and variant2:            # en la variante 2 la firma vive en el título del subgrafo
            got = len([1 for ln in mermaid.splitlines() if ln.strip().startswith("subgraph ")])
        if got != n:
            rep.fail("D1", f"{k}: el AST tiene {n} y el diagrama {got}")
    extra = [l for l in node_labels if l not in expected and not l.startswith("def ")]
    if extra:
        rep.fail("D1", f"etiquetas sin sentencia correspondiente en el código: {extra[:3]}")
    rep.passed("D1")
    return rep
