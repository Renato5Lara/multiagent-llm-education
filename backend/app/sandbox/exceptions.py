"""Sandbox exception hierarchy — all sandbox failures typed for metrics/classification."""

from __future__ import annotations


class SandboxError(Exception):
    """Base exception for all sandbox errors."""


class SandboxTimeout(SandboxError):
    """Code execution exceeded the allowed time limit."""


class SandboxMemoryExceeded(SandboxError):
    """Code execution exceeded the allowed memory limit."""


class SandboxSecurityViolation(SandboxError):
    """Code violated the AST safety policy."""


class SandboxImportViolation(SandboxSecurityViolation):
    """Code attempted to import a blocked module."""


class SandboxSubprocessViolation(SandboxSecurityViolation):
    """Code attempted to spawn a subprocess."""


class SandboxSocketViolation(SandboxSecurityViolation):
    """Code attempted to open a network socket."""


class SandboxFilesystemViolation(SandboxSecurityViolation):
    """Code attempted to access restricted filesystem paths."""


class SandboxCTypesViolation(SandboxSecurityViolation):
    """Code attempted to use ctypes or similar FFI."""


class SandboxPickleViolation(SandboxSecurityViolation):
    """Code attempted unsafe deserialization."""


class SandboxIntrospectionViolation(SandboxSecurityViolation):
    """Code attempted object introspection / class hierarchy traversal."""


class SandboxThreadViolation(SandboxSecurityViolation):
    """Code attempted to spawn threads."""


class SandboxAsyncViolation(SandboxSecurityViolation):
    """Code attempted async operations not in whitelist."""


class SandboxResourceExhaustion(SandboxError):
    """Code exhausted CPU, file descriptors, or other resources."""


class SandboxDockerError(SandboxError):
    """Docker container management failure."""


class SandboxCleanupError(SandboxError):
    """Failed to clean up sandbox resources."""


CLASSIFICATION: dict[type[SandboxError], str] = {
    SandboxTimeout: "timeout",
    SandboxMemoryExceeded: "memory_exceeded",
    SandboxImportViolation: "import_violation",
    SandboxSubprocessViolation: "subprocess_violation",
    SandboxSocketViolation: "socket_violation",
    SandboxFilesystemViolation: "filesystem_violation",
    SandboxCTypesViolation: "ctypes_violation",
    SandboxPickleViolation: "pickle_violation",
    SandboxIntrospectionViolation: "introspection_violation",
    SandboxThreadViolation: "thread_violation",
    SandboxAsyncViolation: "async_violation",
    SandboxResourceExhaustion: "resource_exhaustion",
    SandboxDockerError: "docker_error",
    SandboxCleanupError: "cleanup_error",
    SandboxSecurityViolation: "security_violation",
}


def classify(error: SandboxError) -> str:
    """Classify a sandbox error into a metric-compatible string."""
    for exc_type, label in CLASSIFICATION.items():
        if isinstance(error, exc_type):
            return label
    return "unknown"
