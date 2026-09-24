"""Render REAL de Mermaid → SVG (AG3). Usa mermaid-cli (mermaid.js ejecutado en Chrome headless) instalado en
`backend/tools/mermaid_render` (`npm ci`) y el Chrome del sistema (`MERMAID_CHROME`, por defecto
/usr/bin/google-chrome). El render también es un validador REAL de sintaxis: mermaid.js rechaza lo inválido.

Requisitos del sistema (documentados en REPRODUCIBILITY.md): node ≥ 18, Google Chrome/Chromium, `npm ci`."""

from __future__ import annotations

import asyncio
import json
import os
import re
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from adaptation_swarm.schemas.errors import GenerationError

TOOL_DIR = Path(__file__).resolve().parents[2] / "tools" / "mermaid_render"
MIN_SVG_BYTES = 1_000
_NODE_DEF = re.compile(r'^\s*n\d+(?:\["|\{"|\(\[")', re.M)


@dataclass(frozen=True)
class SvgRender:
    id: str
    svg: bytes
    nodes_in_svg: int
    nodes_in_source: int


def renderer_available() -> tuple[bool, str]:
    if not (TOOL_DIR / "node_modules" / "@mermaid-js").exists():
        return False, f"faltan dependencias: ejecutar `npm ci` en {TOOL_DIR}"
    chrome = os.environ.get("MERMAID_CHROME", "/usr/bin/google-chrome")
    if not Path(chrome).exists():
        return False, f"Chrome/Chromium no encontrado en {chrome} (MERMAID_CHROME)"
    return True, "ok"


def check_svg(svg: bytes, source: str) -> SvgRender | str:
    """Verifica un SVG renderizado: tamaño mínimo, XML bien formado y un nodo por nodo del diagrama."""
    if len(svg) < MIN_SVG_BYTES:
        return f"SVG demasiado pequeño ({len(svg)} B)"
    try:
        root = ET.fromstring(svg)
    except ET.ParseError as exc:
        return f"SVG mal formado: {exc}"
    if not root.tag.endswith("svg"):
        return "el documento no es un <svg>"
    n_svg = len(re.findall(rb'class="node[ "]', svg))
    n_src = len(_NODE_DEF.findall(source))
    if n_svg != n_src:
        return f"nodos en el SVG ({n_svg}) ≠ nodos en la fuente ({n_src})"
    return SvgRender("", svg, n_svg, n_src)


async def render_batch(jobs: list[tuple[str, str]], timeout_s: float = 240.0) -> dict[str, SvgRender]:
    """`jobs` = [(id, mermaid_source)] → {id: SvgRender}. Lanza GenerationError si alguno falla al renderizar o
    no supera `check_svg` (no se acepta la fuente Mermaid como render final)."""
    ok, why = renderer_available()
    if not ok:
        raise GenerationError(f"render Mermaid no disponible: {why}")
    with tempfile.TemporaryDirectory() as td:
        jobs_path, out_dir = Path(td) / "jobs.json", Path(td) / "out"
        jobs_path.write_text(json.dumps([{"id": i, "definition": s} for i, s in jobs]), encoding="utf-8")
        proc = await asyncio.create_subprocess_exec(
            "node", str(TOOL_DIR / "render.mjs"), str(jobs_path), str(out_dir),
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, cwd=str(TOOL_DIR))
        try:
            out, err = await asyncio.wait_for(proc.communicate(), timeout=timeout_s)
        except asyncio.TimeoutError as exc:
            proc.kill()
            raise GenerationError("timeout renderizando Mermaid") from exc
        if proc.returncode != 0:
            raise GenerationError(f"mermaid-cli falló: {err.decode()[:400]}")
        results = {r["id"]: r for r in json.loads(out.decode())}
        rendered: dict[str, SvgRender] = {}
        sources = dict(jobs)
        for jid, _src in jobs:
            r = results.get(jid)
            if r is None or not r.get("ok"):
                raise GenerationError(f"Mermaid rechazó el diagrama {jid}: {(r or {}).get('error')}")
            svg = (out_dir / f"{jid}.svg").read_bytes()
            chk = check_svg(svg, sources[jid])
            if isinstance(chk, str):
                raise GenerationError(f"render inválido {jid}: {chk}")
            rendered[jid] = SvgRender(jid, svg, chk.nodes_in_svg, chk.nodes_in_source)
        return rendered
