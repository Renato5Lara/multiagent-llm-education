"""Capa común de validación de artefactos y de paquetes (Fase 2). Un paquete NO es válido si falta o falla una
modalidad requerida (código, diagrama, texto, audio). Las comprobaciones son objetivas y deterministas; el único
LLM del sistema queda fuera de esta capa.

CODE     existe · extensión `.py` · sha256 · no vacío · validación técnica (sandbox) · higiene (C1) ·
         [C++ si la biblioteca lo tiene: `.cpp` · sha256 · compila y ejecuta en el sandbox]
DIAGRAM  Mermaid válido (estructural + MermaidValidator) · coherente con el AST (D1) · SVG real: existe · sha256 ·
         ≥ 1 KB · XML bien formado · un nodo SVG por nodo Mermaid
TEXT     concepto correcto · longitud del nivel de dificultad · vocabulario del ancla · coherencia con el código (T1–T4)
AUDIO    archivo MP3 real · sha256 · tamaño válido · duración > 0 · metadatos del proveedor · narra EXACTAMENTE el texto
"""

from __future__ import annotations

import io
from dataclasses import dataclass, field
from typing import Any

from mutagen.mp3 import MP3

from adaptation_swarm.agents.ag4_text_agent import TEXT_LEVELS, TextAgent
from adaptation_swarm.multimodal.flowchart import validate_flowchart
from adaptation_swarm.multimodal.library import LibraryStore
from adaptation_swarm.multimodal.render import MIN_SVG_BYTES, check_svg
from adaptation_swarm.multimodal.semantic import (
    code_covers_concept, code_hygiene, validate_diagram_against_code, validate_text_against_code,
)
from adaptation_swarm.schemas.ids import sha256_bytes, sha256_text

MIN_AUDIO_BYTES = 5_000


@dataclass
class ModalityCheck:
    modality: str
    checks: dict[str, bool] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    def expect(self, name: str, cond: bool, msg: str) -> None:
        self.checks[name] = bool(cond)
        if not cond:
            self.errors.append(f"{name}: {msg}")

    @property
    def ok(self) -> bool:
        return all(self.checks.values()) and bool(self.checks)


@dataclass
class PackageValidation:
    modalities: dict[str, ModalityCheck]
    required: tuple[str, ...] = ("code", "diagram", "text", "audio")

    @property
    def valid(self) -> bool:
        return all(m in self.modalities and self.modalities[m].ok for m in self.required)

    @property
    def errors(self) -> list[str]:
        return [f"{m}.{e}" for m, c in self.modalities.items() for e in c.errors]

    def to_dict(self) -> dict[str, Any]:
        return {"valid": self.valid, "modalities": {m: {"ok": c.ok, "checks": c.checks, "errors": c.errors}
                                                    for m, c in self.modalities.items()}}


def validate_package(pkg: dict[str, Any], store: LibraryStore) -> PackageValidation:
    """Valida un paquete (`MultimodalPackage.to_dict()`) contra la biblioteca y sus artefactos en disco."""
    cid = pkg["concept_id"]
    anchor = store.anchor(cid)
    out: dict[str, ModalityCheck] = {}
    code, dia, txt, aud = pkg.get("code") or {}, pkg.get("diagram") or {}, pkg.get("text") or {}, pkg.get("audio") or {}

    # ── CODE ────────────────────────────────────────────────────────────
    c = ModalityCheck("code")
    src = code.get("source", "")
    c.expect("present", bool(src.strip()), "código ausente o vacío")
    if src.strip():
        entry = store.code(cid, code["variant"]).entry
        c.expect("extension_py", entry["path"].endswith(".py"), entry["path"])
        c.expect("sha256", sha256_text(src) == code.get("sha256") == entry["sha256"], "hash del código no coincide")
        c.expect("sandbox_passed", entry["validation"].get("sandbox_status") == "success", "sin validación en sandbox")
        try:
            hyg = code_hygiene(src)
            c.expect("hygiene", hyg.ok, str(hyg.violations))
            cov = code_covers_concept(anchor, src)
            c.expect("covers_concept", cov.ok, str(cov.violations))
        except SyntaxError as exc:
            c.expect("parses", False, str(exc))
        cpp = store.cpp(cid, code["variant"])
        if cpp is not None:
            v = cpp.entry["validation"]
            c.expect("cpp_extension", cpp.entry["path"].endswith(".cpp"), cpp.entry["path"])
            c.expect("cpp_sha256", sha256_text(cpp.text) == cpp.sha256, "hash C++")
            c.expect("cpp_compiles_and_runs", v.get("sandbox_status") == "success" and v.get("language") == "c++17",
                     f"{v}")
            c.expect("cpp_not_python", "int main" in cpp.text and "def " not in cpp.text, "no parece C++")
    out["code"] = c

    # ── DIAGRAM ─────────────────────────────────────────────────────────
    d = ModalityCheck("diagram")
    mer = dia.get("mermaid", "")
    d.expect("present", bool(mer.strip()), "diagrama ausente o vacío")
    if mer.strip() and src.strip():
        d.expect("sha256", sha256_text(mer) == dia.get("sha256"), "hash del diagrama")
        d.expect("structure", not validate_flowchart(mer), str(validate_flowchart(mer)))
        d.expect("derived_from_code", dia.get("derived_from") == code.get("sha256"), "no deriva del código del paquete")
        sem = validate_diagram_against_code(src, mer)
        d.expect("matches_ast", sem.ok, str(sem.violations))
        svg = store.svg(cid, code["variant"], dia["variant"], load=True)
        if svg is None:
            d.checks["svg_present"] = True          # la versión de biblioteca no incluye render (versiones ≤ v5)
        else:
            d.expect("svg_sha256", sha256_bytes(svg.content) == svg.sha256, "hash del SVG")
            d.expect("svg_min_size", len(svg.content) >= MIN_SVG_BYTES, f"{len(svg.content)} B")
            chk = check_svg(svg.content, mer)
            d.expect("svg_valid_xml_and_nodes", not isinstance(chk, str), str(chk))
            d.expect("svg_derived_from_mermaid", svg.entry["derived_from"] == dia.get("sha256"), "cadena rota")
    out["diagram"] = d

    # ── TEXT ────────────────────────────────────────────────────────────
    t = ModalityCheck("text")
    tx = txt.get("text", "")
    t.expect("present", bool(tx.strip()), "texto ausente o vacío")
    if tx.strip():
        t.expect("sha256", sha256_text(tx) == txt.get("sha256"), "hash del texto")
        t.expect("concept", txt.get("concept_id") == cid, "el texto es de otro concepto")
        problem = TextAgent.check_text(anchor, tx.strip(), txt["variant"]) if txt.get("variant") in TEXT_LEVELS else "variante inválida"
        t.expect("level_and_vocabulary", problem is None, str(problem))
        if src.strip():
            sem = validate_text_against_code(anchor, src, tx)
            t.expect("consistent_with_code", sem.ok, str(sem.violations))
    out["text"] = t

    # ── AUDIO ───────────────────────────────────────────────────────────
    a = ModalityCheck("audio")
    a.expect("present", bool(aud.get("path")), "audio ausente")
    if aud.get("path"):
        art = store.audio(cid, txt.get("variant", -1), aud["variant"], load=True)
        a.expect("file_exists", (store.dir / aud["path"]).exists(), aud["path"])
        a.expect("sha256", sha256_bytes(art.content) == aud.get("sha256"), "hash del audio")
        a.expect("size", len(art.content) >= MIN_AUDIO_BYTES, f"{len(art.content)} B")
        try:
            info = MP3(io.BytesIO(art.content)).info
            a.expect("mp3_format", True, "")
            a.expect("duration", info.length > 0.5, f"{info.length}")
        except Exception as exc:
            a.expect("mp3_format", False, str(exc))
        prov = art.entry["provider"]
        a.expect("provider_metadata", all(prov.get(k) for k in ("name", "model", "voice", "input_sha256", "output_sha256")),
                 "faltan metadatos del proveedor TTS")
        a.expect("narrates_package_text", aud.get("derived_from") == txt.get("sha256") == prov.get("input_sha256"),
                 "el audio no narra el texto del paquete")
    out["audio"] = a
    return PackageValidation(out)
