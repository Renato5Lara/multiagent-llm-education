"""Spans operativos de LangSmith para llamadas reales al LLM y a servicios
externos al runtime (RFC-0007, alternativa 2: latencia/tokens dependen del
reloj de pared, por eso el propio RFC los excluye del registro científico
y los admite solo como telemetría operativa).

Este módulo es el ÚNICO punto que sabe hablar con el SDK de `langsmith`.
Nunca se importa desde `runtime/` — se inyecta como una función simple
(`registrar_llamada_llm`) en el punto de extensión que expone
`runtime.domain.shared.llm_openai` (ver `bootstrap.py`), así `runtime/`
jamás importa nada de `app/` (la dependencia va en un solo sentido).

Correlación (validado en Fase 5A): se usa `@traceable` en vez de
`Client().create_run()` a mano porque el decorador SÍ se integra con el
contexto de tracing ambiental de LangSmith (contextvars) — cuando la
llamada real a OpenAI ocurre DENTRO de un nodo LangGraph ya trazado
(diagnosticar/remediar/orientar), el span queda anidado bajo ese nodo
automáticamente, sin pasar `session_id` a mano. Para operaciones que
corren FUERA de cualquier ejecución de grafo (tutor, memoria, módulo —
no hay contexto ambiental que heredar), se añade `session_id` explícito
como tag/metadata para que sean correlacionables por ese campo aunque
aparezcan como raíces independientes en el árbol.

Contrato duro con el llamador (runtime u otros servicios): estas
funciones JAMÁS propagan una excepción, JAMÁS modifican nada que reciban,
y no introducen esperas apreciables — el cliente de LangSmith agrupa y
envía los runs en lote de forma asíncrona (`auto_batch_tracing=True` por
defecto), así que crear un run solo encola, no bloquea en red.
"""

from __future__ import annotations

from typing import Any

from app.telemetry.config import HABILITADO, PROYECTO


def _span_llm(
    modelo: str,
    latencia_ms: float,
    usage: dict[str, int] | None,
    finish_reason: str | None,
    fallo: str | None,
) -> dict[str, Any]:
    from langsmith import traceable

    @traceable(name=f"llm:{modelo}", run_type="llm", project_name=PROYECTO)
    def _run(modelo: str, latencia_ms: float, usage, finish_reason, fallo) -> dict[str, Any]:
        if fallo is not None:
            raise RuntimeError(fallo)
        return {"usage": usage, "finish_reason": finish_reason, "latencia_ms": latencia_ms}

    return _run(modelo, latencia_ms, usage, finish_reason, fallo)


def registrar_llamada_llm(
    modelo: str,
    respuesta: Any | None,
    error: BaseException | None,
    latencia_ms: float,
) -> None:
    """Un span operativo por llamada real a OpenAI (éxito o fallo).

    Firma posicional exacta que espera `runtime.domain.shared.llm_openai.
    ObservadorLLM` — se registra tal cual en `bootstrap.py`, sin envoltorio.
    No-op inmediato si la telemetría está deshabilitada. Protegido de punta
    a punta: ningún fallo aquí (LangSmith caído, API key inválida, etc.)
    puede llegar al runtime."""
    if not HABILITADO:
        return
    try:
        _span_llm(
            modelo,
            latencia_ms,
            dict(getattr(respuesta, "usage", None) or {}) if respuesta is not None else None,
            getattr(respuesta, "finish_reason", None) if respuesta is not None else None,
            repr(error) if error is not None else None,
        )
    except Exception:
        # Telemetria operativa: un fallo aqui (incluido el RuntimeError que
        # el propio _span_llm levanta a proposito para marcar el run como
        # fallido) jamas debe llegar al runtime.
        pass


def registrar_operacion_externa(
    nombre: str,
    *,
    latencia_ms: float,
    session_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    error: BaseException | None = None,
) -> None:
    """Un span operativo para una operación que ocurre FUERA del runtime
    LangGraph (tutor IA, orquestación de módulo, memoria compartida del
    swarm de contenido — AG-05/06/07). No hay un run de LangGraph
    ambiental del que colgar aquí, así que `session_id` (nuestro, de
    dominio) se añade como tag/metadata explícito para que sea
    correlacionable por ese campo. Mismo contrato de garantías que
    `registrar_llamada_llm`."""
    if not HABILITADO:
        return
    try:
        from langsmith import traceable

        tags = [f"session:{session_id}"] if session_id else None
        datos = {"session_id": session_id, **(metadata or {}), "latencia_ms": latencia_ms}

        @traceable(name=nombre, run_type="chain", project_name=PROYECTO, tags=tags)
        def _run(**datos: Any) -> dict[str, Any]:
            if error is not None:
                raise RuntimeError(repr(error))
            return datos

        _run(**datos)
    except Exception:
        pass
