"""HF-0 / Exp-1 — HuggingFaceProvider vs OpenAIProvider sobre Diagnosticar.

Contexto (memoria del proyecto, `fase_produccion_experimental_ia_2026_08_03`
y el informe HF-0 de esta sesión): la fase de producción experimental
permite evaluar proveedores IA alternativos SIN tocar la arquitectura
validada. HF-0 auditó las 8 capacidades con `productor_llm.py` y encontró
que solo Diagnosticar/Remediar/Orientar están conectadas al Boundary real
(`boundary/inbound/productores.py`), y que Diagnosticar es el candidato de
menor riesgo para empezar: su `confianza` declarada por el LLM se
recalibra después (`calibracion.py`, H10) — el kernel queda parcialmente
aislado de lo que el proveedor declare, a diferencia de Remediar/Orientar
que usan la confianza cruda directo en la deliberación D1.

Este script NO toca `runtime/` ni `boundary/inbound/productores.py`. Es un
spike aislado — mismo patrón que `ProveedorCapturador` en
`consenso_barrido_evidencia_llm.py`: un proveedor experimental definido
SOLO aquí, nunca en `runtime/`, porque CLAUDE.md exige evidencia antes de
integrar cualquier capacidad de forma permanente ("si no la produce, queda
descartada o aislada como spike, nunca incorporada 'porque ya está
hecha'").

`HuggingFaceProvider` implementa el contrato `LLMProvider` (modelo,
version, generar(prompt) -> LLMResponse) reutilizando el SDK `openai` ya
instalado, apuntado al router OpenAI-compatible de Hugging Face
Inference Providers (`https://router.huggingface.co/v1`, confirmado por
la documentación oficial en esta misma sesión) — cero dependencia nueva,
cero concepto nuevo.

Métricas (lo que Exp-1 se propuso medir, aprobado por el tesista):
  1. Tasa de JSON válido (roundtrip no revienta con ADR-0004 E-2 ni con
     JSONDecodeError) sobre N llamadas reales.
  2. Acuerdo del veredicto `dominada` contra la regla determinista
     scoring-v1 (`_UMBRAL_ERRORES`), barriendo errores a ambos lados del
     umbral — mismo diseño que
     `test_M3_PR2_diagnosticar_openai_real.py`.
  3. Latencia y tokens (proxy de costo — el router no expone precio).

Requiere `OPENAI_API_KEY` y `HF_TOKEN` reales en el entorno (`.env`). Sin
alguna de las dos credenciales, el script lo reporta y termina sin
fabricar resultados — E2E real, no mocks de dominio.

Uso: python scripts/experimentos/hf0_exp1_huggingface_vs_openai_diagnosticar.py
Salida: backend/experiments/results/hf0_exp1_<run_id>.json
"""

from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from openai import (  # noqa: E402
    APIConnectionError,
    APITimeoutError,
    InternalServerError,
    OpenAI,
    RateLimitError,
)

from runtime.domain.diagnosticar import FakeLLMProvider, producir_llm  # noqa: E402
from runtime.domain.diagnosticar.productor import _UMBRAL_ERRORES  # noqa: E402
from runtime.domain.shared.llm import LLMResponse  # noqa: E402
from runtime.domain.shared.llm_openai import OpenAIProvider  # noqa: E402
from runtime.domain.shared.llm_provider import con_reintentos  # noqa: E402
from runtime.kernel.state.entries import (  # noqa: E402
    Capacidad,
    EntryId,
    FactEntry,
    OrigenProvenance,
    Provenance,
)
from runtime.kernel.state.state import Identidad, LearningState  # noqa: E402

RESULTS_DIR = BACKEND_ROOT / "experiments" / "results"

#: Barrido a ambos lados del umbral, mismo diseño que M3 PR-2.
ERRORES_BARRIDO = (0, 1, _UMBRAL_ERRORES, _UMBRAL_ERRORES + 1, 5)
#: Bajado de 5 a 3 tras el 402 de la primera corrida — conserva crédito
#: mientras se decide si vale la pena crédito prepago.
REPETICIONES_POR_PUNTO = 3

#: Configurable sin tocar código — HF router permite `modelo` o
#: `modelo:proveedor` (docs.huggingface.co/inference-providers).
#: `Qwen/Qwen2.5-7B-Instruct-1M` (intento de abaratar tras el primer 402)
#: resultó NO habilitado para esta cuenta (HTTP 400 model_not_supported,
#: no falta de crédito) — se descarta, no probado. Vuelve a
#: `openai/gpt-oss-120b`: confirmado con una llamada mínima que aún queda
#: crédito y que el modelo SÍ está habilitado. Verificar disponibilidad
#: antes de correr — el catálogo de HF cambia con frecuencia.
HF_MODEL = os.environ.get("HF_MODEL", "openai/gpt-oss-120b")
HF_ROUTER_BASE_URL = "https://router.huggingface.co/v1"

_TRANSITORIAS: tuple[type[Exception], ...] = (
    APIConnectionError,
    APITimeoutError,
    RateLimitError,
    InternalServerError,
)


class HuggingFaceProvider:
    """Spike — implementación de `LLMProvider` (domain/shared/llm.py)
    sobre el router OpenAI-compatible de HF Inference Providers.

    Deliberadamente NO vive en `runtime/domain/shared/`: es evidencia
    para decidir si merece ese lugar, no una integración ya decidida.
    Misma forma que `OpenAIProvider` (mismo SDK, mismo patrón de
    reintentos) para que la única variable real del experimento sea el
    proveedor/modelo, no la infraestructura alrededor.
    """

    version = "hf-router-chat-v1"

    def __init__(self, modelo: str = HF_MODEL, *, intentos: int = 3, temperature: float = 0):
        self.modelo = modelo
        self._intentos = intentos
        self._temperature = temperature
        self._cliente = OpenAI(
            base_url=HF_ROUTER_BASE_URL,
            api_key=os.environ["HF_TOKEN"],
        )

    def generar(self, prompt: str) -> LLMResponse:
        def _llamar() -> LLMResponse:
            inicio = time.monotonic()
            respuesta = self._cliente.chat.completions.create(
                model=self.modelo,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=self._temperature,
            )
            latencia_ms = (time.monotonic() - inicio) * 1000
            eleccion = respuesta.choices[0]
            uso = (
                {
                    "prompt_tokens": respuesta.usage.prompt_tokens,
                    "completion_tokens": respuesta.usage.completion_tokens,
                    "total_tokens": respuesta.usage.total_tokens,
                }
                if respuesta.usage is not None
                else None
            )
            return LLMResponse(
                texto=eleccion.message.content,
                usage=uso,
                latencia_ms=latencia_ms,
                finish_reason=eleccion.finish_reason,
            )

        return con_reintentos(
            _llamar, excepciones_transitorias=_TRANSITORIAS, intentos=self._intentos
        )


class _ProveedorCapturador:
    """Mismo patrón que `ProveedorCapturador` en
    `consenso_barrido_evidencia_llm.py`: pasa la llamada intacta al
    proveedor real y captura latencia/usage de la `LLMResponse` sin
    alterarla — `producir_llm` los descarta (solo lee `.texto`), así que
    es la única forma de medirlos sin tocar `runtime/`. Vive solo en este
    script."""

    def __init__(self, proveedor: Any) -> None:
        self._proveedor = proveedor
        self.ultima_latencia_ms: float | None = None
        self.ultimos_tokens: dict[str, int] | None = None

    @property
    def modelo(self) -> str:
        return self._proveedor.modelo

    @property
    def version(self) -> str:
        return self._proveedor.version

    def generar(self, prompt: str) -> LLMResponse:
        respuesta = self._proveedor.generar(prompt)
        self.ultima_latencia_ms = respuesta.latencia_ms
        self.ultimos_tokens = dict(respuesta.usage) if respuesta.usage else None
        return respuesta


@dataclass
class ResultadoLlamada:
    proveedor: str
    errores: int
    ok: bool
    dominada: bool | None = None
    dominada_esperada: bool | None = None
    acuerdo: bool | None = None
    latencia_ms: float | None = None
    tokens: dict[str, int] | None = None
    error: str | None = None


@dataclass
class ResumenProveedor:
    proveedor: str
    llamadas: list[ResultadoLlamada] = field(default_factory=list)

    @property
    def tasa_json_valido(self) -> float:
        return sum(1 for r in self.llamadas if r.ok) / len(self.llamadas)

    @property
    def tasa_acuerdo_scoring_v1(self) -> float:
        con_veredicto = [r for r in self.llamadas if r.acuerdo is not None]
        if not con_veredicto:
            return 0.0
        return sum(1 for r in con_veredicto if r.acuerdo) / len(con_veredicto)

    @property
    def latencia_ms_promedio(self) -> float | None:
        latencias = [r.latencia_ms for r in self.llamadas if r.latencia_ms is not None]
        return sum(latencias) / len(latencias) if latencias else None

    @property
    def tokens_promedio(self) -> float | None:
        totales = [r.tokens["total_tokens"] for r in self.llamadas if r.tokens]
        return sum(totales) / len(totales) if totales else None


def _estado_con_errores(errores: int, run_id: str) -> LearningState:
    fact = FactEntry(
        id=EntryId(1, 1),
        autor=Capacidad.EVALUAR,
        contenido={
            "competencia": "COMP-2",
            "items_incorrectos": list(range(errores)),
        },
        provenance=Provenance.de(OrigenProvenance.INSTRUMENTO, banco="v2"),
    )
    return LearningState(
        identidad=Identidad(
            session_id=f"hf0-exp1-{run_id}-{errores}",
            student_id="maria",
            version_student_model="v7",
            version_banco="banco-v2",
            version_politica="politica-v1",
            spec_version="foundation-2026-07-10",
        ),
        contexto={"ruta": "condicionales"},
        facts=(fact,),
        transicion=1,
    )


def _correr_una_llamada(proveedor_nombre: str, proveedor: Any, errores: int, run_id: str) -> ResultadoLlamada:
    esperado = errores < _UMBRAL_ERRORES
    estado = _estado_con_errores(errores, run_id)
    capturador = _ProveedorCapturador(proveedor)
    try:
        (intent,) = producir_llm(estado, proveedor=capturador)
        dominada = intent.argumentos["afirmacion"]["dominada"]
        return ResultadoLlamada(
            proveedor=proveedor_nombre,
            errores=errores,
            ok=True,
            dominada=dominada,
            dominada_esperada=esperado,
            acuerdo=(dominada == esperado),
            latencia_ms=capturador.ultima_latencia_ms,
            tokens=capturador.ultimos_tokens,
        )
    except Exception as error:  # noqa: BLE001 — el error ES el dato (tasa de JSON inválido)
        return ResultadoLlamada(
            proveedor=proveedor_nombre,
            errores=errores,
            ok=False,
            latencia_ms=capturador.ultima_latencia_ms,
            tokens=capturador.ultimos_tokens,
            error=f"{type(error).__name__}: {error}",
        )


def main() -> None:
    faltantes = [v for v in ("OPENAI_API_KEY", "HF_TOKEN") if not os.environ.get(v)]
    if faltantes:
        print("Exp-1 requiere credenciales reales — no se fabrican resultados.")
        print(f"Faltan: {', '.join(faltantes)}")
        print("Configurar en backend/.env (ver backend/.env.example) y reintentar.")
        sys.exit(1)

    ahora = datetime.now()
    run_id = ahora.strftime("%Y%m%dT%H%M%S")

    print("=" * 70)
    print("HF-0 / Exp-1 -- HuggingFaceProvider vs OpenAIProvider (Diagnosticar)")
    print(f"run_id: {run_id}  modelo_hf: {HF_MODEL}")
    print("=" * 70)

    resumenes = {
        "fake_regla_v1": ResumenProveedor(proveedor="fake_regla_v1"),
        "openai": ResumenProveedor(proveedor="openai"),
        "huggingface": ResumenProveedor(proveedor="huggingface"),
    }
    proveedores = {
        "fake_regla_v1": lambda: FakeLLMProvider(),
        "openai": lambda: OpenAIProvider(),
        "huggingface": lambda: HuggingFaceProvider(),
    }

    for errores in ERRORES_BARRIDO:
        print(f"\n--- errores={errores} (dominada esperada = {errores < _UMBRAL_ERRORES}) ---")
        for nombre, fabrica in proveedores.items():
            repeticiones = 1 if nombre == "fake_regla_v1" else REPETICIONES_POR_PUNTO
            for _ in range(repeticiones):
                resultado = _correr_una_llamada(nombre, fabrica(), errores, run_id)
                resumenes[nombre].llamadas.append(resultado)
            ultimos = resumenes[nombre].llamadas[-repeticiones:]
            ok = sum(1 for r in ultimos if r.ok)
            print(f"  {nombre:14s} json_valido={ok}/{repeticiones}")

    print("\n" + "=" * 70)
    print("RESUMEN")
    print("=" * 70)
    resumen_export: dict[str, Any] = {}
    for nombre, resumen in resumenes.items():
        print(
            f"{nombre:14s} "
            f"json_valido={resumen.tasa_json_valido:.0%}  "
            f"acuerdo_scoring_v1={resumen.tasa_acuerdo_scoring_v1:.0%}  "
            f"latencia_ms_prom={resumen.latencia_ms_promedio}  "
            f"tokens_prom={resumen.tokens_promedio}"
        )
        resumen_export[nombre] = {
            "tasa_json_valido": resumen.tasa_json_valido,
            "tasa_acuerdo_scoring_v1": resumen.tasa_acuerdo_scoring_v1,
            "latencia_ms_promedio": resumen.latencia_ms_promedio,
            "tokens_promedio": resumen.tokens_promedio,
            "llamadas": [vars(r) for r in resumen.llamadas],
        }
    print("=" * 70)

    resultado_export = {
        "experimento": "HF-0_Exp-1_huggingface_vs_openai_diagnosticar",
        "aprobado_por_tesista": True,
        "no_abre_P3_adaptar": "registrado como hallazgo separado, no ejecutado aquí",
        "run_id": run_id,
        "timestamp": ahora.isoformat(),
        "modelo_hf": HF_MODEL,
        "umbral_errores_scoring_v1": _UMBRAL_ERRORES,
        "barrido_errores": list(ERRORES_BARRIDO),
        "repeticiones_por_punto": REPETICIONES_POR_PUNTO,
        "resumen_por_proveedor": resumen_export,
    }
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    salida = RESULTS_DIR / f"hf0_exp1_{run_id}.json"
    salida.write_text(
        json.dumps(resultado_export, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
    )
    print(f"\nResultado exportado a: {salida.relative_to(BACKEND_ROOT.parent)}")


if __name__ == "__main__":
    main()
