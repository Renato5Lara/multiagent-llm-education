# Bitácora de Migración — Arquitectura Pedagógica v1.0 → Implementación

No es arquitectura. Es registro de avance: qué se implementó, en qué commit, y qué
falta. Una o dos líneas por entrada — el detalle vive en el propio commit y en
[ESTADO.md](ESTADO.md)/[ANEXO-A](ANEXO-A-MATRIZ-TRAZABILIDAD.md) para trazabilidad
de principios.

## Commit 1 — Boundary: Política de Selección de Forma (Adenda A)
✔ `backend/app/services/adaptive_form_selection.py` — `1ba66ed`
✔ Corrección funcional (insumo de Memoria, `formas_ya_mostradas`) — `7c9f8d3`
✔ 13/13 tests, backend importa limpio, cero wiring todavía (módulo inerte)

## Commit 2 — Higiene del repositorio (~8 días integrados en 7 commits)
✔ `d4ccf65` fix(replay): fix de evidencia abandonada (STAB-01)
✔ `9129c53` chore: except silenciosos → logging
✔ `9ebd873` style: tokens de tema oscuro
✔ `503b160` fix(auth): redirect de rol investigador
✔ `b322da0` feat(learning): bloqueo del Post-Test sin ruta completa (IMPL-01)
✔ `c990e74` refactor(docente): retiro de Comparación Swarm (IMPL-02/03)
✔ `a694f3b` fix(users): desacople de Ciclo del pipeline legado
✔ `429f543` refactor(dashboard): recomposición en 4 componentes
✔ `9f2b94e` feat(experience): sub-pasos + botón Ayuda en ModuleExperienceView
✔ Backend importa limpio, frontend build de producción limpio tras cada grupo
□ Pendiente de decisión del usuario, fuera de esta bitácora:
  `backend/scripts/seed_demo_swarm.py` (¿sigue en uso?), `PENDING_FIXES_M1.md`
  y `frontend/--full-page` (descartables, no son trabajo real)

## Commit 3 — Wiring + migración del frontend
✔ `91e7ea4` (3a) — `/cycle-evidence` llama a `seleccionar_forma()`, aditivo
  puro; `CycleEvidenceSubmit.formas_ya_mostradas` nuevo, aún vacío desde el
  frontend en este punto. El módulo del Commit 1 deja de estar inerte.
✔ `b45c9ae` (3b) — `experienceOrchestrator.ts` consume
  `runtime_decision.forma.tipo` como fuente primaria;
  `REINFORCEMENT_BY_MODALITY`/`resolveReinforcementPriority` quedan solo de
  fallback (Boundary sin recomendación reconocible, o sin contenido
  autorado para la forma recomendada). `visitedReinforcements` ahora viaja
  como `formas_ya_mostradas` en cada request — cierra el círculo con la
  corrección funcional del commit `7c9f8d3`.
✔ Orden invertido respecto al plan original (wiring antes que frontend) por
  seguridad: evita un adaptador frontend apuntando a un campo que el
  backend todavía no envía.
✔ 17/17 tests backend, tsc limpio, eslint sin errores nuevos, build de
  producción exitoso. Sin cambio de comportamiento observable: misma
  prioridad, ahora en el Boundary en vez de en el cliente.

## Deuda técnica registrada (no se resuelve ahora)
□ `REINFORCEMENT_BY_MODALITY`/`resolveReinforcementPriority`
  (`experienceOrchestrator.ts`) quedan como fallback local desde el Commit 3.
  Cuando el Boundary pueda recomendar todas las formas del catálogo de PP4 y
  todos los ciclos estén completamente adaptados con contenido autorado para
  cada una, evaluar eliminar definitivamente el fallback — no antes.

## Commit 4 — Infraestructura de la Adenda B (no "Adenda B completa")
✔ `e6c86a3` — `POST /api/students/consent-response` (contrato +
  registro en `research_metrics`, `CONSENT_RESPONSE`) + `useSubmitConsentResponse`
  en el frontend, sin wiring a ningún componente.
✔ Checklist de aceptación (5/5): sin cambio de comportamiento observable
  (endpoint y hook nuevos, sin consumidor); ninguna decisión pedagógica
  nueva (nunca llama a `runtime_bridge`, verificado con test); permanece
  inactiva (ninguna prioridad selecciona una forma "consentimiento" hoy);
  4/4 tests (contrato, persistencia, verificación negativa de no-toca-
  runtime); oferta proactiva y solicitud voluntaria no comparten código.
✔ `ModuleExperienceView.tsx` no se tocó — cero riesgo por construcción,
  no solo por intención. Backend importa limpio, tsc/eslint/build
  limpios.
□ Activación futura (fuera de este commit): ampliar
  `_PRIORIDAD_POR_MODALIDAD` o un productor nuevo del runtime (RFC) para
  que `codigo_guiado`/`narracion_tutor` empiecen a seleccionarse; recién
  ahí construir la UI que ofrezca consentimiento visible.

## Verificación de aislamiento (Commit 4, post-cierre)

Los 4 puntos que propuso el usuario, verificados independientemente del
commit (no solo confiando en lo ya probado):

1. **El endpoint existe** — `POST /api/students/consent-response`, confirmado.
2. **Ningún flujo actual lo consume** — cero referencias a
   `useSubmitConsentResponse`/`consent-response` fuera de su propia
   definición, en frontend y backend.
3. **Su presencia no modifica el comportamiento observable** — suite
   completa del backend corrida de nuevo (no solo los archivos tocados),
   ver resultado abajo.
4. **Los datos registrados alcanzan para una futura activación** —
   matizado, no un "sí" plano: ver tabla de niveles.

**Hallazgo colateral, sin relación con este trabajo:** la corrida completa
encontró 2 errores de colección preexistentes —
`tests/test_tavily_cache.py` y `tests/test_tavily_client.py` importan
`get_tavily_cache`/`get_tavily_client`, funciones que ya no existen en
`app/integrations/tavily/`. Cero cambios sin commitear en esos archivos
(`git status` limpio, último commit real de hace varias sesiones) — no es
una regresión de esta migración, es deuda preexistente fuera de alcance.

### Niveles de evolución del endpoint de consentimiento

| Nivel | Uso | ¿El payload actual alcanza? |
|---|---|---|
| 1 (actual) | Registro analítico (`research_metrics`) | Sí — es literalmente lo que hace hoy |
| 2 | Memoria del ciclo (evitar repetir ofertas en el mismo ciclo) | **No aplica a este endpoint** — esa responsabilidad ya la resuelve `formas_ya_mostradas` (Commit 3), client-side, por ciclo. Este endpoint no necesita evolucionar hacia esto porque el mecanismo ya existe en otro lugar. |
| 3 | Evento de dominio (afectar decisiones futuras del runtime) | **No, tal como está.** Falta una referencia causal a la decisión de Adaptar que originó la oferta (un `EntryId`/asunto) — sin eso, un fact/claim nuevo violaría INV-5 (todo claim exige respaldo) y P6 (la explicación se recorre). Si algún día se decide activar este nivel, el esquema necesita ese campo antes, no después. |

## Commit 5 — Validación funcional
□ Repetir el stress-test de escenarios, ahora contra código real
□ Cada escenario debe terminar en el comportamiento que especifican los
  documentos, no en uno inventado durante la implementación
