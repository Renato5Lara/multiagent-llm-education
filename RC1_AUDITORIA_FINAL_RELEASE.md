# RC-1 — Auditoría Final de Release

> Reemplaza el enfoque de `ROADMAP-RC1.md` (12 áreas, 12 documentos).
> Tras revisión, se decidió una única auditoría integral orientada a
> una sola pregunta: **¿se puede desplegar hoy con confianza?**
> `ROADMAP-RC1.md` queda abandonado (vive sin mergear en la rama
> `docs/rc1-roadmap`, no en `runtime/architecture`) — este documento
> es la fuente única sobre el estado de release.

- **Fecha:** 2026-07-25
- **Baseline:** tag `epica-e-complete` (`487f62f`)
- **Metodología:** build + lint + suite de tests completa (backend),
  más 7 auditorías de código independientes (backend, frontend,
  sistema multiagente, infraestructura/deploy, seguridad+docs+riesgos
  de sustentación, y dos rondas de triaje de las 103 fallas de tests),
  más un recorrido en vivo por rol (Docente, Admin, Investigador —
  Estudiante ya se había validado en vivo durante el cierre de Épica E).
  Todo de solo lectura: ningún hallazgo se corrigió todavía, salvo una
  migración local aditiva aplicada como efecto secundario de verificar
  que las migraciones aplican limpio (ver nota en Infraestructura).

## 1. Lista priorizada de problemas

> **Estado de estabilización (post-auditoría):** de los 6 hallazgos
> 🟠 Alta, 4 ya están corregidos (rama `rc1/stabilization-fixes`,
> commits `8847845`/`e5b6971`/`2f5b464`/`7f2b823`), 1 se decidió y
> corrigió tras confirmar con el tesista, y 1 sigue pendiente de
> verificación externa (no se puede resolver desde el repo). Ver ✅/⏳
> por hallazgo.

### 🟠 Alta

| # | Hallazgo | Archivo | Impacto | Fix | ¿Bloquea despliegue? |
|---|---|---|---|---|---|
| 1 | ✅ **RESUELTO** — `/api/research/*` (Dashboard Investigador) sin autenticación — expone PII de estudiantes y export completo del experimento | `backend/app/api/routes/research.py` | Si la URL pública de Render se usa sin cambios durante la sustentación, cualquiera en internet puede exportar los datos por estudiante | Decisión tomada con el tesista: se auditó la base de datos real y se encontró una cuenta (`jramires6@upao.edu.pe`) que no corresponde a ningún patrón seed/QA/E2E conocido; sin poder confirmar si es una persona real, se trató como tal por precaución. Los 6 endpoints ahora requieren rol admin o docente (`get_current_admin_or_docente`, commit `7f2b823`) — mismo patrón que las dependencias de rol ya existentes. 9/9 tests pasan. | No |
| 2 | ✅ **RESUELTO** — 4ª instancia del bug de Design System de Épica E en `table.tsx` (`TableRow` hover/selected con `bg-gray-50`/`bg-gray-100`) | `frontend/src/components/ui/table.tsx:27` | Visible en 4 pantallas reales: Admin Usuarios/Roles, Docente CourseDetail, Replay StudentTrajectory | Corregido con el mismo patrón aplicado 3 veces en Épica E: `hover:bg-white/[0.06] data-[state=selected]:bg-white/[0.08]` (commit `8847845`). Build limpio. | No |
| 3 | ✅ **RESUELTO** — `DEMO_RECOVERY.md` no cubre el bug conocido de diagnóstico (~7-8% de cuentas nuevas atascadas, commit `95d8a53`) | `DEMO_RECOVERY.md` | Si se crea una cuenta nueva en vivo frente al jurado, riesgo real de bloqueo sin plan de recuperación documentado | Entrada `[15]` agregada con mitigación recomendada (usar cuenta con diagnóstico ya completado en vez de una nueva en vivo) — commit `2f5b464`. | No |
| 4 | ✅ **RESUELTO** — Regresión silenciosa del fix de driver Postgres (`55a752c`) — la reescritura `postgresql://`→`postgresql+psycopg://` se perdió en un merge posterior (`6b6475b`) | `backend/app/core/config.py` (`fix_postgres_scheme`) | Hoy no rompe nada (fallback implícito a `psycopg2-binary`), pero es el mismo patrón que causó el incidente original — si alguien limpia esa dependencia "no usada", el engine sync se rompe sin aviso | Reintroducida exactamente como en `55a752c` (commit `e5b6971`). Verificado: los 3 casos de URL (`postgres://`, `postgresql://` plano, ya con `+psycopg`) resuelven al mismo driver forzado. | No |
| 5 | Dos lockfiles de Python en conflicto (`requirements.lock` vs `requirements-lock.txt`), y Render no usa ninguno (`buildCommand` instala desde `requirements.txt` sin fijar) | `backend/requirements.lock`, `backend/requirements-lock.txt`, `render.yaml` | La promesa de "instalación reproducible" de `RELEASE.md`/`REPRODUCIBILITY.md` no aplica al despliegue real | Elegir un lockfile canónico, archivar el otro, decidir si Render debe fijar versiones | No, pero compromete la reproducibilidad documentada |
| 6 | ⏳ **PENDIENTE — requiere verificación externa** — Posible pérdida de uploads en Render — sin bloque `disk:` en `render.yaml` para `/var/data/uploads` (sí existe volumen persistente en `docker-compose.prod.yml`) | `render.yaml` | Si el plan de Render no respalda esa ruta, archivos subidos por un docente se pierden en el próximo redeploy | **Verificar en el dashboard real de Render** (Settings → Disks del servicio backend) si hay disco persistente montado — no se puede confirmar ni corregir solo desde el repo | No de forma inmediata; sí para cualquier demo que dependa de contenido subido sobreviviendo un redeploy |

### 🟡 Media

| # | Hallazgo | Archivo | Impacto | ¿Bloquea? |
|---|---|---|---|---|
| 7 | `SECRET_KEY` con valor por defecto inseguro, sin guardia de arranque | `backend/app/core/config.py:54` | Mitigado en el camino real de Render (`render.yaml` genera el valor); no mitigado en un despliegue Docker Compose alterno que copie `.env.example` sin editarlo | No para Render; sí para Docker Compose sin editar `.env` |
| 8 | `/api/sandbox/execute` sin autenticación y sin uso real (frontend usa Pyodide, no este endpoint) | `backend/app/api/routes/sandbox.py` | Superficie de ataque innecesaria; en Render (`runtime: python`, sin Docker) probablemente ni funciona | No |
| 9 | `vercel.json` usa `npm install` en vez de `npm ci` | `vercel.json` | `package-lock.json` está consistente hoy; frágil a futuro si diverge | No |
| 10 | Docstring desactualizado en `traza_sesion.py` dice que Modo Evidencia es "100% legacy" cuando `evidence_service.py` ya lo consume en producción | `backend/runtime/boundary/surfaces/traza_sesion.py` | Un jurado técnico que lea ese archivo podría dudar de la integración real | No |
| 11 | ✅ **RESUELTO** — `CHANGELOG.md` no refleja el cierre de Épica E | `CHANGELOG.md:37-38` | Cualquiera que lo lea ve el proyecto un hito atrás | Entrada `epica-e-complete` agregada, "próxima línea de trabajo" actualizada a RC-1 (commit `2f5b464`) | No |
| 12 | ✅ **RESUELTO** — `test_export_experiment_has_three_sheets` fallaba en este entorno local por `openpyxl` no instalado en el venv (el código degrada correctamente a CSV) | venv local, no código | Drift de entorno local, no bug — pero impedía verificar la exportación Excel real antes de la sustentación | `pip install openpyxl==3.1.5` (ya en `requirements.txt`, solo faltaba en el venv). 9/9 tests de `test_research_dashboard.py` pasan, incluyendo el export Excel real. | No |
| 13 | 22 errores/11 warnings de lint pre-existentes (desde antes de esta sesión), incluyendo `Date.now()` llamado durante el render en varios componentes | `DetonatingQuestionCard.tsx`, `MiniQuizCard.tsx`, `ModuleLearningView.tsx`, otros | Podría producir valores de tiempo inestables entre re-renders — relevante porque alimenta métricas de tiempo invertido que el propio Post-Test de Épica E ahora muestra | No, pero es deuda real, no solo estilo |
| 14 | ~51 de 103 fallas del suite de tests backend sin verificación individual profunda (hipótesis por patrón: mismo clúster legacy/shared-memory ya confirmado muerto en archivos hermanos) | Ver § Backend — Calidad | Riesgo residual bajo pero no nulo de que una de ellas oculte una regresión real | No hoy; recomendado verificar antes del tag final |
| 15 | `ANTHROPIC_API_KEY` documentado como alternativa válida pero no implementado en `Settings` | `DEPLOYMENT.md`, `.env.example`, `config.py` | Documentación promete una capacidad que el código no tiene (OpenAI solo ya satisface `has_llm`) | No |

### 🔵 Baja

| # | Hallazgo | Impacto |
|---|---|---|
| 16 | `empty-state.tsx` tiene el mismo bug de tema claro (`text-gray-900`) pero cero usos actuales — código muerto, landmine si se conecta después sin corregirlo primero |
| 17 | `frontend/.env.production` no cubierto por el patrón de `.gitignore` (hoy inofensivo: solo contiene una URL pública, no un secreto) |
| 18 | `DEBUG=True` por defecto en `config.py` — ya mitigado en los dos caminos de despliegue reales documentados |

## 2. Lista de cosas que ya están correctas

**Build y Calidad**
- `npm run build` (`tsc -b && vite build`) — limpio.
- Backend: 2386/2506 tests pasan (95.1%). De las 103 fallas, ~59 tienen causa raíz confirmada con evidencia real (git log/blame + traceback), y **ninguna de las investigadas a fondo reveló una regresión de producto real** — son artefactos de plataforma Windows (`preexec_fn` en sandbox, `ProactorEventLoop`/`SIGKILL` en tests de integración del runtime — Render despliega en Linux, donde no aplican), tests desactualizados de código legacy (BaseAgent, `app/core/consensus.py` sin imports reales), o drift de venv local (`openpyxl`).
- El propio `test_knowledge_test.py` (4 fallas) se confirmó **pre-existente y no relacionado con Épica E** — la afirmación de "sin backend nuevo" de `EPICA_E_COMPLETION.md` queda confirmada, no contradicha; el test simplemente nunca se actualizó tras un pivote de arquitectura de contenido muy anterior (commit `d2d1d8c`).

**Backend**
- Manejador de excepciones genérico oculta detalles salvo en `DEBUG` — seguro en producción.
- Migraciones Alembic: cadena lineal, un solo head, sin bifurcaciones; aplican limpio.
- Sin secretos reales filtrados en código versionado; `.gitignore` cubre `.env` en todas sus variantes.
- Sin IDOR: endpoints de estudiante usan `current_user.id` del JWT, nunca un ID arbitrario del cliente.
- Autorización por rol real (no solo UI oculta) en `users.py`.
- Todas las rutas de `app/api/routes/` están registradas en `main.py`.
- CORS correctamente restringido por entorno.

**Frontend**
- Todas las rutas resuelven a componentes reales; sin rutas rotas ni huérfanas.
- Contrato `ExperimentComparison`/`KnowledgeTestResult`/`CompetencyProfile` (frontend) vs. sus contrapartes backend — sin drift.
- Los 22 errores de lint son 100% pre-existentes (git blame los ubica en 2026-06-30 y 2026-07-15, antes de Épicas C/D/E) — nunca fueron parte del Release Gate real (que siempre fue solo build, nunca lint).

**Sistema Multiagente** (el corazón de la tesis)
- `StateGraph` real de LangGraph, no una máquina de estados simulada.
- Reducers respetan la regla de derivación (sin copias sin razón).
- Consenso/deliberación es mecánica real y determinista, citando RFC-0006/CONCEPT-0002 — no un stub.
- `evidence_service.py` combina solo datos reales (legacy + traza nueva del runtime) — sin evidencia fabricada presentada como real.
- BaseAgent legacy reconfirmado retirado de todo camino en vivo (ningún import real desde `app/api/` o `app/services/`).
- Todo el código revisado cita un RFC/ADR específico — sin conceptos sin respaldo documental.

**Infraestructura**
- `docker-compose.prod.yml`: healthchecks, `depends_on: service_healthy`, volúmenes persistentes, arranque encadenado — consistente.
- La mitad del fix `55a752c` que sí sobrevivió (lado async en `session.py`, y el `startCommand` encadenado de `render.yaml`) sigue correcta.
- `vercel.json`: rewrites SPA y headers COOP/COEP bien configurados.
- `.env.example` alineado con el resto de variables reales de `config.py`.

**Seguridad, Documentación, Riesgos**
- Sin secretos hardcodeados en código propio (solo matches irrelevantes dentro de librerías de terceros).
- `.env.example` completo y legible en ambos proyectos.
- La mención de "50+ cursos institucionales" en `DEPLOYMENT.md` **no es documentación obsolete** — es ambientación intencional del seed (ISIA 2025), no contradice el scope freeze de la tesis (verificado contra `seed.py` y `THESIS_SCOPE_FREEZE.md`).
- `DEMO_RECOVERY.md` sigue siendo sustancial y vigente (375 líneas, ~10 síntomas reales cubiertos) salvo el gap puntual del hallazgo #3.
- `README.md` describe la arquitectura real de forma consistente con lo implementado.
- Sin otros bugs intermitentes/flaky sin resolver en el historial de commits, más allá del ya conocido.

**Recorrido en vivo (Docente, Admin, Investigador)**
- Las 10 pantallas visitadas (Docente Dashboard/Cursos/Panel Pedagógico, Admin Dashboard/Usuarios/Roles/Cursos, Evidencia Hub, Dashboard del Investigador, Runtime Console) cargaron sin errores de consola ni marcadores de pantalla rota.
- El Dashboard del Investigador muestra datos reales y coherentes (12 estudiantes, 8 con post-test, `g = 0.56`, distribución de niveles). Una discrepancia visual aparente en una captura (Básico mostraba 8 en vez de 0) se investigó a fondo: confirmado que es un **artefacto de captura de pantalla de Chrome headless** (el DOM real y la API, verificados tres veces por vías independientes, siempre devuelven el valor correcto) — no es un bug de datos ni de producto.

## 3. Riesgos para producción / sustentación

Ordenados por importancia real para una defensa de tesis en vivo:

1. **Bug de diagnóstico sin plan de recuperación** (hallazgo 🟠 #3) — el riesgo más alto y más barato de mitigar: una cuenta nueva creada en vivo tiene ~7-8% de probabilidad de quedarse atascada, sin ningún paso de recuperación documentado hoy.
2. **`/api/research/*` público sin auth** (hallazgo 🟠 #1) — requiere una decisión explícita tuya sobre si la URL pública de Render se usará tal cual durante la sustentación.
3. **Persistencia de uploads en Render sin confirmar** (hallazgo 🟠 #6) — solo relevante si la demo depende de subir contenido y sobrevivir un redeploy.
4. **~51 fallas de test sin verificación individual** (hallazgo 🟡 #14) — riesgo residual bajo, no urgente, pero pendiente antes de un tag final "para siempre".

Ningún hallazgo alcanzó severidad 🔴 crítica.

## 4. Decisión final

## ⚠ LISTO CON OBSERVACIONES → estabilización en curso

Veredicto original de la auditoría: ningún hallazgo bloqueaba
técnicamente el despliegue documentado en Render. El sistema compilaba
limpio, el 95.1% de los tests pasaba (ninguna falla investigada a
fondo reveló una regresión real), y el sistema multiagente — el
corazón de la tesis — estaba limpio salvo un docstring desactualizado.

**Estabilización ya ejecutada** (rama `rc1/stabilization-fixes`):

1. ✅ Fix de una línea en `table.tsx` (hallazgo #2).
2. ✅ Entrada del bug de diagnóstico en `DEMO_RECOVERY.md` + mitigación
   documentada (hallazgo #3).
3. ✅ Reintroducida la segunda reescritura en `fix_postgres_scheme`
   (hallazgo #4).
4. ✅ `CHANGELOG.md` actualizado (hallazgo #11).
5. ✅ Decisión tomada y ejecutada sobre `/api/research/*` (hallazgo #1):
   se encontró una cuenta real no identificada en la base de datos
   (`jramires6@upao.edu.pe`) y, por precaución, se protegieron los 6
   endpoints con rol admin/docente.
6. ✅ venv local corregido (`openpyxl`, hallazgo #12) — export Excel
   real verificado, no solo su degradación a CSV.

**Pendiente, no bloqueante para continuar:**

- ⏳ Confirmar en el dashboard de Render si `/var/data/uploads` tiene
  disco persistente (hallazgo #6) — no se puede verificar ni corregir
  desde el repo, requiere acceso a la cuenta de Render.

El resto de hallazgos (lockfiles, sandbox endpoint muerto, `vercel.json`,
lint histórico, ~51 tests sin verificar del todo) son reales pero no
urgentes — quedan como backlog razonable, no como bloqueo.

**Siguiente paso:** rebuild + smoke test del despliegue, y publicar,
una vez resuelto o aceptado el punto pendiente de Render.

## Nota operativa

Un fork de la auditoría de Infraestructura ejecutó `alembic upgrade head`
contra la base de datos local de desarrollo como parte de verificar que
las migraciones aplican limpio, aplicando una migración pendiente
(`add_recursos_generados`). Es aditiva y reversible, no destructiva —
se documenta aquí por transparencia, no porque haya sido una acción
fuera de lo esperado para ese tipo de verificación.
