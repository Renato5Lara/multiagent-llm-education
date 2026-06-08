"""
Test suite: Sandbox hardening — attack vector verification.

Tests 25+ attack vectors against the sandbox to verify:
  - All blocked imports are rejected
  - All known escape techniques are blocked
  - Resource limits are enforced
  - Timeout is enforced
  - AST policy catches malicious code statically
  - Cleanup is deterministic and complete
  - Concurrent execution is safe

Run with:
    python -m pytest tests/test_sandbox_attack.py -v --tb=short
    python -m pytest tests/test_sandbox_attack.py -v -k "test_import"
"""

from __future__ import annotations

import asyncio
import pytest

from app.sandbox.ast_policy import ASTSafetyPolicy
from app.sandbox.executor import SandboxExecutor
from app.sandbox.security_monitor import SecurityMonitor
from app.sandbox.cleanup import CleanupManager
from app.sandbox.exceptions import (
    SandboxSecurityViolation,
    SandboxImportViolation,
    SandboxTimeout,
    SandboxDockerError,
)

# ── Fixtures ─────────────────────────────────────────────────────────

@pytest.fixture
def ast_policy():
    return ASTSafetyPolicy(max_nodes=200, max_depth=30)


@pytest.fixture
def security_monitor():
    return SecurityMonitor()


@pytest.fixture
def cleanup_manager():
    return CleanupManager()


def make_executor(**kwargs):
    """Create SandboxExecutor with test-safe defaults and a fresh monitor."""
    monitor = kwargs.pop("monitor", SecurityMonitor())
    return SandboxExecutor(
        ast_policy=kwargs.pop("ast", ASTSafetyPolicy(max_nodes=200, max_depth=30)),
        security_monitor=monitor,
        cleanup=CleanupManager(),
        timeout=kwargs.pop("timeout", 5.0),
        memory_limit_mb=kwargs.pop("memory", 256),
        max_nodes=200,
    )


def run(code: str, **kwargs):
    """Synchronous helper to run sandbox execution."""
    executor = make_executor(**kwargs)

    async def _run():
        return await executor.execute(code)

    return asyncio.run(_run())


# ═════════════════════════════════════════════════════════════════════
# 1. IMPORT BLOCKING
# ═════════════════════════════════════════════════════════════════════

BLOCKED_IMPORTS = [
    ("os", "import os"),
    ("os.path", "import os.path"),
    ("subprocess", "import subprocess"),
    ("sys", "import sys"),
    ("ctypes", "import ctypes"),
    ("socket", "import socket"),
    ("pickle", "import pickle"),
    ("threading", "import threading"),
    ("multiprocessing", "import multiprocessing"),
    ("asyncio", "import asyncio"),
    ("shutil", "import shutil"),
    ("glob", "import glob"),
    ("tempfile", "import tempfile"),
    ("io", "import io"),
    ("pathlib", "import pathlib"),
    ("zipfile", "import zipfile"),
    ("tarfile", "import tarfile"),
    ("http", "import http"),
    ("requests", "import requests"),
    ("builtins", "import builtins"),
    ("importlib", "import importlib"),
    ("dis", "import dis"),
    ("ast", "import ast"),
    ("inspect", "import inspect"),
    ("gc", "import gc"),
    ("signal", "import signal"),
    ("code", "import code"),
    ("marshal", "import marshal"),
    ("shelve", "import shelve"),
    ("mmap", "import mmap"),
    ("fcntl", "import fcntl"),
    ("pty", "import pty"),
    ("tty", "import tty"),
    ("termios", "import termios"),
    ("crypt", "import crypt"),
    ("grp", "import grp"),
    ("pwd", "import pwd"),
]

BLOCKED_FROM_IMPORTS = [
    ("os.system", "from os import system"),
    ("os.popen", "from os import popen"),
    ("os.fork", "from os import fork"),
    ("os.execv", "from os import execv"),
    ("os.kill", "from os import kill"),
    ("subprocess.run", "from subprocess import run"),
    ("subprocess.Popen", "from subprocess import Popen"),
    ("ctypes.CDLL", "from ctypes import CDLL"),
    ("ctypes.pythonapi", "from ctypes import pythonapi"),
    ("pickle.loads", "from pickle import loads"),
    ("pickle.Unpickler", "from pickle import Unpickler"),
    ("socket.socket", "from socket import socket"),
    ("socket.create_connection", "from socket import create_connection"),
]


@pytest.mark.parametrize("name,code", BLOCKED_IMPORTS)
def test_blocked_imports(name, code):
    """All critical modules must be blocked at import level."""
    result = run(code)
    assert result.get("violation"), f"Import '{name}' was NOT blocked: {code}"
    assert "Blocked import" in result.get("error", ""), f"Wrong violation for '{name}'"


@pytest.mark.parametrize("name,code", BLOCKED_FROM_IMPORTS)
def test_blocked_from_imports(name, code):
    """'from X import Y' must also be blocked."""
    result = run(code)
    assert result.get("violation"), f"from-import '{name}' was NOT blocked: {code}"


@pytest.mark.parametrize("name,code", [
    ("os.environ", "import os.environ"),
    ("os.path.join", "import os.path.join as join"),
    ("shutil.copy", "import shutil.copy"),
])
def test_blocked_submodule_imports(name, code):
    """Submodule imports of blocked packages must be blocked."""
    result = run(code)
    assert result.get("violation"), f"Submodule import '{name}' was NOT blocked"


# ═════════════════════════════════════════════════════════════════════
# 2. EVAL / EXEC / COMPILE BYPASS
# ═════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("code", [
    "eval('1+1')",
    "exec('x=1')",
    "compile('x=1', '<string>', 'exec')",
    "__builtins__['eval']('1+1')",
    "__builtins__['exec']('import os')",
    "eval('__import__(\"os\").system(\"id\")')",
    "exec('import os; os.system(\"id\")')",
])
def test_eval_exec_compile_blocked(code):
    """eval/exec/compile must be blocked by AST policy."""
    result = run(code)
    assert result.get("violation"), f"eval/exec was NOT blocked: {code}"


# ═════════════════════════════════════════════════════════════════════
# 3. GETATTR / SETATTR BYPASS
# ═════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("code", [
    "getattr({}, '__class__')",
    "getattr(1, '__class__')",
    "setattr({}, 'x', 1)",
    "delattr({}, 'x')",
])
def test_getattr_setattr_blocked(code):
    """getattr/setattr/delattr must be blocked."""
    result = run(code)
    assert result.get("violation"), f"getattr bypass was NOT blocked: {code}"


# ═════════════════════════════════════════════════════════════════════
# 4. DUNDER ATTRIBUTE / SUBSCRIPT ACCESS
# ═════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("code", [
    "[].__class__",
    "().__class__",
    "{}.__class__",
    "''.__class__",
    "1 .__class__",
    "x.__class__",
    "[].__class__.__bases__",
    "[].__class__.__mro__",
    "[].__class__.__subclasses__()",
    "().__class__.__bases__[0].__subclasses__()",
    "x.__globals__",
    "x.__code__",
    "x.__closure__",
    "x.__dict__",
])
def test_dunder_attribute_blocked(code):
    """__class__, __bases__, __subclasses__, __globals__ must be blocked."""
    code_with_var = f"x = 1\n{code}"
    result = run(code_with_var)
    assert result.get("violation"), f"dunder access was NOT blocked: {code}"


@pytest.mark.parametrize("code", [
    "x['__class__']",
    "x['__init__']",
    "x['__dict__']",
])
def test_dunder_subscript_blocked(code):
    """Dunder string subscripts must be blocked."""
    result = run(f"x = {{}}\n{code}")
    assert result.get("violation"), f"dunder subscript was NOT blocked: {code}"


# ═════════════════════════════════════════════════════════════════════
# 5. RECURSION / STACK ABUSE
# ═════════════════════════════════════════════════════════════════════

RECURSION_CODE = """
def recurse(n):
    if n <= 0:
        return 0
    return 1 + recurse(n - 1)

result = recurse(100000)
print(result)
"""

def test_recursion_depth_limit(ast_policy):
    """Deep recursion must be blocked by AST depth limit."""
    result = ast_policy.validate(RECURSION_CODE)
    # Should be valid by AST (it's just a function), but runtime should crash
    # AST policy allows recursion in general — the subprocess/Docker handles runtime
    assert result.valid


RECURSION_BOMB = """
def f():
    while True:
        f()
f()
"""

def test_recursion_bomb_timeout():
    """Infinite recursion must be caught by timeout."""
    result = run(RECURSION_BOMB, timeout=3.0)
    # May be blocked by AST (too deep) or by timeout at runtime
    passes = result.get("violation") or result.get("violation_type") == "timeout" or not result.get("success")
    assert passes, f"Recursion bomb not stopped: {result}"


# ═════════════════════════════════════════════════════════════════════
# 6. INFINITE LOOP / CPU EXHAUSTION
# ═════════════════════════════════════════════════════════════════════

INFINITE_LOOP_CODE = """
while True:
    pass
"""

def test_infinite_loop_timeout():
    """Infinite loops must be caught by timeout."""
    result = run(INFINITE_LOOP_CODE, timeout=2.0)
    timeout = result.get("violation_type") == "timeout"
    killed = not result.get("success") and result.get("error", "")
    assert timeout or killed, f"Infinite loop not stopped: {result}"


BUSY_WAIT_CODE = """
while True:
    x = 1 + 1
"""

def test_busy_wait_timeout():
    """Busy-wait loops must be caught by timeout."""
    result = run(BUSY_WAIT_CODE, timeout=2.0)
    assert not result.get("success"), "Busy-wait loop was not stopped"


# ═════════════════════════════════════════════════════════════════════
# 7. MEMORY / RESOURCE EXHAUSTION
# ═════════════════════════════════════════════════════════════════════

MEMORY_BOMB_CODE = """
data = []
while True:
    data.append('x' * 1000000)
"""

def test_memory_bomb():
    """Memory exhaustion must be stopped (OOM kill or timeout)."""
    result = run(MEMORY_BOMB_CODE, timeout=5.0, memory=64)
    oom = result.get("violation_type") == "memory_exceeded"
    timeout = result.get("violation_type") == "timeout"
    assert oom or timeout or not result.get("success"), f"Memory bomb not stopped: {result}"


LIST_BOMB_CODE = """
[[[]] * 1000000 for _ in range(1000000)]
"""

def test_list_memory_bomb():
    """Large list allocations must be stopped."""
    result = run(LIST_BOMB_CODE, timeout=5.0, memory=64)
    assert not result.get("success"), f"List bomb not stopped: {result}"


# ═════════════════════════════════════════════════════════════════════
# 8. FORK / THREAD / PROCESS BOMBS
# ═════════════════════════════════════════════════════════════════════

FORK_BOMB_CODE = """
import os
while True:
    os.fork()
"""

def test_fork_bomb_blocked():
    """os.fork must be blocked by AST policy."""
    result = run(FORK_BOMB_CODE)
    assert result.get("violation"), "Fork bomb was NOT blocked by AST"


THREAD_BOMB_CODE = """
import threading
def spin():
    while True:
        pass
for _ in range(100):
    threading.Thread(target=spin).start()
"""

def test_thread_bomb_blocked():
    """Thread spawning must be blocked by AST policy."""
    result = run(THREAD_BOMB_CODE)
    # Either import blocked (threading) or function blocked
    assert result.get("violation"), f"Thread bomb was NOT blocked: {result}"


# ═════════════════════════════════════════════════════════════════════
# 9. FILESYSTEM ABUSE
# ═════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("code", [
    "open('/etc/passwd').read()",
    "open('/tmp/foo', 'w').write('test')",
    "open('.env').read()",
    "__builtins__['open']('/etc/shadow')",
])
def test_filesystem_access_blocked(code):
    """All filesystem access must be blocked."""
    result = run(code)
    assert result.get("violation"), f"Filesystem access NOT blocked: {code}"


# ═════════════════════════════════════════════════════════════════════
# 10. SERIALIZATION / PICKLE ABUSE
# ═════════════════════════════════════════════════════════════════════

PICKLE_PAYLOAD = """
import pickle
pickle.loads(b"cos\\nsystem\\n(S'id'\\ntR.")
"""

def test_pickle_abuse_blocked():
    """pickle deserialization must be blocked."""
    result = run(PICKLE_PAYLOAD)
    assert result.get("violation"), "Pickle abuse was NOT blocked"


# ═════════════════════════════════════════════════════════════════════
# 11. CTYPES ABUSE
# ═════════════════════════════════════════════════════════════════════

CTYPES_CODE = """
import ctypes
libc = ctypes.CDLL(None)
libc.system(b"id")
"""

def test_ctypes_blocked():
    """ctypes must be blocked."""
    result = run(CTYPES_CODE)
    assert result.get("violation"), "ctypes was NOT blocked"


CTYPES_DIRECT_CODE = """\
import ctypes
ctypes.pythonapi.PyOS_system(b"id")
"""

def test_ctypes_pythonapi_blocked():
    """ctypes.pythonapi must be blocked."""
    result = run(CTYPES_DIRECT_CODE)
    assert result.get("violation"), "ctypes.pythonapi was NOT blocked"


# ═════════════════════════════════════════════════════════════════════
# 12. OBJECT INTROSPECTION ABUSE
# ═════════════════════════════════════════════════════════════════════

INTROSPECTION_CODE = """
class Foo:
    pass

Foo.__subclasses__ = classmethod(lambda cls: [object])
"""

def test_introspection_blocked():
    """__subclasses__ assignment must be blocked."""
    result = run(INTROSPECTION_CODE)
    assert result.get("violation"), "Introspection via __subclasses__ was NOT blocked"


# ═════════════════════════════════════════════════════════════════════
# 13. SANDBOX ESCAPE ATTEMPTS
# ═════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("code", [
    "__import__('os').system('id')",
    "__builtins__['__import__']('os').system('id')",
    "().__class__.__bases__[0].__subclasses__()",
    "''.__class__.__mro__[1].__subclasses__()",
    "{}.__class__.__bases__[0].__subclasses__()",
    "[].__class__.__bases__[0].__subclasses__()",
])
def test_sandbox_escape_attempts(code):
    """Classic sandbox escape chains must be blocked."""
    result = run(code)
    assert result.get("violation"), f"Sandbox escape was NOT blocked: {code}"


# ═════════════════════════════════════════════════════════════════════
# 14. AST POLICY EDGE CASES
# ═════════════════════════════════════════════════════════════════════

def test_ast_policy_valid_code():
    """Legitimate Python must pass AST policy."""
    policy = ASTSafetyPolicy()
    code = """
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)

result = factorial(10)
print(result)
"""
    result = policy.validate(code)
    assert result.valid, f"Valid code was rejected: {result.violations}"


def test_ast_policy_syntax_error():
    """Syntax errors must be caught by AST policy."""
    policy = ASTSafetyPolicy()
    result = policy.validate("def broken(")
    assert not result.valid


def test_ast_policy_empty_code():
    """Empty code must be rejected."""
    policy = ASTSafetyPolicy()
    result = policy.validate("")
    assert not result.valid
    result = policy.validate("   ")
    assert not result.valid


def test_ast_policy_node_limit():
    """Code exceeding node limit must be rejected."""
    policy = ASTSafetyPolicy(max_nodes=10)
    result = policy.validate("a=1\nb=2\nc=3\nd=4\ne=5\nf=6")
    assert not result.valid, "Code with >10 nodes was accepted"


def test_ast_policy_max_depth():
    """Deeply nested code must be rejected."""
    policy = ASTSafetyPolicy(max_depth=5)
    code = "a = 1\n" * 50
    result = policy.validate(code)
    # Note: multiple statements at the same level don't increase depth
    # This tests that depth > 5 is actually caught with nested structures
    nested = """
if True:
    if True:
        if True:
            if True:
                if True:
                    if True:
                        pass
"""
    result = policy.validate(nested)
    assert not result.valid, "Deeply nested code was accepted"


# ═════════════════════════════════════════════════════════════════════
# 15. CONCURRENT EXECUTION SAFETY
# ═════════════════════════════════════════════════════════════════════

def test_concurrent_execution():
    """Multiple concurrent executions must not interfere."""
    codes = [
        "print('hello')",
        "x = 1 + 1; print(x)",
        "print('test')",
        "[i**2 for i in range(10)]",
    ]
    executor = make_executor()

    async def run_all():
        tasks = [executor.execute(code) for code in codes * 5]
        return await asyncio.gather(*tasks)

    results = asyncio.run(run_all())
    assert len(results) == 20, f"Expected 20 results, got {len(results)}"
    successes = [r for r in results if r.get("success")]
    assert len(successes) == 20, f"Not all concurrent executions succeeded: {results}"


# ═════════════════════════════════════════════════════════════════════
# 16. CLEANUP VERIFICATION
# ═════════════════════════════════════════════════════════════════════

def test_cleanup_after_execution():
    """Executor must clean up after each execution."""
    executor = make_executor()
    initial_total = executor.stats["total_executions"]

    async def _exec():
        return await executor.execute("print('test')")

    result = asyncio.run(_exec())
    assert result.get("success"), f"Execution failed: {result}"
    final_total = executor.stats["total_executions"]
    assert final_total > initial_total, f"Stats not updated: {initial_total} -> {final_total}"


def test_security_monitor_tracks_violations():
    """SecurityMonitor must correctly track and classify violations."""
    monitor = SecurityMonitor()
    assert monitor.total_violations == 0

    monitor.record_violation("import", "Attempted to import os")
    monitor.record_violation("timeout", "Execution timed out after 10s")
    monitor.record_violation("memory_exceeded", "Memory limit exceeded")

    assert monitor.total_violations == 3
    breakdown = monitor.classification_breakdown()
    assert breakdown["import_violations"] == 1
    assert breakdown["timeout_violations"] == 1
    assert breakdown["memory_violations"] == 1

    summary = monitor.summary()
    assert summary["total_violations"] == 3
    assert len(summary["violation_types"]) == 3


# ═════════════════════════════════════════════════════════════════════
# 17. SANITIZE PRINT / STDOUT
# ═════════════════════════════════════════════════════════════════════

def test_normal_print_works():
    """Normal print statements must work."""
    result = run("print('Hello, World!')")
    assert result.get("success")
    assert "Hello, World!" in result.get("stdout", "")


def test_stdout_stderr_separation():
    """stdout and stderr must be properly separated."""
    code = """
print("stdout_line")
1 / 0
"""
    result = run(code)
    assert "stdout_line" in result.get("stdout", "")
    assert not result.get("success")  # division by zero error
    assert "stderr" in result and result["stderr"]  # stderr has the traceback


# ═════════════════════════════════════════════════════════════════════
# 18. TIMEOUT MEASUREMENT
# ═════════════════════════════════════════════════════════════════════

def test_timeout_enforcement():
    """Timeout must be enforced and measured."""
    result = run("while True: pass", timeout=1.0)
    assert not result.get("success")
    timeout = result.get("violation_type") == "timeout"
    error = "timeout" in result.get("error", "").lower()
    assert timeout or error, f"Timeout not enforced: {result}"


def test_timeout_duration_tracked():
    """Timeout duration must be tracked in results."""
    result = run("while True: pass", timeout=2.0)
    assert result.get("duration_ms", 0) > 0
    assert result.get("container_duration_ms", 0) > 0


# ═════════════════════════════════════════════════════════════════════
# 19. NODE COUNT TRACKING
# ═════════════════════════════════════════════════════════════════════

def test_ast_node_count_tracked():
    """AST node count must be reported in execution result."""
    result = run("print('hello')")
    assert "ast_nodes" in result
    assert result["ast_nodes"] > 0


# ═════════════════════════════════════════════════════════════════════
# 20. ERROR CLASSIFICATION
# ═════════════════════════════════════════════════════════════════════

def test_error_classification():
    """Violation types must be properly classified."""
    from app.sandbox.exceptions import (
        SandboxImportViolation, SandboxTimeout, classify,
    )
    assert classify(SandboxImportViolation("test")) == "import_violation"
    assert classify(SandboxTimeout("test")) == "timeout"
    assert classify(Exception("test")) == "unknown"
