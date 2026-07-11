"""Serialización canónica (ADR-0001).

Los bytes canónicos son la fuente para el hash, la comparación de replay
(R3) y la firma de integridad; cualquier otra representación es
proyección. Reglas: JSON UTF-8 con claves ordenadas y sin espacio no
significativo; strings NFC; Decimal a escala fija; Enum por valor;
EntryId en su forma textual; dataclasses por campos.

**El float binario está prohibido en el registro** (A3): su
representación no es reproducible entre plataformas. Los payloads usan
entero, texto o Decimal.
"""

from __future__ import annotations

import dataclasses
import json
import unicodedata
from decimal import Decimal
from enum import Enum
from typing import Any, Mapping

from runtime.kernel.state.entries import EntryId

#: Escala vigente de la política de precisión (ADR-0001 §4, valor inicial).
#: Cambiarla es nueva versión de política registrada, jamás edición local.
ESCALA_DECIMAL = Decimal("0.0001")


def _plano(valor: Any) -> Any:
    if isinstance(valor, EntryId):
        return str(valor)
    if isinstance(valor, Enum):
        return valor.value
    if isinstance(valor, Decimal):
        return str(valor.quantize(ESCALA_DECIMAL))
    if isinstance(valor, float):
        raise ValueError(
            "ADR-0001: float binario prohibido en el registro — usar "
            "Decimal, entero o texto (A3)"
        )
    if isinstance(valor, str):
        return unicodedata.normalize("NFC", valor)
    if isinstance(valor, (int, bool)) or valor is None:
        return valor
    if dataclasses.is_dataclass(valor) and not isinstance(valor, type):
        return {
            campo.name: _plano(getattr(valor, campo.name))
            for campo in dataclasses.fields(valor)
        }
    if isinstance(valor, Mapping):
        return {
            unicodedata.normalize("NFC", str(clave)): _plano(v)
            for clave, v in valor.items()
        }
    if isinstance(valor, (tuple, list)):
        return [_plano(v) for v in valor]
    raise ValueError(
        f"ADR-0001: tipo no serializable en el registro: {type(valor).__name__}"
    )


def a_canonico(valor: Any) -> bytes:
    """La forma canónica única: mismo valor → mismos bytes, siempre."""
    return json.dumps(
        _plano(valor), ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
