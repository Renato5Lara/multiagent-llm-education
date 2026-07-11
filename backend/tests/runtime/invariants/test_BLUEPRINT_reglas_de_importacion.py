"""Las reglas de importación del BLUEPRINT como tests de contrato.

El lint es parte de la suite (ADR-0005 §5 rev. 2): si una regla física de
la arquitectura se viola, el CI falla sin tooling adicional.
"""

import re
from pathlib import Path

_RUNTIME = Path(__file__).resolve().parents[3] / "runtime"

_CAPACIDADES = {
    "modelar",
    "diagnosticar",
    "orientar",
    "adaptar",
    "tutorizar",
    "evaluar",
    "remediar",
    "validar",
}


def _fuentes(subruta: str = "") -> list[Path]:
    base = _RUNTIME / subruta if subruta else _RUNTIME
    return sorted(p for p in base.rglob("*.py")) if base.exists() else []


def _importa(texto: str, modulo: str) -> bool:
    return bool(
        re.search(rf"^\s*(import|from)\s+{re.escape(modulo)}(\.|\s|$)", texto, re.M)
    )


class TestBLUEPRINT_LimitesFisicos:
    def test_langgraph_solo_existe_dentro_de_engine(self):
        # RFC-0001 §1: el motor es un detalle del Graph Engine.
        for fuente in _fuentes():
            if _importa(fuente.read_text(encoding="utf-8"), "langgraph"):
                assert "engine" in fuente.parts, f"langgraph fuera de engine/: {fuente}"

    def test_el_runtime_jamas_importa_la_plataforma(self):
        # P11 / D-001: nada del runtime importa app/ ni al Legacy.
        for fuente in _fuentes():
            assert not _importa(
                fuente.read_text(encoding="utf-8"), "app"
            ), f"import de la plataforma en: {fuente}"

    def test_el_kernel_es_puro(self):
        # BLUEPRINT: kernel/ no importa domain, engine, boundary ni langgraph.
        for fuente in _fuentes("kernel"):
            texto = fuente.read_text(encoding="utf-8")
            for prohibido in (
                "runtime.domain",
                "runtime.engine",
                "runtime.boundary",
                "langgraph",
            ):
                assert not _importa(
                    texto, prohibido
                ), f"{prohibido} dentro del Kernel: {fuente}"

    def test_P3_ninguna_capacidad_importa_a_otra(self):
        for fuente in _fuentes("domain"):
            partes = fuente.relative_to(_RUNTIME / "domain").parts
            propia = partes[0] if len(partes) > 1 else None
            texto = fuente.read_text(encoding="utf-8")
            for otra in _CAPACIDADES - ({propia} if propia else set()):
                assert not _importa(
                    texto, f"runtime.domain.{otra}"
                ), f"P3: {fuente} importa a la capacidad {otra}"

    def test_ADR_0001_json_dumps_solo_en_canonical(self):
        # Único punto de serialización (orden del tesista, 2026-07-11).
        for fuente in _fuentes():
            if "json.dumps" in fuente.read_text(encoding="utf-8"):
                assert (
                    fuente.name == "canonical.py"
                ), f"json.dumps fuera del punto único: {fuente}"
