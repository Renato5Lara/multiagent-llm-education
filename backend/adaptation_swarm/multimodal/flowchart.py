"""Generador de diagramas de flujo Mermaid a partir del AST REAL de un código Python
(AG3; asesoría: "representaciones gráficas asociadas a la lógica del código").

Coherencia código↔diagrama por construcción: cada nodo sale de un nodo del AST, no de texto libre.

Variantes (orden creciente de detalle/costo):
  0  estructura: cabecera de función, decisiones/bucles, break/continue y return
  1  detalle:    variante 0 + todas las sentencias simples (asignaciones, llamadas)
  2  completo:   variante 1 + Inicio/Fin, etiquetas de arista (Sí/No, iteración), subgrafo por función
"""

from __future__ import annotations

import ast
import re

_MAX_LABEL = 64


_PAIRS = {"(": ")", "[": "]", "{": "}"}


def _balance(text: str) -> str:
    """Deja la etiqueta con delimitadores balanceados (exigencia del validador Mermaid). Tras truncar una expresión a mitad se
    CIERRAN los delimitadores abiertos (se conserva el contenido); si el desbalance viene del propio texto (p. ej. un
    paréntesis dentro de una cadena) se retiran los delimitadores de ese tipo."""
    stack: list[str] = []
    for ch in text:
        if ch in _PAIRS:
            stack.append(_PAIRS[ch])
        elif ch in _PAIRS.values():
            if stack and stack[-1] == ch:
                stack.pop()
            else:
                stack = None  # cierre sin apertura: desbalance del propio texto
                break
    if stack is not None:
        return text + "".join(reversed(stack))
    for opener, closer in _PAIRS.items():
        if text.count(opener) != text.count(closer):
            text = text.replace(opener, "").replace(closer, "")
    return text


def _label(text: str, suffix: str = "") -> str:
    """Etiqueta segura para Mermaid. El `suffix` (p. ej. «?» de las decisiones) se conserva SIEMPRE: se trunca el texto, no el sufijo."""
    t = " ".join(text.split()).replace('"', "'").replace(";", ",").replace("`", "'").replace("#", "no.")
    room = _MAX_LABEL - len(suffix)
    if len(t) > room:
        t = t[: room - 1] + "…"
    return _balance(t) + suffix


def _is_docstring(node: ast.stmt) -> bool:
    return isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)


class _Flow:
    def __init__(self, variant: int):
        self.variant = variant
        self.lines: list[str] = []
        self._n = 0

    # nodos y aristas ------------------------------------------------------
    def node(self, text: str, shape: str = "rect", suffix: str = "") -> str:
        self._n += 1
        nid = f"n{self._n}"
        lab = _label(text, suffix)
        wrap = {"rect": ('["', '"]'), "decision": ('{"', '"}'), "term": ('(["', '"])')}[shape]
        self.lines.append(f"    {nid}{wrap[0]}{lab}{wrap[1]}")
        return nid

    def edge(self, a: str, b: str, label: str | None = None) -> None:
        if label and self.variant >= 2:
            self.lines.append(f'    {a} -->|"{_label(label)}"| {b}')
        else:
            self.lines.append(f"    {a} --> {b}")

    def link(self, pending: list[tuple[str, str | None]], target: str) -> None:
        for src, lab in pending:
            self.edge(src, target, lab)

    # sentencias -----------------------------------------------------------
    def stmts(self, body: list[ast.stmt], pending: list[tuple[str, str | None]],
              loop: dict | None) -> list[tuple[str, str | None]]:
        for st in body:
            # El código inalcanzable (tras un return/break) también se dibuja, como componente SIN aristas entrantes:
            # el diagrama refleja TODO el AST (la validación D1 exige un nodo por construcción).
            pending = self.stmt(st, pending, loop)
        return pending

    def stmt(self, st: ast.stmt, pending: list[tuple[str, str | None]], loop: dict | None):
        if _is_docstring(st) or isinstance(st, (ast.Pass, ast.Import, ast.ImportFrom)):
            return pending
        if isinstance(st, ast.Return):
            n = self.node("return " + (ast.unparse(st.value) if st.value else ""), "term")
            self.link(pending, n)
            self._returns.append(n)
            return []
        if isinstance(st, ast.If):
            d = self.node(ast.unparse(st.test), "decision", suffix="?")
            self.link(pending, d)
            yes = self.stmts(st.body, [(d, "Sí")], loop)
            no = self.stmts(st.orelse, [(d, "No")], loop) if st.orelse else [(d, "No")]
            return yes + no
        if isinstance(st, (ast.For, ast.While)):
            head = (f"for {ast.unparse(st.target)} in {ast.unparse(st.iter)}" if isinstance(st, ast.For)
                    else f"while {ast.unparse(st.test)}")
            h = self.node(head, "decision")
            self.link(pending, h)
            ctx = {"header": h, "breaks": []}
            body_exits = self.stmts(st.body, [(h, "cada iteración" if isinstance(st, ast.For) else "Sí")], ctx)
            for src, lab in body_exits:                    # arista de retorno al encabezado
                self.edge(src, h, "siguiente" if lab is None else lab)
            natural = [(h, "fin del bucle" if isinstance(st, ast.For) else "No")]
            if st.orelse:                                  # `else` del bucle: solo si termina sin `break`
                natural = self.stmts(st.orelse, [(h, "sin break")], loop)
            return natural + ctx["breaks"]
        if isinstance(st, ast.Break) and loop is not None:
            n = self.node("break", "rect")
            self.link(pending, n)
            loop["breaks"].append((n, None))
            return []
        if isinstance(st, ast.Continue) and loop is not None:
            n = self.node("continue", "rect")
            self.link(pending, n)
            self.edge(n, loop["header"])
            return []
        if isinstance(st, ast.Try):
            # try/except: el cuerpo y cada manejador son ramas reales del flujo (antes se ignoraban los manejadores)
            t = self.node("try", "rect")
            self.link(pending, t)
            exits = self.stmts(st.body, [(t, None)], loop)
            for h in st.handlers:
                kind = ast.unparse(h.type) if h.type is not None else "Exception"
                exits += self.stmts(h.body, self._handler_entry(t, kind), loop)
            if st.finalbody:
                exits = self.stmts(st.finalbody, exits, loop)
            return exits
        if isinstance(st, ast.With):
            return self.stmts(st.body, pending, loop)
        if isinstance(st, ast.FunctionDef):
            return self.function(st, pending)
        # sentencia simple
        if self.variant >= 1:
            n = self.node(ast.unparse(st), "rect")
            self.link(pending, n)
            return [(n, None)]
        return pending

    def _handler_entry(self, try_node: str, kind: str) -> list[tuple[str, str | None]]:
        h = self.node(f"except {kind}", "decision")
        self.edge(try_node, h, "excepción")
        return [(h, "Sí")]

    def function(self, fn: ast.FunctionDef, pending: list[tuple[str, str | None]]):
        args = ast.unparse(fn.args)
        title = f"def {fn.name}({args})"
        if self.variant >= 2:
            self.lines.append(f'    subgraph sg_{fn.name}["{_label(title)}"]')
            start = self.node("Inicio", "term")
        else:
            start = self.node(title, "rect")
        self.link(pending, start)
        exits = self.stmts(fn.body, [(start, None)], None)
        if self.variant >= 2:
            end = self.node("Fin", "term")
            self.link(exits + [(r, None) for r in self._returns], end)
            self._returns = []
            self.lines.append("    end")
            return []
        self._returns = []
        return exits

    def build(self, tree: ast.Module) -> str:
        self._returns: list[str] = []
        top = [s for s in tree.body if not _is_docstring(s)]
        funcs = [s for s in top if isinstance(s, ast.FunctionDef)]
        if funcs:
            for fn in funcs:
                self.function(fn, [])
        else:
            start = self.node("Inicio", "term")
            exits = self.stmts(top, [(start, None)], None)
            if self.variant >= 2:
                end = self.node("Fin", "term")
                self.link(exits, end)
        return "flowchart TD\n" + "\n".join(self.lines)


def build_flowchart(code: str, variant: int) -> str:
    if variant not in (0, 1, 2):
        raise ValueError("variant debe ser 0, 1 o 2")
    return _Flow(variant).build(ast.parse(code))


_NODE_RE = re.compile(r"^\s*(n\d+)(?:\[\"|\{\"|\(\[\")")
_EDGE_RE = re.compile(r"^\s*(n\d+)\s*-->(?:\|\"[^\"]*\"\|)?\s*(n\d+)\s*$")


def validate_flowchart(src: str) -> list[str]:
    """Validación estructural propia (además de `MermaidValidator`): ids únicos, aristas con
    extremos declarados, subgrafos balanceados. Devuelve la lista de errores (vacía = válido)."""
    errors: list[str] = []
    lines = src.strip().splitlines()
    if not lines or not lines[0].startswith("flowchart"):
        return ["falta la declaración `flowchart`"]
    declared: list[str] = []
    edges: list[tuple[str, str]] = []
    depth = 0
    for ln in lines[1:]:
        s = ln.strip()
        if s.startswith("subgraph "):
            depth += 1
        elif s == "end":
            depth -= 1
        elif (m := _NODE_RE.match(ln)):
            declared.append(m.group(1))
        elif (m := _EDGE_RE.match(ln)):
            edges.append((m.group(1), m.group(2)))
        elif s:
            errors.append(f"línea no reconocida: {s[:60]}")
    if depth != 0:
        errors.append("subgrafos desbalanceados")
    if len(set(declared)) != len(declared):
        errors.append("ids de nodo duplicados")
    ids = set(declared)
    if not edges:
        errors.append("el diagrama no tiene aristas")
    for a, b in edges:
        if a not in ids or b not in ids:
            errors.append(f"arista con extremo no declarado: {a}-->{b}")
    return errors
