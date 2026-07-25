"""Telemetría operativa (LangSmith) — RFC-0007, alternativa 2 rechazada.

Este paquete NUNCA es fuente de evidencia para la tesis. La fuente de
evidencia sigue siendo el plano de observabilidad de RFC-0007
(`consultar_traza`/`consultar_replay`, ya en `runtime/boundary/`). Lo de
aquí es exclusivamente telemetría operativa (salud del servicio, latencia,
tokens) para visualización de desarrollo/demo, mantenida separada del
plano de evidencia y sin mezclarse con él (RFC-0007, "Alternativas
consideradas y rechazadas", punto 2).

Se desactiva por completo si `LANGSMITH_TRACING`/`LANGSMITH_TRACING_V2` no
está configurado — ver `config.py`.
"""
