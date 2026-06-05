from __future__ import annotations

import ast
from dataclasses import dataclass

from app.sandbox.schemas import SecurityViolation


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
    ("os", "system"),
    ("os", "popen"),
    ("os", "fork"),
    ("os", "spawn"),
    ("os", "execv"),
    ("os", "execve"),
    ("subprocess", "run"),
    ("subprocess", "Popen"),
    ("socket", "socket"),
    ("shutil", "rmtree"),
    ("pathlib", "Path"),
    ("multiprocessing", "Process"),
}


@dataclass(frozen=True)
class SandboxPolicy:
    denied_import_roots: frozenset[str] = frozenset(DENIED_IMPORT_ROOTS)
    denied_calls: frozenset[str] = frozenset(DENIED_CALLS)

    def validate(self, code: str) -> list[SecurityViolation]:
        try:
            tree = ast.parse(code)
        except SyntaxError as exc:
            return [
                SecurityViolation(
                    rule="syntax",
                    message=exc.msg,
                    line=exc.lineno,
                    symbol=exc.text.strip() if exc.text else None,
                )
            ]

        visitor = _PolicyVisitor(self)
        visitor.visit(tree)
        return visitor.violations


class _PolicyVisitor(ast.NodeVisitor):
    def __init__(self, policy: SandboxPolicy):
        self.policy = policy
        self.violations: list[SecurityViolation] = []

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            root = alias.name.split(".", 1)[0]
            if root in self.policy.denied_import_roots:
                self._deny("restricted_import", f"Import '{root}' is not allowed", node, root)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        root = (node.module or "").split(".", 1)[0]
        if root in self.policy.denied_import_roots:
            self._deny("restricted_import", f"Import '{root}' is not allowed", node, root)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        name = self._call_name(node.func)
        if name in self.policy.denied_calls:
            self._deny("restricted_call", f"Call '{name}' is not allowed", node, name)

        dotted = self._dotted_call(node.func)
        if dotted:
            root, attr = dotted
            if (root, attr) in DENIED_ATTRIBUTES or root in self.policy.denied_import_roots:
                self._deny("restricted_call", f"Call '{root}.{attr}' is not allowed", node, f"{root}.{attr}")
        self.generic_visit(node)

    def _call_name(self, func: ast.expr) -> str:
        return func.id if isinstance(func, ast.Name) else ""

    def _dotted_call(self, func: ast.expr) -> tuple[str, str] | None:
        if not isinstance(func, ast.Attribute):
            return None
        parts: list[str] = [func.attr]
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

    def _deny(self, rule: str, message: str, node: ast.AST, symbol: str) -> None:
        self.violations.append(
            SecurityViolation(
                rule=rule,
                message=message,
                line=getattr(node, "lineno", None),
                symbol=symbol,
            )
        )
