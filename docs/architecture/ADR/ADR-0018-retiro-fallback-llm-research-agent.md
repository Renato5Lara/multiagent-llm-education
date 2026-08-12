# ADR-0018 — Retiro formal del fallback heurístico vía LLM en `ResearchAgent`

- **Estado:** Aceptado (2026-08-12)
- **Fecha:** 2026-08-12
- **Preserva:** `app/services/research_agent.py` (implementación vigente,
  sin cambios de código en esta ADR), hallazgos de los Gates C2-D y C2-E
  (saneamiento de suite, sesión de investigación de esta fecha)
- **Criterio de aceptación:** ver §5

## 1. Contexto

Durante el saneamiento de la suite de tests (Gate C2, clasificación de
`tests/test_research_agent.py`), el Gate C2-D encontró que 2 de los 7
tests del archivo (`test_fallback_when_llm_fails`,
`test_examples_from_llm_findings`) no fallan por un simple cambio de
firma: protegen una capacidad — generar contenido de investigación vía
LLM cuando Tavily no está disponible, marcado internamente como
`source: "heuristic"` — que existió brevemente en el commit `5a1fb44`
(2026-06-06, versión de `ResearchAgent` que heredaba de `BaseAgent`) y
ya no existe en la implementación vigente.

El Gate C2-E investigó si ese retiro fue una decisión deliberada:

- **Reconstrucción temporal** (`git log --follow`, 6 commits en toda la
  historia de `app/services/research_agent.py`, confirmado con `git show
  <sha>:<path>` sobre los blobs reales, no solo mensajes de commit): el
  fallback existía en `5a1fb44` (274 líneas) y ya no existía 3 días
  después en `add3546` (123 líneas, 2026-06-09). El diff propio de
  `add3546` respecto a su padre real (`27f8cb2`) no contiene ese cambio
  — solo un ajuste no relacionado de 22 líneas
  (`publish_observation`→`publish_observation_sync`). El commit exacto
  que removió el fallback no es reconstruible limpiamente desde el
  grafo de commits actual (posible amend/rebase durante el desarrollo
  temprano del archivo).
- **Búsqueda documental exhaustiva**: `grep` de "tavily", "heuristic" y
  "fallback" sobre la totalidad de `docs/architecture/` (incluyendo
  RFC-0005 y ADR-0001 a ADR-0017) no encontró ninguna decisión que
  documente este retiro.
- **Dependencia real**: los 3 callers de producción de
  `ResearchAgent.analyze()`/`.run()`
  (`weekly_pedagogy_service.py:434`, `module_orchestration_service.py:594`,
  `weekly_learning/orchestration.py:45`) fueron revisados; el más
  relevante, `module_orchestration_service.py:596-634`, ya envuelve la
  llamada en un `try/except Exception` genérico que degrada a
  `{"research": {}, "research_metrics": {}, "consistency_validation": {}}`
  ante *cualquier* fallo, no solo la ausencia de Tavily — confirmando
  que la arquitectura vigente ya está diseñada asumiendo que la
  investigación puede faltar por completo.

Conclusión del diagnóstico: el retiro del fallback fue una pérdida sin
decisión documentada — exactamente el tipo de regresión silenciosa que
esta sesión de investigación viene detectando (mismo patrón que F3/C5b,
aunque de naturaleza distinta: aquí es una capacidad perdida en un
rediseño temprano, no un `await` faltante). Corresponde cerrar esa
ambigüedad con una decisión explícita antes de sanear los tests que la
protegían.

## 2. Decisión

**Se declara el retiro formal de la capacidad de fallback heurístico vía
LLM en `ResearchAgent`.** No se reintroduce. El comportamiento vigente
(degradar a resultado vacío/parcial con `degraded=True` cuando Tavily no
está disponible, sin generar contenido sintético de respaldo) queda
ratificado como el contrato correcto y definitivo del sistema.

No se modifica ningún archivo de producción en esta ADR — el código ya
implementa la decisión que aquí se formaliza; el efecto práctico es
habilitar el saneamiento de los tests que asumían el comportamiento
anterior (Gate C2, ejecutado por separado).

## 3. Justificación

- **Sin dependencia real**: ningún caller de producción exige que la
  investigación esté siempre poblada; el pipeline ya tolera y maneja
  explícitamente su ausencia total.
- **Riesgo de integridad académica**: reintroducir generación de
  contenido pedagógico vía LLM sin fuentes verificables (el propio
  campo `source: "heuristic"` de la versión retirada lo admitía) expone
  al estudiante a contenido no fundamentado, presentado con la misma
  apariencia que investigación real respaldada por fuentes — un riesgo
  de calidad inaceptable para una plataforma cuya tesis depende de la
  trazabilidad de la evidencia pedagógica.
- **Costo/latencia**: una llamada LLM adicional en el camino de fallo
  añade latencia y costo sin beneficio pedagógico verificable, dado que
  el punto anterior ya descarta su valor.
- **Consistencia con el resto de la arquitectura**: el sistema ya trata
  "sin evidencia suficiente" como un resultado legítimo en otros puntos
  del pipeline (D3-insuficiencia de RFC-0006 §3, ADR-0016) en vez de
  forzar una síntesis artificial — declarar este retiro alinea
  `ResearchAgent` con ese mismo principio.

## 4. Alternativas rechazadas

- **Reintroducir el fallback LLM tal como existía en `5a1fb44`**:
  rechazada — reintroduce el riesgo de contenido no fundamentado sin
  que ningún caller real lo necesite hoy.
- **Dejarlo como deuda sin decidir**: rechazada — perpetuaría la
  ambigüedad que impide sanear los 2 tests de C2-D correspondientes de
  forma metodológicamente sólida (retirarlos porque el contrato quedó
  formalmente retirado, no simplemente porque hoy no pasan).
- **Reintroducirlo con marcado explícito de "contenido no verificado"
  visible al estudiante**: considerada pero no adoptada en esta ADR —
  mitigaría el riesgo de integridad pero sigue sin tener un caller real
  que lo requiera; si en el futuro aparece una necesidad de producto
  concreta, debe evaluarse en un ADR propio, no reabrir este.

## 5. Consecuencias / Criterios de aceptación

1. `tests/test_fallback_when_llm_fails` y
   `tests/test_examples_from_llm_findings` (`tests/test_research_agent.py`)
   se retiran en el saneamiento de C2 citando esta ADR, no por
   simple incompatibilidad de fixture.
2. Ningún archivo de `app/` cambia como consecuencia directa de esta
   ADR — el comportamiento declarado es el que ya existe.
3. Si en el futuro se decide que `ResearchAgent` necesita un mecanismo
   de contenido de respaldo ante fallo de Tavily, esa sería una
   capacidad *nueva*, diseñada desde cero (posiblemente con
   verificación/marcado explícito de contenido no fundamentado), no una
   reversión de esta ADR sin más.
