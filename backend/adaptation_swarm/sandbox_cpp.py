"""Sandbox de C++ (AG2): compila con g++ -std=c++17 -Wall -Wextra y EJECUTA el código dentro de un contenedor
podman/docker sin red, con memoria/PIDs limitados, raíz de solo lectura y sin capacidades. Imagen:
`upao-cpp-sandbox` (tools/cpp_sandbox/Dockerfile). Además hay una política estática previa (cabeceras
permitidas, sin llamadas al sistema)."""

from __future__ import annotations

import asyncio
import re
import time
from dataclasses import dataclass

from adaptation_swarm.config import SETTINGS

IMAGE = "upao-cpp-sandbox:latest"
ALLOWED_HEADERS = frozenset({
    "iostream", "vector", "string", "algorithm", "cassert", "cmath", "numeric", "map", "set", "unordered_map",
    "unordered_set", "sstream", "utility", "functional", "limits", "climits", "cstdint", "array", "stack", "queue",
    "iomanip", "tuple", "cctype", "cstdlib", "cstddef", "optional", "string_view", "cstdio", "cstring", "stdexcept",
    "initializer_list", "iterator", "cstdarg", "type_traits", "typeinfo", "variant",
})
_INCLUDE = re.compile(r'^\s*#\s*include\s*([<"])([^>"]+)[>"]', re.M)
_FORBIDDEN = re.compile(
    r"(?<![\w:.>])(system|popen|fork|execv?[lpe]*|dlopen|socket|asm|__asm__|remove|rename|fopen|freopen)\s*\(|"
    r"#\s*(embed|pragma|import)\b|__has_include|\bstd::(thread|filesystem|ofstream|ifstream|fstream)\b")


def policy_violations(source: str) -> list[str]:
    out: list[str] = []
    for quote, header in _INCLUDE.findall(source):
        if quote == '"' or header not in ALLOWED_HEADERS:
            out.append(f"cabecera no permitida: {quote}{header}")
    if _FORBIDDEN.search(source):
        out.append(f"construcción prohibida: {_FORBIDDEN.search(source).group(0).strip()}")
    return out


@dataclass(frozen=True)
class CppResult:
    status: str            # success | compile_error | runtime_error | timeout | security_violation | infrastructure_error
    stdout: str
    stderr: str
    total_ms: float
    warnings: int

    @property
    def success(self) -> bool:
        return self.status == "success"


_SCRIPT = (
    "cat > /tmp/main.cpp; "
    "if ! g++ -std=c++17 -O0 -Wall -Wextra -o /tmp/a.out /tmp/main.cpp 2>/tmp/cerr; then "
    "echo '@@COMPILE_ERROR' >&2; head -c 2000 /tmp/cerr >&2; exit 90; fi; "
    "grep -c 'warning:' /tmp/cerr | sed 's/^/@@WARNINGS=/' ; "
    "timeout 5 /tmp/a.out; exit $?"
)


class CppSandbox:
    def __init__(self, image: str = IMAGE, binary: str | None = None):
        self.image, self.binary = image, binary or SETTINGS.sandbox_bin

    async def run(self, source: str, *, timeout_s: float = 30.0) -> CppResult:
        t0 = time.perf_counter()
        viol = policy_violations(source)
        if viol:
            return CppResult("security_violation", "", "; ".join(viol), 0.0, 0)
        cmd = [self.binary, "run", "--rm", "-i", "--network", "none", "--memory", "256m", "--pids-limit", "64",
               "--read-only", "--tmpfs", "/tmp:rw,exec,size=64m", "--cap-drop", "ALL",
               "--security-opt", "no-new-privileges", self.image, "sh", "-c", _SCRIPT]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd, stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            out, err = await asyncio.wait_for(proc.communicate(source.encode()), timeout=timeout_s)
        except FileNotFoundError:
            return CppResult("infrastructure_error", "", f"{self.binary} no disponible", 0.0, 0)
        except asyncio.TimeoutError:
            return CppResult("timeout", "", "excedió el tiempo límite", (time.perf_counter() - t0) * 1000, 0)
        so, se = out.decode(errors="replace"), err.decode(errors="replace")
        ms = (time.perf_counter() - t0) * 1000
        warn = int(m.group(1)) if (m := re.search(r"@@WARNINGS=(\d+)", so)) else 0
        so = re.sub(r"@@WARNINGS=\d+\n?", "", so)
        if proc.returncode == 0:
            return CppResult("success", so, se, ms, warn)
        if proc.returncode == 90:
            return CppResult("compile_error", so, se, ms, warn)
        if proc.returncode in (124, 137, 143):
            return CppResult("timeout", so, se, ms, warn)
        if "Error: image" in se or "unable to" in se.lower() and "image" in se.lower():
            return CppResult("infrastructure_error", so, se[:400], ms, warn)
        return CppResult("runtime_error", so, se[:600], ms, warn)
