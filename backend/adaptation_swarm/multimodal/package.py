"""Paquete multimodal final (RF05): código + diagrama Mermaid + texto + audio, con la cadena de
hashes que garantiza que las cuatro piezas se refieren al mismo concepto y versión:

    diagrama.derived_from == sha256(código)        (el diagrama sale del AST de ESE código)
    audio.derived_from   == sha256(texto)          (el audio narra EXACTAMENTE ese texto)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from adaptation_swarm.schemas.errors import LibraryIntegrityError
from adaptation_swarm.schemas.ids import package_id as make_package_id


@dataclass(frozen=True)
class MultimodalPackage:
    package_id: str
    cycle_id: str
    concept_id: str
    library_version: str
    S: tuple[int, ...]
    code: dict[str, Any]
    diagram: dict[str, Any]
    text: dict[str, Any]
    audio: dict[str, Any]
    chain_valid: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "package_id": self.package_id, "cycle_id": self.cycle_id, "concept_id": self.concept_id,
            "library_version": self.library_version, "S": list(self.S), "chain_valid": self.chain_valid,
            "code": self.code, "diagram": self.diagram, "text": self.text, "audio": self.audio,
        }


def check_chain(code: dict, diagram: dict, text: dict, audio: dict) -> None:
    if diagram["derived_from"] != code["sha256"]:
        raise LibraryIntegrityError("cadena rota: el diagrama no deriva del código del paquete")
    if audio["derived_from"] != text["sha256"]:
        raise LibraryIntegrityError("cadena rota: el audio no narra el texto del paquete")
    if not (code["concept_id"] == diagram["concept_id"] == text["concept_id"] == audio["concept_id"]):
        raise LibraryIntegrityError("las piezas pertenecen a conceptos distintos")


def assemble(
    *, cycle_id: str, concept_id: str, library_version: str, S: tuple[int, ...],
    code: dict, diagram: dict, text: dict, audio: dict,
) -> MultimodalPackage:
    check_chain(code, diagram, text, audio)
    pid = make_package_id(cycle_id, code["sha256"], diagram["sha256"], text["sha256"], audio["sha256"])
    return MultimodalPackage(pid, cycle_id, concept_id, library_version, S, code, diagram, text, audio, True)
