"""AST policy enforcement — whitelist/blacklist Python AST nodes, imports, attributes.

Every code submission is parsed via `ast.parse()` and validated before execution.
This is the FIRST line of defense: catch malicious code statically, before it runs.
"""

from __future__ import annotations

import ast
import sys
from typing import Any

from app.sandbox.exceptions import (
    SandboxImportViolation,
    SandboxSubprocessViolation,
    SandboxSocketViolation,
    SandboxFilesystemViolation,
    SandboxCTypesViolation,
    SandboxPickleViolation,
    SandboxIntrospectionViolation,
    SandboxThreadViolation,
    SandboxAsyncViolation,
    SandboxSecurityViolation,
)

# ── Node whitelist — only these AST node types are allowed ────────
ALLOWED_AST_NODES: frozenset[type[ast.AST]] = frozenset({
    # Expressions
    ast.Expr, ast.Constant, ast.Name, ast.Load, ast.Store, ast.Del,
    ast.UnaryOp, ast.UAdd, ast.USub, ast.Not, ast.Invert,
    ast.BinOp, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv,
    ast.Mod, ast.Pow, ast.LShift, ast.RShift, ast.BitOr, ast.BitXor,
    ast.BitAnd, ast.MatMult,
    ast.BoolOp, ast.And, ast.Or,
    ast.Compare, ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
    ast.Is, ast.IsNot, ast.In, ast.NotIn,
    ast.Call, ast.keyword, ast.Attribute,
    ast.Subscript, ast.Index, ast.Slice,
    ast.List, ast.Tuple, ast.Set, ast.Dict, ast.ListComp,
    ast.SetComp, ast.DictComp, ast.GeneratorExp,
    ast.comprehension, ast.Starred,
    ast.Lambda, ast.IfExp,
    ast.FormattedValue, ast.JoinedStr,
    ast.NamedExpr,

    # Statements
    ast.Module, ast.Interactive,
    ast.Assign, ast.AnnAssign, ast.AugAssign,
    ast.If, ast.For, ast.While, ast.Break, ast.Continue,
    ast.Try, ast.ExceptHandler, ast.TryStar,
    ast.With, ast.withitem, ast.AsyncWith,
    ast.Raise, ast.Assert,
    ast.Import, ast.ImportFrom, ast.alias,
    ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.Return,
    ast.Yield, ast.YieldFrom, ast.Await,
    ast.arguments, ast.arg, ast.keyword,

    # Pattern matching (Python 3.10+)
    ast.Match, ast.MatchValue, ast.MatchSingleton, ast.MatchSequence,
    ast.MatchMapping, ast.MatchClass, ast.MatchStar, ast.MatchAs,
    ast.MatchOr,

    ast.Global, ast.Nonlocal, ast.Pass, ast.Delete,
    ast.AsyncFor, ast.AsyncWith, ast.comprehension,
})

# ── Blocked top-level module imports ──────────────────────────────
BLOCKED_IMPORTS: frozenset[str] = frozenset({
    # System/process — sandbox escapes
    "os", "subprocess", "sys", "signal", "pdb", "traceback",
    "faulthandler", "atexit", "gc", "inspect",

    # FFI — memory escapes
    "ctypes", "cffi", "numba", "Cython",

    # Networking
    "socket", "ssl", "socketserver", "http", "urllib",
    "requests", "aiohttp", "httpx", "urllib3",
    "asyncio", "selectors", "select", "asyncore",

    # Serialization — arbitrary code execution
    "pickle", "shelve", "marshal", "dbm",
    "xml.etree", "xml.dom", "xml.sax", "xmlrpc",
    "configparser",

    # Filesystem
    "shutil", "glob", "fnmatch", "tempfile", "fileinput",
    "io", "pathlib", "zipfile", "tarfile", "gzip", "bz2", "lzma",

    # Concurrency — resource abuse
    "threading", "_thread", "multiprocessing", "concurrent",
    "queue",

    # Misc — dangerous
    "builtins", "__future__", "future", "past",
    "imp", "importlib", "pkgutil", "pkg_resources",
    "code", "codeop", "codecs",
    "re", "regex",
    "platform", "ctypes", "resource",

    # Debug / introspection
    "dis", "ast", "symtable", "token", "tokenize",
    "profile", "cProfile", "trace", "tracemalloc",
    "sysconfig", "distutils",

    # C extension loading
    "dl", "grp", "pwd", "spwd", "crypt",
    "fcntl", "termios", "tty", "pty",
    "mmap", "msvcrt",
})

# ── Blocked attribute chains (prevent method-level escapes) ───────
BLOCKED_ATTRIBUTE_CHAINS: list[list[str]] = [
    # Object introspection
    ["__class__"], ["__bases__"], ["__subclasses__"], ["__mro__"],
    ["__globals__"], ["__code__"], ["__closure__"],
    ["__builtins__"], ["__dict__"], ["__dir__"],
    ["func_globals"], ["gi_frame"], ["f_back"],

    # Descriptor protocol abuse
    ["__getattribute__"], ["__setattr__"], ["__delattr__"],
    ["__get__"], ["__set__"], ["__delete__"],
    ["__enter__"], ["__exit__"],

    # Code object manipulation
    ["__code__"], ["__func__"], ["__self__"],
    ["__call__"], ["__new__"], ["__init__"],
    ["__reduce__"], ["__reduce_ex__"],
    ["__getstate__"], ["__setstate__"],

    # Module-level
    ["__import__"], ["__file__"], ["__path__"],

    # C / FFI
    ["from_address"], ["string_at"], ["POINTER"], ["CFUNCTYPE"],
    ["dlopen"], ["dlclose"],

    # System
    ["system"], ["popen"], ["fork"], ["exec"], ["spawn"],
]

# ── Blocks call patterns (function name → violation type) ─────────
BLOCKED_CALLS: dict[str, type[SandboxSecurityViolation]] = {
    "getattr": SandboxSecurityViolation,
    "setattr": SandboxSecurityViolation,
    "delattr": SandboxSecurityViolation,
    "__builtins__": SandboxSecurityViolation,
    "eval": SandboxSecurityViolation,
    "exec": SandboxSecurityViolation,
    "compile": SandboxSecurityViolation,
    "__import__": SandboxImportViolation,
    "importlib": SandboxImportViolation,
    "open": SandboxFilesystemViolation,
    "input": SandboxSecurityViolation,
    "breakpoint": SandboxSecurityViolation,
    "help": SandboxSecurityViolation,
    "exit": SandboxSecurityViolation,
    "quit": SandboxSecurityViolation,
}


class ValidationResult:
    """Result of AST policy validation."""

    def __init__(self) -> None:
        self.valid: bool = True
        self.violations: list[str] = []
        self.node_count: int = 0
        self.max_depth: int = 0

    def fail(self, message: str) -> None:
        self.valid = False
        self.violations.append(message)

    @property
    def summary(self) -> str:
        if self.valid:
            return f"Valid ({self.node_count} nodes, depth {self.max_depth})"
        return f"BLOCKED ({len(self.violations)} violations): {self.violations[0]}"

    def __bool__(self) -> bool:
        return self.valid


class ASTSafetyPolicy:
    """Whitelist-based AST policy for Python code.

    Validates:
    1. All AST nodes are in ALLOWED_AST_NODES
    2. No blocked imports
    3. No blocked attribute chains
    4. No blocked function calls
    5. Recursion depth limit
    """

    def __init__(
        self,
        max_nodes: int = 500,
        max_depth: int = 50,
        max_source_bytes: int = 65536,
    ):
        self._max_nodes = max_nodes
        self._max_depth = max_depth
        self._max_source_bytes = max_source_bytes

    def validate(self, source: str) -> ValidationResult:
        """Parse and validate source code against the security policy."""
        result = ValidationResult()

        if not source.strip():
            result.fail("Empty source")
            return result

        if len(source.encode("utf-8")) > self._max_source_bytes:
            result.fail(f"Source too large (max {self._max_source_bytes} bytes)")
            return result

        try:
            tree = ast.parse(source, mode="exec")
        except SyntaxError as e:
            result.fail(f"Syntax error: {e}")
            return result

        self._walk(tree, result, depth=0)

        if result.node_count > self._max_nodes:
            result.fail(f"Too many AST nodes ({result.node_count} > {self._max_nodes})")

        return result

    def _walk(
        self, node: ast.AST, result: ValidationResult, depth: int,
    ) -> None:
        """Recursively walk the AST, validating each node."""
        result.node_count += 1
        result.max_depth = max(result.max_depth, depth)

        if depth > self._max_depth:
            result.fail(f"AST depth exceeds limit ({depth} > {self._max_depth})")
            return

        node_type = type(node)

        if node_type not in ALLOWED_AST_NODES:
            result.fail(f"Blocked AST node type: {node_type.__name__}")
            return

        # ── Import validation ─────────────────────────────────────
        if isinstance(node, ast.Import):
            for alias in node.names:
                self._check_import(alias.name, result)

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                self._check_import(node.module, result)
            for alias in node.names:
                self._check_import(alias.name, result)

        # ── Call validation ───────────────────────────────────────
        elif isinstance(node, ast.Call):
            self._check_call(node, result)

        # ── Attribute validation ──────────────────────────────────
        elif isinstance(node, ast.Attribute):
            self._check_attribute_chain(node, result)

        # ── Name validation ───────────────────────────────────────
        elif isinstance(node, ast.Name):
            if node.id in BLOCKED_CALLS:
                result.fail(f"Blocked name: {node.id}")

        # ── Subscript / index (dunder access) ─────────────────────
        elif isinstance(node, ast.Subscript):
            self._check_subscript(node, result)

        for child in ast.iter_child_nodes(node):
            self._walk(child, result, depth + 1)

    def _check_import(self, name: str, result: ValidationResult) -> None:
        """Check if an import name is blocked."""
        if name in BLOCKED_IMPORTS:
            result.fail(f"Blocked import: '{name}'")
            return
        for blocked in BLOCKED_IMPORTS:
            if name.startswith(f"{blocked}."):
                result.fail(f"Blocked import: '{name}'")
                return

    def _check_call(self, node: ast.Call, result: ValidationResult) -> None:
        """Check if a function call is blocked."""
        func = node.func
        if isinstance(func, ast.Name):
            if func.id in BLOCKED_CALLS:
                exc_type = BLOCKED_CALLS[func.id]
                result.fail(f"Blocked call: {func.id}()")

        elif isinstance(func, ast.Attribute):
            chain = self._resolve_attribute_chain(func)
            for blocked_chain in BLOCKED_ATTRIBUTE_CHAINS:
                if chain[-len(blocked_chain):] == blocked_chain:
                    result.fail(f"Blocked attribute call: {'.'.join(chain)}")

    def _check_attribute_chain(
        self, node: ast.Attribute, result: ValidationResult,
    ) -> None:
        """Check if an attribute access resolves to a blocked pattern."""
        chain = self._resolve_attribute_chain(node)
        for blocked in BLOCKED_ATTRIBUTE_CHAINS:
            if len(chain) >= len(blocked) and chain[-len(blocked):] == blocked:
                result.fail(f"Blocked attribute: {'.'.join(chain)}")

    def _check_subscript(
        self, node: ast.Subscript, result: ValidationResult,
    ) -> None:
        """Check subscript access for dunder strings."""
        if isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, str):
            val = node.slice.value
            if val.startswith("__") and val.endswith("__"):
                result.fail(f"Blocked dunder subscript: '{val}'")

    def _resolve_attribute_chain(self, node: ast.AST) -> list[str]:
        """Resolve a chain of Attribute/Name/Call nodes to a list of strings."""
        parts: list[str] = []
        current = node
        while True:
            if isinstance(current, ast.Attribute):
                parts.append(current.attr)
                current = current.value
            elif isinstance(current, ast.Name):
                parts.append(current.id)
                break
            elif isinstance(current, ast.Call):
                if isinstance(current.func, ast.Attribute):
                    parts.append(f"{current.func.attr}()")
                    current = current.func.value
                elif isinstance(current.func, ast.Name):
                    parts.append(f"{current.func.id}()")
                    break
                else:
                    parts.append("<?>")
                    break
            else:
                parts.append("<?>")
                break
        return list(reversed(parts))
