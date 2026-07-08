# Informe Técnico — Research & Experiment Layer

> Fecha: 2026-07-08 · Rama: `stabilization/m1-operational-baseline`
> Commits: `12d0c03..7f7ac04` (11 commits) + este informe
> Estado: funcionalmente validado por validación automatizada;
> **pendiente de validación manual del tesista** (Regla de Cierre).

## Objetivo

Convertir la plataforma en un instrumento de experimentación científica:
pre-test/post-test de conocimiento persistidos, perfil enriquecido con
conocimiento previo, ruta sensible al conocimiento, métricas de
investigación automáticas, dashboard del investigador y exportación
CSV/Excel — sin romper ninguna funcionalidad existente.

---

## 1. Migraciones creadas

| Revisión | Archivo | Contenido |
|---|---|---|
| `f6a7b8c9d0e1` (head, sobre `e5f6a7b8c9d0`) | `backend/alembic/versions/f6a7b8c9d0e1_add_research_experiment_layer.py` | 5 tablas nuevas + 2 columnas en `learning_paths` (`knowledge_level`, `generation_duration_ms`). Guarded (no toca lo que ya exista) y reversible (`downgrade` verificado). |

## 2. Modelos creados (SQLAlchemy 2.0, `Mapped`/`mapped_column`)

| Modelo | Tabla | Rol |
|---|---|---|
| `KnowledgeTestQuestion` | `knowledge_test_questions` | Banco fijo de 36 ítems MCQ (4 × 9 módulos), versionado |
| `KnowledgeTestAttempt` | `knowledge_test_attempts` | Intento pre/post; único por (estudiante, curso, kind) |
| `KnowledgeTestAnswer` | `knowledge_test_answers` | Respuesta normalizada por pregunta (con copia de la correcta) |
| `ExperimentResult` | `experiment_results` | Comparación pre→post materializada (ganancias, niveles, tiempos) |
| `ResearchMetric` | `research_metrics` | Event-log genérico de métricas de investigación |

`LearningSession` NO se recreó: ya existía (Misión Activa) y se usa como
fuente de tiempo de estudio.

## 3. Archivos nuevos (backend)

- `backend/app/models/knowledge_test.py` · `backend/app/models/research.py`
- `backend/app/data/knowledge_test_bank.py` (+`__init__.py`) — banco + seed
  idempotente (uuid5 deterministas), enganchado best-effort al lifespan
- `backend/app/services/knowledge_test_service.py` — corrección, umbrales
  (<40/40–70/≥70), desglose por módulo, enriquecimiento del perfil,
  ExperimentResult
- `backend/app/services/research_metrics_service.py` — `record_metric`
  best-effort
- `backend/app/services/research_dashboard_service.py` — agregados SQL
- `backend/app/services/research_export_service.py` — CSV (BOM UTF-8) y
  XLSX (openpyxl, import-guard)
- `backend/app/schemas/knowledge_test.py`
- `backend/app/api/routes/knowledge_test.py` · `backend/app/api/routes/research.py`
- Tests: `backend/tests/test_knowledge_test.py` (27),
  `backend/tests/test_research_metrics.py` (3),
  `backend/tests/test_research_dashboard.py` (6)

## 4. Archivos modificados (backend)

- `backend/app/main.py` — registro de routers + seed en lifespan
- `backend/app/models/__init__.py` — registro de los 5 modelos
- `backend/app/models/student_progress.py` — 2 columnas ORM en `LearningPath`
- `backend/app/services/student_service.py` — `_initial_module_statuses`
  (desbloqueo por dominio ≥75%) + medición de duración de generación
- `backend/app/api/routes/students.py` — gate 409 `PRETEST_REQUIRED`
  (fail-open) + instrumentación de métricas en 5 handlers
- `backend/requirements.txt` — `openpyxl==3.1.5`
- `backend/tests/test_query_counts.py` — presupuesto 10→11 (+1 consulta
  constante del pre-test, no N+1)

## 5. APIs creadas (documentadas por OpenAPI en `/docs`)

**Estudiante** (`/api/students/knowledge-test`, rol estudiante):
- `GET  /{course_id}/status` — banco disponible, pre requerido, resúmenes
- `POST /{course_id}/start` `{kind: pre|post}` — crea o reanuda (409 si ya
  completado; post exige pre)
- `POST /attempt/{attempt_id}/submit` `{answers}` — corrige y clasifica
- `GET  /{course_id}/result?kind=` · `GET /{course_id}/comparison`

**Investigador** (`/api/research`, acceso abierto como `/api/evidence`):
- `GET /summary` — todas las métricas del dashboard
- `GET /students` — dataset por estudiante
- `GET /export?fmt=csv|xlsx` — descarga para SPSS/RStudio/Python

## 6. Componentes React creados

- `frontend/src/hooks/useKnowledgeTest.ts` · `frontend/src/hooks/useResearch.ts`
- `frontend/src/pages/estudiante/KnowledgeTest.tsx` — Evaluación
  Diagnóstica y Post-Test (misma pantalla, `kind` como prop) con fases
  intro→preguntas→resultado y comparación pre→post
- `frontend/src/components/auth/PretestGuard.tsx` — bloquea la Ruta hasta
  completar el pre-test (fail-open)
- `frontend/src/pages/evidencia/ResearchDashboard.tsx` —
  `/evidencia/investigacion` con KPIs, distribuciones, tabla y exportación

**Modificados:** `App.tsx` (rutas + guard), `DiagnosticTest.tsx` (solo el
handler final: conduce al pre-test; secciones A/B intactas — toque
autorizado), `Dashboard.tsx` (CTA Rendir Post-Test), `LearningPath.tsx`
(botón post-test en el banner de finalización), `EvidenceHub.tsx` +
`EvidenceLayout.tsx` (tarjeta e ítem de sidebar).

## 7. Pruebas realizadas

- **36 tests nuevos en verde** (instrumento, gate, perfilador, ruta,
  métricas, dashboard, export).
- **Baseline sin regresiones**: los fallos preexistentes de la rama
  (124 F / 21 E + 3 módulos con error de colección, previos a este trabajo)
  no aumentaron; el único ajuste fue el presupuesto del query-count test
  (+1 consulta constante, documentado).
- **Migración**: `upgrade head` + `downgrade -1` + `upgrade head` en la BD
  de desarrollo; seed idempotente verificado (2ª corrida = 0 inserciones).
- **Stack real**: backend arrancado; `/api/research/summary` devolvió datos
  reales (76 rutas, 7 perfiles), CSV con BOM y cabeceras SPSS-safe, XLSX
  con content-type correcto; endpoints de estudiante devuelven 401 sin token.
- **Frontend**: `npm run build` limpio (1.78 s).

## 8. Compatibilidad garantizada

- Estudiantes con ruta previa y sin pre-test: **nunca bloqueados** (guard
  frontend y gate backend los eximen).
- Banco no seedeado o status inaccesible: **fail-open total** — el flujo
  histórico queda intacto.
- Autenticación, arquitectura swarm y agentes: **no modificados** (la capa
  solo escribe la shared memory que `AdaptiveLearningAgent` ya leía).
- Todas las escrituras nuevas (perfil, memoria, métricas) son best-effort:
  jamás rompen el flujo del estudiante.

## 9. Posibles mejoras futuras (registradas, NO comprometidas)

1. Formas paralelas del instrumento (pre ≠ post equivalentes) si el asesor
   lo exige — el modelo ya versiona el banco.
2. Conectar `app/experiment/analysis.py` (ANOVA, Cohen's d, potencia) al
   dataset de `experiment_results` para estadística inferencial en el
   dashboard.
3. Tiempo por pregunta (`time_spent_seconds` ya existe en
   `knowledge_test_answers`; falta capturarlo en la UI).
4. Export adicional en formato `.sav` (SPSS nativo) vía pyreadstat.
5. Snapshot del intento de misión por regeneración (deuda ya registrada en
   SPEC_MISION_ACTIVA).

## 10. Validación pendiente (Regla de Cierre)

El recorrido completo debe ser validado manualmente por el tesista en
navegador real: login → onboarding → diagnóstico de estilo → **pre-test →
resultado → generar ruta** → misión → completar → **post-test →
comparación** → `/evidencia/investigacion` → **Exportar CSV/Excel**.
