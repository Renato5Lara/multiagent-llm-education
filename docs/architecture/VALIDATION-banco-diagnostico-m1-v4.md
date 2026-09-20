# Registro de validación del banco de diagnóstico de M1 (versión 4)

- **Estado:** Registro de ejecución — hechos observados el 2026-09-20. No es
  una especificación.
- **Fecha:** 2026-09-20
- **Pregunta que responde (y que ningún otro documento responde):** ¿qué se
  ejecutó y qué quedó demostrado al implementar y activar el banco de
  diagnóstico v4 descrito en `DESIGN-banco-diagnostico-m1.md`, y qué quedó
  abierto?
- **No es:** el diseño del instrumento (eso es `DESIGN-banco-diagnostico-m1.md`);
  ni una medición de rendimiento; ni una demostración de la calidad
  psicométrica del banco. No modifica `DESIGN-banco-diagnostico-m1.md`.

Regla de lectura: este documento distingue lo **verificado** de lo **abierto**.
Donde una afirmación no se probó, se dice que no se probó.

## 1. Alcance

Implementación en código del banco v4 (8 ítems de M1) y de sus dependencias
(versionado de intentos, puerta del Post-Test, render multilínea), activación
real en la BD de desarrollo y dos recorridos extremo a extremo del Pre-Test.

Fuera de alcance, y sin tocar en la fase (comprobado sobre el diff de los 8
commits, §2): `backend/runtime/`, migraciones, modelos, `module1.ts`,
`module2.ts`, datos históricos.

## 2. Commits de implementación

Rama `feat/pretest-m1-v4`. Ocho commits, ocho archivos:

| Fase | Commit | Contenido |
|---|---|---|
| C0 especificación | `319c239` | `docs/architecture/DESIGN-banco-diagnostico-m1.md` |
| C1 render multilínea | `3bf739d` | `frontend/src/pages/estudiante/KnowledgeTest.tsx` |
| C5 versionado | `5c6de99` | `knowledge_test_service.py`, `test_knowledge_test_versioning.py` |
| C5 test | `eee4dc8` | `test_knowledge_test_versioning.py` |
| C4 puerta Post-Test | `bc5ee18` | `knowledge_test_service.py`, `test_knowledge_test_post_gate.py` |
| C4 corrección: M1 explícito | `e6edd35` | `knowledge_test_service.py`, `test_knowledge_test_post_gate.py` |
| C2 banco v4 | `99e6ba9` | `knowledge_test_bank.py`, `test_knowledge_test.py`, `test_knowledge_test_bank_v4.py`, `test_knowledge_test_post_gate.py` |
| Corrección UI "8 situaciones" | `029a4ca` | `KnowledgeTest.tsx` (1 línea) |

Comprobación sobre `git diff --name-only 319c239^..029a4ca`: ningún archivo
bajo `backend/runtime/`, `alembic/versions`, `backend/app/models/`, ni
`module1.ts`/`module2.ts`. La columna `bank_version` de los intentos es
anterior a la fase (commit `12d0c03`, migración `f6a7b8c9d0e1`); la fase no
añade migración ni modifica modelos.

**Una línea toca `topic_by_module`** (commit `5c6de99`): en
`enrich_profile_from_pretest`, la fuente de las preguntas pasó de
`get_bank_questions(db)` a `_questions_of_attempt(db, attempt)`. Es parte
legítima del versionado (el perfil se calcula con las preguntas de la versión
del propio intento). No cambia la estructura `{module_number: topic}`; el
problema conocido de esa estructura se registra en §11.

## 3. Instrumento activado (v4)

- 8 preguntas, `course_code = IS301`, `version = 4`, `module_number = 1` en
  todas, `order` global único `0..7`.
- Competencias: COMP-0 ×2, COMP-2 ×2, COMP-5 ×2, COMP-3 ×2 (COMP-1 y COMP-4 no
  se miden, como declara el diseño).
- Funciones: concebir ×2 (`order` 0-1), representar ×2 (2-3), ejecutar ×4 (4-7).
- `correct_index`: 0, 1, 2 y 3 aparecen dos veces cada uno.
- Orden de servicio por `order` ascendente. Numeración de ítems del diseño:
  `order` 0, 1, 2, 3, 4, 5, 6, 7 = ítems 1, 2, 3, 4, 7, 8, 5, 6 (secuencia
  1, 2, 3, 4, 7, 8, 5, 6, decisión O = B del diseño).

| `order` | ID | Competencia |
|---|---|---|
| 0 | `ffe48c81-d87c-5096-8858-7192b7a638c3` | comp_0_problema |
| 1 | `48a6d5c9-0732-5341-b664-e4c237f964dc` | comp_0_problema |
| 2 | `a5d0e7d9-90f8-5562-87a9-8e7c17e260ab` | comp_2_interpretacion |
| 3 | `7d58a114-e6b0-5700-8c49-30ee018e4f5e` | comp_2_interpretacion |
| 4 | `a552a366-40eb-5b3b-955d-2aa600f6586e` | comp_5_razonamiento |
| 5 | `f9183df3-3e3d-5911-bd73-c5e76eb70de3` | comp_5_razonamiento |
| 6 | `259ea7b7-f3c1-5b99-b1cb-8611773a3bec` | comp_3_simulacion |
| 7 | `90a80e35-5e37-506a-88d5-4cc296417b69` | comp_3_simulacion |

## 4. Activación real y estado de la BD

**Mecanismo.** `BANK_VERSION = 4` es una constante del código
(`knowledge_test_bank.py`), no una variable de entorno. La activación es el
arranque normal del backend: el `lifespan` (`main.py`) ejecuta
`seed_knowledge_test_bank`, de forma idempotente y best-effort. No se ejecutó
ningún seed manual.

**Comando:** `cd backend && .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000`
(sin `--reload`, enlazado a localhost). Log del seed:
`Banco de conocimiento seedeado: 8 preguntas nuevas (v4)`. `GET /health` → 200.
Sin errores ni warnings en el log de las dos ejecuciones.

**Antes de arrancar** (BD real, solo lectura):

- Intentos `in_progress`: 0.
- Preguntas: v1 = 44 (IS301 + SWA101), v2 = 12, v3 = 12, v4 = 0 (total 68).
- Intentos: 35, todos `completed` y con `bank_version` no nulo:
  v2 = 3 pre + 1 post; v3 = 29 pre + 2 post.
- `ExperimentResult`: 3 (pares pre/post de la misma versión: v2/v2, v3/v3, v3/v3).
- 420 respuestas (35 × 12), sin huérfanas ni respuestas ligadas a una versión
  distinta de la de su intento.
- Alembic: `e7f8a9b0c1d2` = head del código (29 archivos de migración).
- Los 8 IDs de v4 no colisionan con ningún ID existente.

**Después:** v1 = 44, v2 = 12, v3 = 12, **v4 = 8**, total 76. Los 8 registros
v4 coinciden con los IDs esperados (8 presentes, 0 inesperados, 0 colisiones),
`order` `0..7` sin huecos, `module_number = 1`. La instantánea de datos
históricos (§8) fue idéntica a la previa.

**Comprobación operativa (solo lectura, sesión de solo lectura):**
`BANK_VERSION` = 4; `is_bank_seeded` = `True`; `get_bank_questions()` devuelve
8 filas v4 con los IDs esperados; `get_bank_questions(version=3)` devuelve 12 y
`version=2` devuelve 12. `GET /api/students/knowledge-test/{id}/status` sin
token → 401.

## 5. Idempotencia del seed

Segunda ejecución del mecanismo normal (detención con SIGTERM y nuevo
arranque): 0 inserciones (el log no contiene `seedeado`); el hash de las 8
filas v4, incluyendo `created_at` e `is_active`, fue idéntico antes y después
(`63cd65660378b14319902abb2df31ad0`); la instantánea histórica idéntica; total
76.

## 6. Versionado de intentos y puerta del Post-Test

- Cada intento queda ligado a su `bank_version` al crearse; se sirve, reanuda,
  puntúa y perfila con su propia versión (C5). El Post-Test se sirve con la
  versión del Pre-Test del estudiante (decisión P1 del diseño §8).
  `compute_experiment_result` solo materializa la comparación si pre y post
  tienen la misma versión.
- Puerta del Post-Test: para v4 exige completar M1
  (`POST_TEST_REQUIRED_MODULE_ORDER_BY_BANK_VERSION = {4: 1}`); v2 y v3
  conservan su techo de módulos.
- **Esto está cubierto por tests, no por un recorrido real.** Ningún Post-Test
  se ejecutó contra v4 en esta fase.

## 7. Tests

- Suites relacionadas con el test de conocimiento: `test_knowledge_test.py`,
  `test_knowledge_test_bank_v4.py`, `test_knowledge_test_post_gate.py`,
  `test_knowledge_test_versioning.py`, `test_reconciliacion_p0.py`,
  `test_research_dashboard.py`, `test_runtime_bridge.py`.
- Resultado: **129 pasaron, 0 fallaron** (8 min 44 s), con 132 warnings
  (`SAWarning` sobre transacción del fixture SQLite en el seed del banco y un
  `DeprecationWarning` de HTTP 422).
- Los tests usan SQLite en memoria (`conftest.py`). Se ejecutaron con
  `DATABASE_URL` apuntando a un puerto inexistente, de modo que cualquier
  acceso accidental a la BD real habría fallado. La comparación fila a fila de
  la BD real antes y después de los tests: 0 filas nuevas, 0 modificadas o
  eliminadas.
- No se ejecutó la suite completa del proyecto, solo las 7 anteriores.

## 8. Integridad de datos históricos

**Método.** (a) Instantánea por fila de las 50 tablas públicas: `md5(fila::text)`
de cada fila, antes del primer E2E (14 069 filas) y después del segundo;
comparación de conjuntos. (b) Hashes por columnas seleccionadas de las tablas
del instrumento.

**Resultado (a):** ninguna fila preexistente resultó modificada o eliminada al
final de ambos E2E (comparación contra la instantánea previa al primero). Solo
aparecieron filas nuevas atribuibles a los dos estudiantes de prueba (§10, §15).

La instantánea (a) se tomó **después** de la activación de v4; la integridad
de la activación en sí (68 → 76 filas) se apoya en los hashes de (b), tomados
antes y después de arrancar el backend.

**Línea base (b).** Idéntica antes y después de la activación. Tras los dos
E2E se mantuvieron idénticos los hashes de preguntas v1/v2/v3, de intentos
históricos y de `ExperimentResult`; el hash global de respuestas cambia
porque se añadieron 16 respuestas de los estudiantes de prueba (lo que cubre
(a)):

| Objeto | Filas | Hash md5 |
|---|---|---|
| Preguntas v1 | 44 | `a2f900590feac0e1c8e9d3e9eb96c50f` |
| Preguntas v2 | 12 | `7eec46fe1e5840906fcec9fef1127c9c` |
| Preguntas v3 | 12 | `33f535d39da3c7e72630e22b1f572ccb` |
| Intentos históricos (todos los no-E2E) | 35 | `c10d18cc7c8b7381783b00fea1c017f9` |
| Respuestas (antes de los E2E; 436 después) | 420 | `a78f2e3ebc9179ba930a139dcdbd923d` |
| `ExperimentResult` | 3 | `d61019aa054ca64c00a80be048a21663` |

Fórmulas (`string_agg(... , ';' order by id)`):

- Preguntas: `id||'|'||topic||'|'||text||'|'||options::text||'|'||correct_index||'|'||"order"||'|'||module_number`, por versión.
- Intentos: `id||status||coalesce(bank_version,'')||coalesce(score,'')`.
- Respuestas: `id||selected_index||correct_index`.
- `ExperimentResult`: `id||pre_attempt_id||post_attempt_id`.

Estos hashes cubren solo las columnas indicadas; la garantía sobre el resto de
columnas es la comparación por fila de (a). No se afirma "cero regresiones": se
afirma que no se observaron modificaciones de datos históricos y que las suites
ejecutadas pasaron.

## 9. Validación visual (T3)

**Entorno.** Vite (frontend real) con un API simulado local (fuera del repo)
que servía los 8 ítems leídos de `knowledge_test_bank.py`; sin backend real ni
BD. Navegador: Chromium headless con Playwright (la extensión de Chrome no
conectó).

Las referencias usan `order` (0-7) para evitar ambigüedad con la numeración
de ítems del diseño (§3).

**Verificado:** opciones multilínea con saltos de línea preservados
(`white-space: pre-line`) en `order` 2, 3, 6 y 7; `font-mono` solo en las
opciones que contienen salto de línea, y tipografía proporcional en las de una
línea; el glifo `↓` del diagrama de flujo (`order` 3) se dibuja con JetBrains
Mono (una sola fuente utilizada, sin fuente de respaldo); la línea en blanco
de una opción de `order` 7 (`Hola⏎⏎Adiós`) se preserva; sin errores de
consola.

**Observaciones (no corregidas, preexistentes o no bloqueantes):** en
`order` 6 una opción de una línea queda en tipografía proporcional junto a
tres opciones multilínea en monoespaciada; todos los enunciados usan
`font-mono` desde antes de C1. La pantalla de introducción decía "12
situaciones"; se corrigió a "8 situaciones" en `029a4ca` (el texto está
escrito a mano en el frontend).

## 10. Recorridos extremo a extremo del Pre-Test v4

**Entorno común.** Backend real (`127.0.0.1:8000`), PostgreSQL real, frontend
Vite y Chromium headless (Playwright); el backend real ejecutó el flujo,
incluidas llamadas reales a OpenAI. Cada estudiante es una cuenta nueva de
prueba; la única fila insertada directamente fue `users`, y el resto lo
crearon los endpoints reales. El onboarding creó la matrícula al IS301 real,
sin crear objetivos (8 antes y después). Las sesiones del navegador se
inyectaron con tokens obtenidos por HTTP; no se escribió ninguna contraseña
en el navegador. El diagnóstico Likert (VARK, perfil visual) se hizo por API.
No se ejecutó ningún Post-Test.

### 10.1 Escenario 8/8 → `avanzar`

- Estudiante `e2e-v4-f3e04c@upao.test`; intento `8a64897c-1e1c-4d94-bdab-eced676bad64`.
- `/start` sirvió 8 preguntas v4, sin `correct_index`, con `order`
  `[0..7]` (secuencia de ítems 1, 2, 3, 4, 7, 8, 5, 6). Enunciado y opciones
  de los 8 ítems coincidieron exactamente con el banco.
- Respuestas: las 8 correctas. Intento `completed`, `bank_version = 4`, 8/8,
  100 %, nivel `avanzado`, `module_breakdown = {"1": {8/8}}`; 8 respuestas
  ligadas a preguntas v4; `question_order` = `0..7`.
- Perfil de competencias: 4 competencias (COMP-0/2/3/5), todas "dominado".
- Evidencia al Runtime: 5 claves de idempotencia `completed` del Pre-Test (4
  por competencia + 1 del objetivo M1 `7bf31573-e7d9-4a44-ab9e-2b2f6e2793f2`).
- Ruta (`3e7ea35d-5ded-4317-bfcc-ee0d7bacb843`): 8 módulos. M1 `available`,
  sin `completed_at` ni puntaje; M2 `available` y frontera; M3–M8 `locked`.
  `avance_por_objetivo` → `{1: 'avanzar'}`.
- **Hueco:** la pantalla de resultado inmediata no se capturó (el script se
  cerró tras el envío por una condición de espera incorrecta). La ruta se
  generó con la acción "Generar ruta adaptativa" de la pantalla de ruta, no
  desde el botón de la pantalla de resultado.

### 10.2 Escenario 0/8 → `reforzar`

- Estudiante `e2e-v4-reforzar-5f2df4@upao.test`; intento
  `b4911738-4864-452d-aba1-11985eea3bf5`.
- Respuestas deliberadamente incorrectas: `(correct_index + 1) mod 4` en cada
  ítem. Antes de enviar se verificó en el navegador que el radio marcado
  coincidía con el índice esperado y se leyó el borrador (`localStorage`): 8
  respuestas, exactamente las esperadas y ninguna igual a la correcta. Se
  eligió 0/8 porque es el único escenario con confianza por encima de θ (§11).
- Intento `completed`, `bank_version = 4`, 0/8, 0 %, nivel `basico`,
  `module_breakdown = {"1": {0/8}}`; 8 respuestas incorrectas ligadas a v4.
- Perfil: 4 competencias al 0 %. Evidencia: 5 claves `completed`.
- Pantalla de resultado inmediata (capturada **antes** de generar la ruta): sin
  errores de consola; 4 competencias al 0 %; sin datos de versiones anteriores;
  sin módulos.
- Ruta (`dbff2187-6193-47e7-86c3-f03d41b62789`): 8 módulos. M1 `available` y
  frontera, sin `completed_at` ni puntaje; M2–M8 `locked`. La pantalla de ruta
  mostró "Refuerzo de fundamentos… Temas prioritarios: Introducción a la
  programación" (el primer estudiante mostró "Énfasis en aplicación").
- **Desviación:** la ruta también se generó con "Generar ruta adaptativa",
  porque el navegador se cerró tras capturar el resultado y el botón de la
  pantalla de resultado es de un solo uso.

### 10.3 Contraste

| | 8/8 | 0/8 |
|---|---|---|
| Veredicto del Runtime (objetivo M1) | `avanzar` | `reforzar` |
| M1 | `available`, sin dominio otorgado | `available`, sin dominio otorgado |
| M2 | `available` (frontera) | `locked` |
| M3–M8 | `locked` | `locked` |

En ninguno de los dos casos el Pre-Test otorgó dominio (`completed`) de M1.

## 11. Cadena causal observada del Runtime

Leída en solo lectura del estado del Runtime (política `v2`, θ = 0.5) para el
segundo estudiante:

1. Hecho `T-000040`: competencia "introduccion-a-la-programacion", 8 errores
   de 8, índices `[0..7]`.
2. Interpretación `T-000042` (autor Diagnosticar, procedencia LLM):
   `dominada: false`, `errores: 8`, respaldo `T-000040`. La regla es
   `dominada = errores < 2` (`runtime/domain/diagnosticar/productor.py`,
   scoring-v1); la variante LLM recibe la misma regla en su prompt.
3. Confianza: 0.6756 (límite inferior de Wilson de 8/8 = 0.676), por encima de
   θ = 0.5.
4. Propuesta `T-000043` (autor Remediar, procedencia LLM): `{"accion":
   "reforzar"}`, respaldo `T-000042`, vigente
   (`runtime/domain/remediar/productor.py`, `_producir_por_objetivo`).
5. `avance_por_objetivo` → `{1: 'reforzar', 2: None, 3: None}`.

Primer estudiante (contraste): hecho `T-000038` con 0 errores de 8;
interpretación `dominada: true`, `errores: 0`, confianza 0.6756; propuesta de
Orientar `{"accion": "avanzar"}`, confianza 0.6756, respaldo `T-000040`;
`avance_por_objetivo` → `{1: 'avanzar'}`.

**Precisión importante.** El estado final de M2 (`locked`) no distingue por sí
solo un veredicto `reforzar` de la ausencia de veredicto: con o sin veredicto,
`_initial_module_statuses_con_runtime` y `_initial_module_statuses` producen
`[available, locked × 7]`. Lo que demuestra que el resultado proviene de la
evidencia es el veredicto que devuelve el Runtime y su cadena de respaldo, no
el bloqueo observable.

Fuerza de evidencia (límite inferior de Wilson) de `k` fallos sobre 8 ítems
(`runtime/domain/shared/calibracion.py`): k = 2: 0.071; 3: 0.137; 4: 0.215; 5:
0.306; 6: 0.409; 7: 0.529; 8: 0.676.

## 12. Archivos deliberadamente fuera de alcance

- Los cinco archivos modificados ajenos a la fase, que **no** forman parte de
  ningún commit de ella: `.claude/settings.local.json`,
  `.codegraph/daemon.pid`, `CLAUDE.md`, `backend/app/api/routes/auth.py` y
  `backend/app/main.py`. `main.py` y `auth.py` contienen instrumentación E1
  (activa solo con `E1_INSTRUMENTATION=1`, que no se definió ni figura en
  `backend/.env`); el backend se ejecutó con esas modificaciones sin
  commitear presentes en el árbol.
- Los 23 elementos untracked preexistentes (`backend/scripts/…` y
  `docs/architecture/ADR/.impeccable/`).
- Los scripts y capturas de los recorridos viven fuera del repositorio.

## 13. Comprobación previa al cierre

Auditoría de solo lectura previa a este documento: el estado de `git status`
fue idéntico al inicial; ningún cambio de la fase quedó sin commitear.

## 14. Limitaciones y hallazgos pendientes

1. **`topic_by_module` colapsa con v4.** La estructura `{module_number: topic}`
   con `module_number = 1` en los 8 ítems produce una sola clave, y los campos
   `strengths`/`weaknesses` del `knowledge_assessment` del `DiagnosticResult` y
   de la memoria compartida dependen de ella. Cuál `topic` conserva depende del
   orden de iteración; no se observó en datos. Fuera de alcance de esta fase.
2. **Rango intermedio de errores sin calibrar.** Solo se probaron 0/8 y 8/8.
   Con 2 a 6 errores, la fuerza de evidencia queda por debajo de θ = 0.5 y no se
   determinó qué veredicto produce el Runtime. Es una cuestión de calibración
   de la política, no un defecto de la activación.
3. **Post-Test v4 no ejecutado.** La puerta (M1 completado) y el emparejamiento
   pre/post por versión están cubiertos por tests, no por un recorrido real.
4. **Pantalla de resultado del primer E2E no capturada** (§10.1); sí validada en
   el segundo.
5. **Pantalla de resultado con todo al 0 %:** el panel "Tu punto de partida"
   muestra en verde "Razonamiento computacional 0 %" (empate al 0 %). Cosmético;
   no corregido.
6. **`resumed` en `POST /start`:** devuelve `true` también para un intento recién
   creado (la fórmula es verdadera para cualquier intento `in_progress`).
   Preexistente; no corregido.
7. **`mastered_modules: [1]`** figura en el resultado del intento 8/8 (regla
   heredada de "módulo dominado" con ≥ 75 %); no se comprobó cómo lo presenta
   la pantalla de resultado inmediata en ese caso.
8. **Diagnóstico Likert por API**, no por la interfaz, en ambos recorridos.
9. **Drift de Alembic preexistente.** `alembic check` reporta que el ORM espera
   las tablas `research_sessions`, `retrieval_cache` y `retrieval_history` que
   la BD no tiene, más diferencias de nombres de índice; ninguna afecta a
   `knowledge_test_*` ni a `experiment_results`. No se tocó ni se comprobó si
   ya era conocido.
10. **`DESIGN-banco-diagnostico-m1.md`** conserva en su cabecera el estado
    "Propuesta … sin implementar", que ya no es exacto. No se modificó por
    instrucción; queda pendiente de actualizar.
11. **Latencias:** los recorridos no se diseñaron como benchmark; no se
    registran tiempos como métrica.
12. **Rama sin publicar:** 50 commits locales por delante de `origin/main`; C1 y
    el resto de la fase no están en ningún remoto.

## 15. Datos de prueba y estado del entorno

| Estudiante | `user_id` | Intento | Ruta |
|---|---|---|---|
| `e2e-v4-f3e04c@upao.test` | `aeee8bb5-c649-4c12-ad8b-0c5c7a516692` | `8a64897c-1e1c-4d94-bdab-eced676bad64` | `3e7ea35d-5ded-4317-bfcc-ee0d7bacb843` |
| `e2e-v4-reforzar-5f2df4@upao.test` | `c2a4b3dd-2bca-4302-8538-86a06df9c76b` | `b4911738-4864-452d-aba1-11985eea3bf5` | `dbff2187-6193-47e7-86c3-f03d41b62789` |

Ambos son **datos de prueba en la BD real** y siguen presentes (no se
eliminaron). Sus filas: usuario, matrícula, perfil, diagnóstico, intento con 8
respuestas, ruta con 8 módulos, 13 claves de idempotencia, 3 métricas de
investigación, 4 registros de auditoría, un evento de outbox, un registro de
memoria compartida y un intento de login. Deben tratarse como excluidos de
cualquier análisis de investigación sobre estudiantes reales.

Al cerrar la fase, el backend (`127.0.0.1:8000`) y el contenedor
`upao_postgres` seguían en ejecución.

## 16. Cómo repetir las comprobaciones

- Conteos por versión: `select version, count(*) from knowledge_test_questions group by 1;`
- Intentos por versión: `select bank_version, kind, status, count(*) from knowledge_test_attempts group by 1,2,3;`
- Ningún intento en curso: `select count(*) from knowledge_test_attempts where status = 'in_progress';`
- Veredicto del Runtime de un estudiante: `avance_por_objetivo(student_id,
  course_id, objetivos)` en `app/services/runtime_bridge.py` (solo lectura).
- Los hashes de §8 con las fórmulas indicadas.
