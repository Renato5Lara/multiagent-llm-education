"""C++ real (compilado y ejecutado en contenedor sin red) y render real de Mermaid a SVG.

El aislamiento del sandbox de C++ se comprueba EJECUTANDO dentro del contenedor real un programa que intenta salir a la red, escribir en la raíz y
leer archivos del host (no se infiere de los flags). Mermaid distingue el rechazo del PARSER (mermaid.js) de un fallo de Chrome/Puppeteer."""

import asyncio
import errno
import json
import re
import subprocess

import pytest

from adaptation_swarm import sandbox_cpp
from adaptation_swarm.agents.ag2_code_agent import CodeAgent, _extract_cpp
from adaptation_swarm.config import SETTINGS
from adaptation_swarm.multimodal.anchor import build_anchor
from adaptation_swarm.multimodal.render import TOOL_DIR, check_svg, render_batch, renderer_available
from adaptation_swarm.sandbox_cpp import CppSandbox, policy_violations
from adaptation_swarm.schemas.errors import GenerationError
from tests.adaptation_swarm.conftest import WHILE_ID

pytestmark = pytest.mark.integration
GOOD = '#include <iostream>\n#include <cassert>\nint suma(int a, int b) { return a + b; }\nint main() { assert(suma(2, 3) == 5); std::cout << "OK\\n"; }\n'


async def test_cpp_sandbox_compiles_and_runs_real_code():
    r = await CppSandbox().run(GOOD)
    assert r.success and r.stdout.strip() == "OK" and r.warnings == 0


async def test_cpp_sandbox_reports_compile_error_runtime_error_timeout_and_policy():
    sb = CppSandbox()
    assert (await sb.run("int main() { return 1 +; }\n")).status == "compile_error"
    assert (await sb.run("#include <cassert>\nint main() { assert(1 == 2); }\n")).status == "runtime_error"
    assert (await sb.run("int main() { while (true) {} }\n")).status == "timeout"
    ev = await sb.run('#include <cstdlib>\n#include <fstream>\nint main() { system("ls"); }\n')
    assert ev.status == "security_violation" and "system" in ev.stderr


def test_cpp_static_policy_rejects_includes_outside_the_allowlist():
    assert policy_violations('#include "/etc/passwd"\nint main(){}') and policy_violations("#include <sys/socket.h>\nint main(){}")


# Programa que INTENTA lo que el contenedor debe impedir. Solo hace `stat`/`open(O_EXCL)` de sondeo; no destruye nada. Solo intenta la conexión si la
# única interfaz es `lo`: si el aislamiento de red faltara, la prueba falla en la comprobación de interfaces SIN llegar a enviar tráfico a Internet.
_ISOLATION_PROBE = r"""
#include <arpa/inet.h>
#include <cerrno>
#include <cstdio>
#include <cstring>
#include <dirent.h>
#include <fcntl.h>
#include <iostream>
#include <netinet/in.h>
#include <string>
#include <sys/select.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <unistd.h>

static void probe_write(const char* label, const char* path) {
    int fd = open(path, O_WRONLY | O_CREAT | O_EXCL, 0600);
    if (fd >= 0) { std::cout << label << "=OK\n"; close(fd); unlink(path); }
    else std::cout << label << "=FAIL errno=" << errno << "\n";
}

int main() {
    std::string ifaces;
    if (DIR* d = opendir("/sys/class/net")) {
        while (dirent* e = readdir(d)) if (e->d_name[0] != '.') ifaces += (ifaces.empty() ? "" : ",") + std::string(e->d_name);
        closedir(d);
    }
    std::cout << "ifaces=" << ifaces << "\n";
    int s = socket(AF_INET, SOCK_STREAM, 0);
    std::cout << "socket=" << (s >= 0 ? "OK" : "FAIL") << "\n";
    if (ifaces == "lo") {
        sockaddr_in a{}; a.sin_family = AF_INET; a.sin_port = htons(53); inet_pton(AF_INET, "1.1.1.1", &a.sin_addr);
        fcntl(s, F_SETFL, O_NONBLOCK);
        int err = connect(s, reinterpret_cast<sockaddr*>(&a), sizeof a) == 0 ? 0 : errno;
        std::cout << "connect_errno=" << err << "\n";
    } else std::cout << "connect_errno=SKIPPED (hay una interfaz distinta de lo)\n";
    probe_write("root_write", "/rootfs_write_probe");
    probe_write("etc_write", "/etc/rootfs_write_probe");
    probe_write("tmp_write", "/tmp/tmpfs_write_probe");
    struct stat st{};
    int lib = stat("HOST_LIBRARY", &st) == 0 ? 0 : errno;
    std::cout << "host_library_errno=" << lib << "\n";
    std::cout << "host_home_errno=" << (access("/var/home", F_OK) == 0 ? 0 : errno) << "\n";
    if (FILE* f = fopen("/proc/self/status", "r")) {
        char line[256];
        while (fgets(line, sizeof line, f)) {
            if (!strncmp(line, "CapEff:", 7)) std::cout << "cap_eff=" << std::string(line + 8, strcspn(line + 8, "\n")) << "\n";
            if (!strncmp(line, "NoNewPrivs:", 11)) std::cout << "no_new_privs=" << std::string(line + 12, strcspn(line + 12, "\n")) << "\n";
        }
        fclose(f);
    }
    std::cout << "PROBE_DONE\n";
}
"""


def _sandbox_containers() -> list[str]:
    """Contenedores (en cualquier estado) creados a partir de la imagen del sandbox de C++."""
    out = subprocess.run([SETTINGS.sandbox_bin, "ps", "-a", "--filter", f"ancestor={sandbox_cpp.IMAGE}", "--format", "{{.ID}}"],
                         capture_output=True, text=True, check=True).stdout
    return sorted(out.split())


@pytest.fixture(scope="module")
def isolation_probe() -> dict:
    """Ejecuta UNA vez la sonda en el contenedor real. La política estática se desactiva a propósito (bloquea `socket(` y `<sys/socket.h>`):
    lo que se prueba aquí es la capa del CONTENEDOR (red, raíz, host, capacidades), no la política. Un fallo de infraestructura FALLA, no se omite."""
    before = _sandbox_containers()
    source = _ISOLATION_PROBE.replace("HOST_LIBRARY", str(SETTINGS.library_root))
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(sandbox_cpp, "policy_violations", lambda src: [])
        result = asyncio.run(CppSandbox().run(source))
    after = _sandbox_containers()
    assert result.status == "success" and "PROBE_DONE" in result.stdout, f"la sonda no se ejecutó en el contenedor ({result.status}): {result.stderr}"
    return {"values": dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line), "before": before, "after": after}


def test_cpp_sandbox_has_no_network_interface_and_an_outbound_connect_is_unreachable(isolation_probe):
    v = isolation_probe["values"]
    assert v["ifaces"] == "lo", f"el contenedor tiene interfaces de red: {v['ifaces']}"
    assert v["socket"] == "OK"                                                     # crear el socket es posible: el intento de conexión ocurrió de verdad
    assert v["connect_errno"] == str(errno.ENETUNREACH), f"connect a 1.1.1.1:53 -> {v['connect_errno']} (se esperaba ENETUNREACH)"


def test_cpp_sandbox_root_filesystem_is_read_only_and_only_tmp_is_writable(isolation_probe):
    v = isolation_probe["values"]
    assert v["root_write"] == v["etc_write"] == f"FAIL errno={errno.EROFS}", (v["root_write"], v["etc_write"])       # EROFS, no un simple permiso denegado
    assert v["tmp_write"] == "OK"                                                  # control: el tmpfs sí es escribible, así que las sondas funcionan


def test_cpp_sandbox_cannot_see_host_files(isolation_probe):
    v = isolation_probe["values"]
    assert v["host_library_errno"] == v["host_home_errno"] == str(errno.ENOENT), (v["host_library_errno"], v["host_home_errno"])


def test_cpp_sandbox_drops_all_capabilities_and_forbids_gaining_privileges(isolation_probe):
    v = isolation_probe["values"]
    assert int(v["cap_eff"], 16) == 0 and v["no_new_privs"] == "1"


def test_cpp_sandbox_container_is_removed_after_the_probe(isolation_probe):
    assert isolation_probe["after"] == isolation_probe["before"], f"quedaron contenedores: {set(isolation_probe['after']) - set(isolation_probe['before'])}"


def test_check_cpp_static_rules():
    anchor = build_anchor(concept_id="c", concept_title="Suma", learning_objective_id="l", learning_objective_title="Operadores",
                          reference_code="def suma(a, b):\n    return a + b\n")
    tests = "assert suma(2, 3) == 5\nassert suma(0, 0) == 0\n"
    ok = '#include <cassert>\nint suma(int a, int b) { return a + b; }\nint main() { assert((suma(2, 3) == 5)); assert((suma(0, 0) == 0)); }\n'
    assert CodeAgent.check_cpp(ok, anchor, tests, 0) is None
    assert CodeAgent.check_cpp(ok.replace("assert((suma(2, 3) == 5))", "assert(suma(2, 3) == 5)"), anchor, tests, 0) is None   # coma dentro de una llamada: segura
    unsafe = ok.replace("assert((suma(0, 0) == 0))", "assert(suma(0, 0) == std::vector<int>{0, 0}[0])")
    assert "paréntesis dobles" in CodeAgent.check_cpp(unsafe, anchor, tests, 0)                 # coma de llaves: rompe la macro
    assert "int main" in CodeAgent.check_cpp("int suma(int a,int b){return a+b;}", anchor, tests, 0)
    assert "Python" in CodeAgent.check_cpp("def suma(a, b):\n    return a\nint main(){}", anchor, tests, 0)
    assert "asserts" in CodeAgent.check_cpp(ok.replace("assert((suma(0, 0) == 0));", ""), anchor, tests, 0)
    assert "comentarios" in CodeAgent.check_cpp(ok, anchor, tests, 1)                       # v1 exige comentarios
    assert CodeAgent.check_cpp("// c\n" + ok, anchor, tests, 0) is None                    # v0 admite uno (centinela)
    assert "como máximo" in CodeAgent.check_cpp("// a\n// b\n" + ok, anchor, tests, 0)
    assert _extract_cpp("```cpp\nint main(){}\n```") == "int main(){}\n"


def test_library_cpp_is_real_cpp_translated_from_the_python_variant(store):
    if store.cpp(WHILE_ID, 0) is None:
        pytest.skip("la versión de biblioteca abierta no incluye C++ (≤ lib-v5)")
    for v in range(3):
        cpp, py = store.cpp(WHILE_ID, v), store.code(WHILE_ID, v)
        assert cpp.entry["path"].endswith(".cpp") and cpp.entry["derived_from"] == py.sha256
        assert "int main" in cpp.text and "def " not in cpp.text and cpp.text != py.text
        val = cpp.entry["validation"]
        assert val["language"] == "c++17" and val["sandbox_status"] == "success"


async def test_library_cpp_recompiles_and_runs_in_the_sandbox(store):
    if store.cpp(WHILE_ID, 0) is None:
        pytest.skip("la versión de biblioteca abierta no incluye C++ (≤ lib-v5)")
    for v in range(3):
        r = await CppSandbox().run(store.cpp(WHILE_ID, v).text)
        assert r.success, r.stderr


async def test_real_mermaid_render_produces_valid_svg_per_node():
    ok, why = renderer_available()
    assert ok, why
    src = 'flowchart TD\n    n1(["Inicio"])\n    n2{"while i <= n"}\n    n1 --> n2\n    n3(["Fin"])\n    n2 -->|"No"| n3\n'
    out = await render_batch([("a", src)])
    r = out["a"]
    assert r.svg.startswith(b"<svg") and len(r.svg) > 1000 and r.nodes_in_svg == r.nodes_in_source == 3


VALID = 'flowchart TD\n    n1["a"]\n    n2["b"]\n    n1 --> n2\n'
# (id, fuente, texto que mermaid.js debe dar). Inequívocamente inválidas: sintaxis rota, tipo de diagrama inexistente, arista incompleta.
INVALID = [
    ("parse", "flowchart TD\n    n1[[[ esto no es mermaid válido ->>>\n", "Parse error on line 2"),
    ("unknown", "esto no es un diagrama mermaid en absoluto\n", "No diagram type detected"),
    ("edge", "flowchart TD\n    n1 --> \n    --> n2 [\n", "Parse error on line 3"),
]


def _origin(message: str) -> str:
    """De dónde viene un GenerationError de `render_batch` (los tres mensajes que emite render.py)."""
    if message.startswith("mermaid-cli falló"):
        return "chrome-o-puppeteer"                     # el proceso node terminó con error (Chrome no inició, Puppeteer no conectó...)
    if message.startswith("timeout"):
        return "timeout"
    if message.startswith("Mermaid rechazó el diagrama"):
        return "parser" if re.search(r"Parse error on line|No diagram type detected", message) else "rechazo-sin-firma-del-parser"
    return "otro"


def test_mermaid_parser_rejects_invalid_diagrams_directly_without_chrome():
    """`mermaid.parse()` en Node puro (sin navegador): separa el rechazo del parser de cualquier fallo de Chrome/Puppeteer. Límite: sin DOM, mermaid.js
    solo valida diagramas SIN etiquetas (con `n1["a"]` lanza `DOMPurify.addHook is not a function`); por eso el control válido es `a --> b` y de los
    inválidos se exige el mensaje exacto del parser, de modo que ese TypeError nunca se confunde con un rechazo."""
    ok, why = renderer_available()
    assert ok, why
    script = ('import mermaid from "mermaid";'
              'const out = [];'
              'for (const c of JSON.parse(process.argv[1])) {'
              '  try { await mermaid.parse(c.source); out.push({id: c.id, ok: true}); }'
              '  catch (e) { out.push({id: c.id, ok: false, error: String(e.message || e).slice(0, 300)}); } }'
              'process.stdout.write(JSON.stringify(out));')
    cases = [{"id": "valid", "source": "flowchart TD\n    a --> b\n"}] + [{"id": i, "source": src} for i, src, _ in INVALID]
    run = subprocess.run(["node", "--input-type=module", "-e", script, json.dumps(cases)], cwd=TOOL_DIR, capture_output=True, text=True, timeout=60)
    assert run.returncode == 0, f"node/mermaid no arrancó (entorno, no parser): {run.stderr[:400]}"
    res = {r["id"]: r for r in json.loads(run.stdout)}
    assert res["valid"]["ok"] is True
    for cid, _src, expected in INVALID:
        assert res[cid]["ok"] is False and expected in res[cid]["error"], (cid, res[cid])


def test_render_tool_reports_chrome_started_and_the_parser_rejected_the_invalid_diagram(tmp_path):
    """El binario real (`render.mjs`, mermaid-cli + Chrome + Puppeteer) con un válido y un inválido en la MISMA sesión: que el válido se renderice prueba
    que Chrome y Puppeteer funcionan; el inválido debe ser rechazado por el parser. Si Chrome no inicia, esta prueba FALLA (no se acepta como rechazo)."""
    ok, why = renderer_available()
    assert ok, why
    jobs, out_dir = tmp_path / "jobs.json", tmp_path / "out"
    jobs.write_text(json.dumps([{"id": "valid", "definition": VALID}, {"id": "bad", "definition": INVALID[0][1]}]), encoding="utf-8")
    run = subprocess.run(["node", str(TOOL_DIR / "render.mjs"), str(jobs), str(out_dir)], cwd=TOOL_DIR, capture_output=True, text=True, timeout=180)
    assert run.returncode == 0, f"Chrome/Puppeteer no iniciaron (problema de entorno): {run.stderr[:400]}"
    res = {r["id"]: r for r in json.loads(run.stdout)}
    assert res["valid"]["ok"] is True and (out_dir / "valid.svg").stat().st_size > 1000
    assert res["bad"]["ok"] is False and INVALID[0][2] in res["bad"]["error"], res["bad"]
    assert not (out_dir / "bad.svg").exists()


@pytest.mark.parametrize("cid, source, expected", INVALID, ids=[i for i, _, _ in INVALID])
async def test_real_renderer_rejects_invalid_mermaid_because_of_the_parser_and_not_chrome(cid, source, expected):
    ok, why = renderer_available()
    assert ok, why
    control = await render_batch([("control", VALID)])                    # Chrome y Puppeteer funcionan: un fallo de entorno rompe AQUÍ, no se toma por rechazo
    assert control["control"].svg.startswith(b"<svg")
    with pytest.raises(GenerationError) as exc:
        await render_batch([(cid, source)])
    message = str(exc.value)
    assert _origin(message) == "parser", f"el rechazo no viene del parser de Mermaid: {message[:300]}"
    assert expected in message and cid in message


def test_check_svg_rejects_tiny_malformed_and_mismatched_svgs():
    src = 'flowchart TD\n    n1["a"]\n    n2["b"]\n    n1 --> n2\n'
    assert "pequeño" in check_svg(b"<svg/>", src)
    assert "mal formado" in check_svg(b"<svg>" + b"x" * 2000, src)
    fake = b'<svg xmlns="http://www.w3.org/2000/svg">' + b'<g class="node default"/>' + b" " * 1500 + b"</svg>"
    assert "nodos" in check_svg(fake, src)
