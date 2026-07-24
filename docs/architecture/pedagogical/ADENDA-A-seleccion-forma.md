# ADENDA A al Documento 5 — Política de Selección de Forma

**Parte de la Arquitectura Pedagógica v1.0.** Cierra el vacío detectado durante el
stress-test de escenarios de cierre (2026-07-23): ningún documento traducía la
decisión real del runtime (`modalidad` + `profundidad`) a una forma concreta del
catálogo de PP4, ni por tanto a su categoría automática/con-consentimiento (Doc 5
§4.1). No fija un mapeo específico (eso sería contenido, no arquitectura) — fija
responsabilidad e insumos.

---

**Quién decide:** el Boundary — nunca el runtime (elegir una forma no es una nueva
decisión pedagógica, es traducción; que el runtime la tomara violaría su propia
frontera ya declarada en `adaptar/productor.py`: "categorías pedagógicas, nunca más")
ni la interfaz (reintroduciría subjetividad de diseño sobre algo que sigue siendo
pedagógico, violando PP1).

**Con qué insumos:** exclusivamente lo que Adaptar ya produjo — modalidad,
profundidad, y `alternativas_descartadas` cuando exista señal de Tutorizar (PP5).
Nunca información que el runtime no haya declarado.

**Restricción de la política:** la función (modalidad, profundidad,
alternativas_descartadas) → forma concreta debe ser determinista y declarada
explícitamente, con el mismo estándar de trazabilidad que ya rige a
`DISENO_POR_ACCION` — nunca una heurística oculta en el frontend. Una vez elegida la
forma, su categoría (automática / con consentimiento) se deriva aplicando la regla
general ya establecida en la Política de Consentimiento Adaptativo (Doc 5 §4.1) —
nunca al revés.

**Lo que esta adenda NO decide:** el mapeo específico (qué forma exacta le
corresponde a qué combinación) — eso es contenido/producto, pertenece a la
implementación.
