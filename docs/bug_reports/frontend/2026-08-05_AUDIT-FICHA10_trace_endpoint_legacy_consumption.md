# Ficha 10 — Consumo de `/api/trace/session/{id}` (endpoint eliminado)

## Metadata

- **Fecha:** 2026-08-05
- **Rama:** `investigacion/sesion5-rendimiento`
- **Protocolo pedido (Fase 2):** (1) confirmar consumo real del
  endpoint eliminado; (2) identificar archivos frontend afectados;
  (3) clasificar: código muerto / degradación silenciosa /
  funcionalidad rota que afecta evidencia; (4) no implementar cambios
  todavía. Mismo rigor que Ficha 05/09. **Ningún archivo de código
  modificado.**
- **Origen:** hallazgo colateral de la validación de Paso 4, Sesión 5
  Frente B (`AUDIT-2026-08-05_REMEDIATION_STATUS.md`, observación #6).

---

## 1. ¿Existe consumo real del endpoint eliminado?

**Sí, confirmado en ambos extremos.**

**Backend:** `grep` de `/api/trace` y `@router.get("/session` en
`backend/app/api/routes/*.py` no encuentra ningún router con ese
prefijo — el único `GET /session/{session_id}` que existe hoy vive en
`replay.py`, bajo `/api/replay` (prefijo distinto,
`router = APIRouter(prefix="/api/replay", ...)`), no relacionado.
`/api/trace/session/{id}` **no existe en el backend actual**,
confirmado, no una hipótesis — desapareció con la eliminación física
de `routes/traces.py` en Ficha 04 (commit `ab3860b`).

**Frontend:** `useTrace()` (`frontend/src/hooks/useTrace.ts:14-21`)
llama exactamente a esa ruta:

```ts
async function fetchTraceBySession(sessionId: string) {
  const { data } = await api.get<TraceChainResponse>(
    `/api/trace/session/${sessionId}`,
  );
  return data;
}

export function useTrace(sessionId?: string) {
  return useQuery({
    queryFn: () => fetchTraceBySession(sessionId!),
    enabled: Boolean(sessionId),   // ← se dispara siempre que hay sessionId real
    retry: (failureCount, error) => {
      if (error.response?.status === 404) return false;  // no reintenta en 404
      return failureCount < 1;
    },
  });
}
```

`enabled: Boolean(sessionId)` — se dispara para **cualquier** sesión
real de estudiante, no es un camino muerto ni condicional a un flag.
Es una llamada de red real, hecha en cada visita a la página real del
estudiante (`ModuleLearningView.tsx`), que siempre falla con 404.

---

## 2. Archivos frontend afectados

9 consumidores directos o indirectos de `useTrace()`:

| Archivo | Rol |
|---|---|
| `hooks/useTrace.ts` | El hook — origen de la llamada rota |
| `components/observability/AgentThoughtStream.tsx` | Panel **siempre visible** en `ModuleLearningView.tsx` ("Observability section") |
| `components/observability/AgentDebateBubbles.tsx` | Usado por `DebatePanel` (local a `ModuleLearningView.tsx`), también siempre montado |
| `components/observability/TraceExplorer.tsx` | Modal bajo demanda ("Ver análisis técnico completo →") |
| `components/observability/AgentThoughtWindow.tsx` | Sub-componente de `TraceExplorer` |
| `components/observability/RealTraceTimeline.tsx` | Sub-componente de `AgentThoughtStream` (rama "real") |
| `components/observability/ThoughtSummary.tsx` | Sub-componente adicional |
| `components/observability/AgentList.tsx` | Sub-componente de `TraceExplorer` |
| `components/observability/DebateTimeline.tsx` | Sub-componente relacionado con debate |

**Todos son alcanzables desde `ModuleLearningView.tsx`** — la página
real de módulo del estudiante, la misma que se recorrió extensamente
durante la Sesión UX/UI sin que esto se detectara visualmente (ver
punto 3).

---

## 3. Clasificación — no es ninguna de las tres categorías de forma pura

### No es código muerto

El hook se ejecuta de verdad, en cada sesión real, con un intento de
red real que falla. No es un camino inalcanzable.

### No es "funcionalidad rota" en el sentido ingenuo

**El mecanismo de respaldo fue diseñado deliberadamente**, documentado
explícitamente en el propio código
(`AgentThoughtStream.tsx:16-25`):

> "Two-layer architecture: Layer 1 (student, always works):
> SyntheticTimeline from PIPELINE_STEPS constants. Layer 2 (real,
> needs LLM keys): RealTraceTimeline from `/api/trace/session/{id}`.
> Switch is automatic: when the trace endpoint returns data,
> RealTraceTimeline is shown. **When it returns 404 (template-fallback
> mode), SyntheticTimeline is shown.** Adding `OPENAI_API_KEY` to the
> environment upgrades the display with no frontend changes."

El diseño original **esperaba** que 404 significara "sin
`OPENAI_API_KEY` configurada, capacidades por regla activas" — un
estado legítimo, no un error. El mismo patrón de dos capas existe en
`AgentDebateBubbles.tsx` (`SyntheticDebate` vs. datos reales,
etiquetado explícito `(estimado)` en el contenido sintético).

### Lo que sí es un defecto real: el significado de "404" cambió sin que el frontend lo sepa

En este entorno, `OPENAI_API_KEY` **está configurada** (confirmado
durante toda esta sesión — log de arranque de `uvicorn`: "OpenAI LLM
generation available"). El 404 de hoy **no** significa "sin clave
LLM" — significa "la ruta fue eliminada físicamente" (Ficha 04). El
frontend no puede distinguir ambos casos: siempre que hay 404, cae al
mismo `SyntheticTimeline`/`SyntheticDebate`, como si fuera el caso
legítimo original que el diseño sí anticipaba.

### Hallazgo adicional — inconsistencia real entre dos superficies del mismo dato roto

- **`AgentThoughtStream`** (panel colapsable, siempre presente en la
  página, sin acción del usuario) — degradación **completamente
  silenciosa**: muestra "Este módulo fue preparado por N agentes de
  IA · Sistema de orquestación multiagente · ~Ns", sin ninguna
  etiqueta ni indicación de que el contenido es sintético. Solo la
  ausencia del badge verde `LIVE` distingue este estado del real — una
  señal negativa, no una advertencia activa.
- **`TraceExplorer`** (modal bajo demanda, requiere clic explícito en
  "Ver análisis técnico completo →") — degradación **visible y
  honesta**: `ExplorerError` (`TraceExplorer.tsx:157-169`) muestra
  "Unable to load trace data. Check that the backend
  `/api/trace/session` endpoint is reachable." — un mensaje técnico
  explícito, correcto incluso hoy.
- **`AgentDebateBubbles`** (contenido sintético) sí se autoetiqueta
  `(estimado)` en cada burbuja; **`SyntheticTimeline`** (el fallback de
  `AgentThoughtStream`) no tiene una etiqueta equivalente en su vista
  colapsada — inconsistencia adicional entre dos mecanismos del mismo
  patrón de dos capas.

**Por eso nunca se detectó durante el recorrido visual de la Sesión
UX/UI:** la superficie que domina la experiencia normal (el panel
siempre visible) es precisamente la que oculta el problema; solo
aparece si alguien hace clic deliberadamente en "Ver análisis técnico
completo" — algo que ningún recorrido de Paso 1 de UX/UI hizo.

---

## 4. ¿Impacta evidencia experimental / Modo Evidencia?

**Impacto acotado, no crítico, pero real para la sustentación:**

- **Modo Evidencia / Runtime Console** (la superficie de observabilidad
  oficial para jurado/docente, RFC-0007, ya validada con datos reales
  en Ficha 06 de esta misma auditoría) **no depende de este endpoint**
  — usa `/api/runtime/sessions/{id}/traza` y demás rutas de
  `runtime.py`, respaldadas por `runtime_transitions` real. Esa
  superficie sigue siendo confiable.
- **El riesgo está en la página del estudiante**, no en Modo Evidencia:
  si durante una demo se abre "Ver análisis técnico completo" en la
  página de un estudiante real, aparecerá un error técnico visible
  ("Unable to load trace data") en medio de una demostración — no
  rompe la plataforma, pero es una superficie de fricción/confusión no
  planeada si nadie la anticipa.
- El resto del tiempo (panel colapsable, siempre visible), el sistema
  muestra contenido sintético sin advertirlo — no es información falsa
  peligrosa (es una estimación razonable del pipeline), pero tampoco es
  honesto sobre su propia naturaleza, a diferencia de
  `AgentDebateBubbles` que sí se etiqueta.

---

## Clasificación final

**No es código muerto. No es simplemente "funcionalidad rota".** Es un
**mecanismo de respaldo deliberado cuyo disparador cambió de
significado** (de "sin clave LLM" a "endpoint eliminado") sin que el
frontend lo sepa, con **dos superficies que manejan la misma ausencia
de datos de forma inconsistente entre sí** (una oculta, otra revela) —
un hallazgo genuinamente distinto a cualquiera de los ya cerrados en
esta auditoría.

**No se implementa ningún cambio en este documento.**

## Candidatos de remediación (sin decidir, para un futuro Paso 3/4)

**Opción A — Mejorar el copy del fallback** (p. ej. "Datos sintéticos
de demostración — no existe traza real disponible" en
`AgentThoughtStream`, igualándolo a la etiqueta `(estimado)` que
`AgentDebateBubbles` ya usa). Cero impacto de arquitectura, evita el
engaño silencioso, riesgo muy bajo — candidata más simple de las dos.

**Opción B — Cambiar la fuente de datos** de `AgentThoughtStream`/
`TraceExplorer` para que consuman la trazabilidad real ya vigente
(`runtime_transitions`/`/runtime/sessions/{id}/traza`, la misma que
respalda Modo Evidencia) en vez de intentar reconectar el router
eliminado `/api/trace/*`. Coherente con hacia dónde ya migró la
arquitectura (LangGraph Runtime + Runtime Console) — pero es una
decisión de producto/arquitectura de mayor alcance, no una corrección
rápida: **no** sería "reactivar el endpoint viejo automáticamente".

Ninguna de las dos se decide ni se implementa aquí — ambas quedan
como candidatas explícitas para cuando se abra su propio Paso 3/4.

Ninguno de los dos se decide ni se implementa aquí.
