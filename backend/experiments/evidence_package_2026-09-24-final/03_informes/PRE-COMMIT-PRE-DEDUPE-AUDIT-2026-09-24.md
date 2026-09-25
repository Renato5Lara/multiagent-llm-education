# Fase 3B — Auditoría pre-commit y pre-dedupe (2026-09-24)

Alcance: SOLO ANÁLISIS. Rama `feat/pretest-m1-v4` @ `d31d29c`. Único archivo creado: este informe (fuera del repo, en `Auditoria Tesis/`).
Comandos ejecutados: solo lectura (`git status/diff/ls-files`, `alembic heads/history/current`, `sha256sum`, `SELECT` sobre Postgres, `sus_cli status`,
`build_evidence_package --verify`, `dedupe_library` en **simulación**, scripts de análisis en el scratchpad de la sesión). Autoridad: Asesoría → DECISION-CLOSURE → MASTER-SPEC → informes de Fases 1–3.

## Resumen ejecutivo (leer primero)

1. **El plan de commits `GIT-COMMIT-PLAN-2026-09-24.md` NO es ejecutable tal como está.** Hay 6 defectos (§3.2): el commit 1 (stack CMG) no es autocontenido — `cmg_multiagent_configuration_service.py` exige `POLITICAS["v3-experimento-rama-a"]`, que solo existe en el `politica.py` modificado sin versionar; el PoC (AG2) y la imagen `upao-python-repl-sandbox` dependen de los cambios sin versionar de `app/sandbox/runner.py` y `runner_payload.py`; `_tts_cache/` **no** está en `.gitignore`; y varios tests/scripts CMG quedan sin su dependencia.
2. **El dedupe es técnicamente seguro pero no es lo que resuelve el problema de Git.** Git ya deduplica por contenido: las 10 versiones ocupan ≈ 406 MB únicos (v5+v9+v10 ≈ 305 MB), no 1.2 GB. Los hardlinks solo reducen disco local (1198 → ≈ 430 MB), no el repositorio. Ya existen hardlinks reales entre v5→v10 (2008 archivos).
3. **Hallazgos sobre mis propios entregables de la Fase 3 (a corregir antes de darlos por cerrados):** (a) el paquete de evidencia toma como «latest» `lib-v9`, no `lib-v10`, por un orden lexicográfico erróneo → el manifiesto de `lib-v10` **no está** en el paquete; (b) el `README_EVIDENCE_INDEX.md` afirma «lib-v9/v10: 0/0/0» en la auditoría semántica, pero solo existe la auditoría de v9 (la de v10 nunca se generó); (c) `environment.json` guarda `alembic_head: "FAILED…"`; (d) `sus_cli import-*` valida todo antes de insertar pero la **inserción no es transaccional** (mi informe de Fase 3 decía «todo o nada»: es una sobreafirmación).
4. **Resultados científicos confirmados sin cambios** (§10): F1_adapt = 0.8031 en ambas corridas; RNF03 NO cumplido; RNF01/RNF04 cumplidos solo con 4 workers; RNF05 pendiente; 0 participantes/valoraciones en BD.
5. **Ninguna acción destructiva ni commit** (§14).

---

## 1. Estado Git

| Concepto | Valor |
|---|---|
| Commits nuevos | 0 (`d31d29c` sigue siendo HEAD); `.git/index` con mtime `2026-09-23 15:27` (sin `add`); 0 stashes |
| Entradas en `git status --short` | 101 (16 modificados tracked + 85 sin seguimiento a nivel de directorio) |
| Archivos individuales sin seguimiento (`ls-files --others --exclude-standard`) | 8 531 (de ellos ≈ 8 400 son `datasets/adaptation_library/`) |
| `git diff --stat` | 16 archivos, +454 / −31 |
| `__pycache__`, `.venv`, `node_modules` | ignorados por `.gitignore` (verificado con `check-ignore`) |
| Secretos (`sk-…`, `tvly-…`, `AKIA…`, claves privadas) en archivos sin seguimiento (incluida la biblioteca de texto) | 0 coincidencias |
| `.git` | 14 MB; remoto `origin` = GitHub `Renato5Lara/multiagent-llm-education`; **`git-lfs` no instalado** |

### 1.1 Clasificación completa (agrupada por ruta)

`M` = modificado tracked; `??` = sin seguimiento. «Versionar» = recomendación técnica (no decisión).

| Ruta | Estado | Clase | Responsabilidad | ¿Versionar? | Motivo |
|---|---|---|---|---|---|
| `.claude/settings.local.json` | M | E temporal | config local de la herramienta | **No** | cambia sola; local |
| `.codegraph/daemon.pid` | M | E temporal | pid de daemon | **No** | temporal |
| `CLAUDE.md` | M | B previo | instrucciones del proyecto (usuario) | Decisión del usuario | 5 líneas cambiadas, ajenas al PoC; commit propio `docs` |
| `backend/runtime/domain/{adaptar,diagnosticar,orientar,remediar}/productor.py`, `backend/runtime/kernel/deliberation/politica.py` | M (5) | B previo | Kernel: campos experimentales R16–R19 + política `v3-experimento-rama-a` | **Sí, ANTES del CMG** | el CMG los necesita (§3.2-1) |
| `backend/app/sandbox/runner.py`, `backend/app/sandbox/docker/runner_payload.py` | M (2) | B previo | sandbox Podman+SELinux (`--userns=keep-id`, `,z`) y arreglo de `setattr` | **Sí, ANTES del PoC** | AG2 y la imagen del sandbox los necesitan (§3.2-2) |
| `backend/app/api/routes/auth.py` | M | B previo | instrumentación E1 (login) | Con el commit E1 (junto a `main.py` E1 y `scripts/instrumentacion_e1.py`) | independiente del PoC |
| `backend/app/main.py` | M | A+B mixto | 3 hunks E1 + 1 hunk PoC | Parcial (`git add -p`) | §3.3 |
| `backend/app/models/__init__.py` | M | A+B mixto | 1 línea CMG + 2 líneas PoC contiguas | Parcial (`git add -p` + `e`) | §3.3 |
| `backend/alembic/env.py` | M | A | 2 imports PoC | Sí (commit swarm-DB) | solo PoC |
| `backend/requirements.txt`, `docker-compose.yml` | M | A | redis/numpy/mutagen/scipy; servicio redis | Sí (commit swarm) | diff **solo** PoC (verificado) |
| `backend/adaptation_swarm/` (≈ 95 archivos, incl. `human_eval/`, `EVIDENCE_INDEX.md`, `tools/{dedupe_library,build_evidence_package}.py`) | ?? | A | código del PoC | Sí | — |
| `backend/tests/adaptation_swarm/` (22 archivos) | ?? | A | 201 pruebas | Sí | — |
| `backend/alembic/versions/{a17c0de5a001,b2f4c9d10a02}_*.py` | ?? | A | migraciones PoC | Sí | — |
| `backend/alembic/versions/{f101101bc75d,928a10b002db}_*.py` | ?? | B CMG | migraciones CMG previas (ancestros) | Sí (antes) | §4 |
| `backend/app/models/{swarm_adaptation,swarm_human_evaluation}.py` | ?? | A | modelos PoC | Sí | — |
| `backend/app/models/experiment_cmg_result.py`; `backend/app/services/cmg_*.py` (5) | ?? | B CMG | stack CMG | Sí (tras Kernel/sandbox) | §3.2-1 |
| `backend/tests/test_cmg_*.py` (6), `test_experimento_cmg_runner.py`, `test_r19/r23/r24/r26*.py`, `test_sandbox_runner_payload_setattr_fix.py` | ?? | B CMG/sandbox | tests CMG/sandbox | Sí, cada uno con su dependencia | §3.2-3/4 |
| `backend/experiments/d1_{adversarial_pilot,graduado_piloto}.py` | ?? | B CMG | pilotos D1 | Sí | — |
| `backend/experiments/results/{corrida2_*,d1_*,experiment_cmg_*,r32_*}` (≈ 14) | ?? | D histórico CMG | resultados CMG previos | Sí, en commit del CMG (NO tocar) | `test_r26` lee `experiment_cmg_dataset_v1.csv` |
| `backend/experiments/results/adaptation_swarm_*` (8) | ?? | D evidencia PoC | corridas + auditorías (congeladas) | Sí | inmutables |
| `backend/experiments/results/library_semantic_audit_lib-v{5..9}*.json` (5) | ?? | D evidencia PoC | auditoría semántica | Sí | falta la de v10 |
| `backend/experiments/evidence_package_2026-09-23/` (128) | ?? | D evidencia PoC | paquete con `MANIFEST.sha256` | Sí (tras decisión E) | **nuevo desde la clasificación previa** |
| `backend/loadtest/` (incl. 85 archivos en `results/`, 2.0 MB), `backend/requirements-loadtest.txt` | ?? | A + D | Locust/JMeter y resultados | Sí | — |
| `backend/tools/cpp_sandbox/`, `backend/tools/mermaid_render/{package.json,package-lock.json,render.mjs}` | ?? | A | sandbox C++, render Mermaid | Sí | `node_modules` (374 MB) ignorado |
| `backend/scripts/repro_db_bootstrap.sh` | ?? | A | bootstrap de BD | Sí | — |
| `backend/scripts/{experimento_*,oe*_fixtures,lanzar_servidor_*,gateA_analisis,instrumentacion_e1,benchmark_capacidad_http,analizar_saturacion_oe3,diagnostico_punto4_*}.py`, `benchmark_results/`, `oe2_results/`, `oe4_results/` (≈ 287 archivos) | ?? | B histórico | experimentos OE/E1 previos | Decisión del usuario; commits propios | **no** son del PoC. `experimento_cmg_runner.py` sí lo necesita el test CMG |
| `datasets/synthetic_profiles/` (96 KB) | ?? | A | dataset sintético + gold | Sí | congelado |
| `datasets/adaptation_library/` (1198 MB físicos; 2 610 MB lógicos) | ?? | C generado | biblioteca versionada por hash | **Decisión C** | §5 |
| `docs/architecture/ADR/ADR-0019-poc-…md` | ?? | A | ADR del PoC | Sí | — |
| `docs/architecture/ADR/.impeccable/` | ?? | F residuo | otra herramienta | **No** | ajeno |

## 2. Diferencias frente a `GIT-CLASSIFICATION-2026-09-23-fase2.md`

| Diferencia | Detalle |
|---|---|
| Entradas de status | 100 → 101: aparece `backend/experiments/evidence_package_2026-09-23/` |
| Dentro de directorios ya listados | `adaptation_swarm/` + `human_eval/` (6), `EVIDENCE_INDEX.md`, `tools/dedupe_library.py`, `tools/build_evidence_package.py`; `tests/adaptation_swarm/` +`test_evidence_and_tools.py` (+ 2 pruebas en `test_sus_panel.py`); `datasets/adaptation_library/` +`lib-v10-5dd83cd4` (1081 archivos) |
| Sin cambios | los 16 `M`, las 4 migraciones, el stack CMG, `.impeccable/`, resultados históricos |
| La clasificación previa (y el plan) **no detectó** | las dependencias cruzadas de §3.2 (Kernel ↔ CMG, sandbox ↔ PoC/tests, scripts/resultados ↔ tests CMG) |
| Corrección a la clasificación previa | `requirements.txt` y `docker-compose.yml` fueron marcados «pueden traer cambios ajenos»: el diff es **100 % PoC** |

## 3. Auditoría del plan de commits (`GIT-COMMIT-PLAN-2026-09-24.md`)

### 3.1 Verificación por criterio (los 11 puntos pedidos)

| # | Criterio | Resultado |
|---|---|---|
| 1 | Responsabilidad única por commit | Parcial: commit 4 mezcla PoC + `requirements.txt` + `docker-compose.yml` + `tools/` (aceptable como «infra del PoC», pero el commit 1 mezcla CMG + migraciones + tests) |
| 2 | Reproducible | **No** (§3.2): el commit 1 falla al importar el servicio CMG sin el Kernel; el 2 falla el test de `setattr` sin el payload |
| 3 | No mezcla CMG con PoC | Correcto salvo `models/__init__.py` (línea CMG + líneas PoC contiguas: exige `git add -p` con edición `e`) |
| 4 | Sin documentos de tesis | Correcto: el paquete copia informes de `Auditoria Tesis/` (no la tesis) — pero ver criterio 5 |
| 5 | Sin resultados que deban ser externos | **Conflicto de política**: `03_informes/` del paquete copia dentro del repo informes de auditoría que la regla del usuario manda guardar fuera del repo (`Auditoria Tesis/`). Decidir en E |
| 6 | Sin temporales | Correcto (`.claude/`, `.codegraph/`, `.impeccable/` excluidos) |
| 7 | Sin cachés | **Incumplido**: `datasets/adaptation_library/_tts_cache/` (383 MB, 393 archivos) **no está en `.gitignore`**; `git add datasets/` lo incorporaría. 368 MB son idénticos a mp3 de las versiones y 14.7 MB (15 archivos) no los usa ninguna versión |
| 8 | Sin secretos | Correcto (0 coincidencias) |
| 9 | Sin `.venv` | Correcto (ignorado) |
| 10 | Sin `_tts_cache` | Ver 7: el plan solo lo menciona como opción |
| 11 | Sin artefactos generados innecesarios | Pendiente de la decisión C (biblioteca) |

### 3.2 Defectos del plan (verificados con comandos)

1. **Commit 1 (CMG) no es autocontenido.** `app/services/cmg_multiagent_configuration_service.py:119` hace `POLITICAS[_POLITICA_EXPERIMENTAL_ID]` con `"v3-experimento-rama-a"`, definida solo en el `politica.py` modificado (+93 líneas, campos R16–R19) y en los 4 `productor.py` modificados. Además importa `runtime.domain.*` y `runtime.kernel.*`. `tests/test_r19_aislamiento_experimental_rama_a.py` también. → Debe existir un commit previo «Kernel: campos experimentales R16–R19» (los 5 archivos `M` de `runtime/`).
2. **El PoC depende del sandbox modificado sin versionar.** `adaptation_swarm/agents/ag2_code_agent.py:24` usa `app.sandbox.runner.SandboxRunner`; en `HEAD` el runner usa `--user 65534:65534` y monta sin `,z`, lo que el propio comentario del cambio documenta como fallo bajo Podman + SELinux Enforcing. La imagen `upao-python-repl-sandbox` (`app/sandbox/docker/Dockerfile: COPY runner_payload.py`) se construye con el payload que contiene el arreglo del bug de `setattr`. `REPRODUCIBILITY.md §1` manda `podman build … app/sandbox/docker`. → El plan **excluye** `app/sandbox/*`; sin él, la reproducción desde un clon limpio fallaría en Podman/SELinux. Debe versionarse (commit propio) antes del PoC. *(Análisis estático; no se ejecutó un clon limpio en esta fase.)*
3. **`test_sandbox_runner_payload_setattr_fix.py`** lee `app/sandbox/docker/runner_payload.py` como texto: en el commit 2 del plan (sin el payload) su verificación no corresponde al código commiteado.
4. **`tests/test_experimento_cmg_runner.py`** importa `scripts.experimento_cmg_runner` (sin seguimiento, clasificado «no del PoC»); **`test_r26…`** lee `experiments/results/experiment_cmg_dataset_v1.csv` (sin seguimiento). Ninguno está en un commit del plan.
5. **`_tts_cache/`** sin regla de ignore (§3.1-7).
6. **Resultados de `experiments/results/`**: el commit 7 solo nombra `adaptation_swarm_*`; los `library_semantic_audit_*` (5) y los históricos CMG (≈ 14) no están asignados a ningún commit.
7. Menor: los `git add -p` de `main.py` y `models/__init__.py` se describen sin mapear hunks (ver §3.3) y el paso de `requirements.txt`/`docker-compose.yml` ya no requiere revisión de cambios ajenos.

**Orden corregido sugerido (no ejecutar):** (0) `.gitignore`: `datasets/adaptation_library/_tts_cache/` (y decisión C) → (1) Kernel R16–R19 → (2) sandbox Podman/SELinux + arreglo `setattr` (+ su test) → (3) stack CMG + migraciones `f101101bc75d`,`928a10b002db` + tests CMG + `scripts/experimento_cmg_runner.py` + resultados CMG históricos + pilotos D1 (+ hunk de `models/__init__.py` de `ExperimentCMGResult`) → (4) tablas swarm/SUS (`a17c0de5a001`,`b2f4c9d10a02` + modelos + hunk PoC de `models/__init__.py` + `env.py`) → (5) `adaptation_swarm/` + `tools/` + `requirements` + `docker-compose` + `repro_db_bootstrap.sh` → (6) endpoint (hunk 4 de `main.py`) → (7) tests del PoC → (8) dataset sintético + resultados congelados + auditorías semánticas → (9) ADR-0019 → (10) loadtest → (11) paquete de evidencia → (E1, aparte) `auth.py` + hunks 1–3 de `main.py` + `scripts/instrumentacion_e1.py`, y `CLAUDE.md`.

### 3.3 Mapa de hunks de los archivos mixtos (solo lectura; sin `git add -p`)

| Archivo | Hunk (nuevo) | Pertenece a | Detalle |
|---|---|---|---|
| `backend/app/main.py` | `@@ -224,0 +225,3` | **E1 (previo)** | `_E1_ENABLED = os.getenv("E1_INSTRUMENTATION") == "1"` |
| | `@@ -229 +232,29` | **E1 (previo)** | `add_request_id`: `ContextVar` `request_id_var` desde `scripts.instrumentacion_e1` (import perezoso bajo flag; sin el script, inerte) |
| | `@@ -236,0 +268,7` | **E1 (previo)** | `request.state.t_arrival = time.perf_counter()` |
| | `@@ -352,0 +391,5` | **PoC** | `from adaptation_swarm.api.router import router as adaptation_swarm_router` + `app.include_router(adaptation_swarm_router)` |
| `backend/app/models/__init__.py` | `@@ -36,0 +37,5` | **mixto contiguo** | línea 1 `ExperimentCMGResult` = **CMG**; líneas 2–5 (`GoldPanelRating, SusParticipant, SusResponse`; bloque `swarm_adaptation`) = **PoC** → `git add -p` + `e` |
| | `@@ -70,0 +76,3` | **mixto contiguo** | `"ExperimentCMGResult"` = **CMG**; las otras 2 líneas de `__all__` = **PoC** |
| `backend/alembic/env.py` | `@@ -37,2 +37,4` | **PoC** | 2 imports (`swarm_adaptation`, `swarm_human_evaluation`); **no** importa el modelo CMG |
| `backend/requirements.txt` | `@@ -72 +72,5` | **PoC** | redis 8.1.0, numpy 2.5.3, mutagen 1.47.0, scipy 1.18.1 |
| `docker-compose.yml` | `@@ -20,2 +20,14` | **PoC** | servicio `redis` |

## 4. Auditoría de migraciones

`alembic heads` → **1 cabeza**: `b2f4c9d10a02`. La BD (`alembic current`) está en `b2f4c9d10a02`. Cadena verificada con `alembic history`:

`… → c5d6e7f8a9b0 (create_concepts_table) → d6e7f8a9b0c1 (migrate_is301_to_8_modules, **preexistente, tracked**) → e7f8a9b0c1d2 (widen_path_module_description, tracked) → f101101bc75d → 928a10b002db → a17c0de5a001 → b2f4c9d10a02`

| Revisión | `down_revision` | Pertenece a | Seguimiento | Notas |
|---|---|---|---|---|
| `f101101bc75d` add_experiment_cmg_results | `e7f8a9b0c1d2` | **CMG** | sin versionar | fecha 2026-09-22; crea `experiment_cmg_results` (FK a `concepts`) |
| `928a10b002db` add_run_label_to_experiment_cmg_results | `f101101bc75d` | **CMG** | sin versionar | ancestro directo de la primera migración del PoC |
| `a17c0de5a001` add_adaptation_swarm_tables | `928a10b002db` | **PoC** | sin versionar | `swarm_runs/profiles/cycles/iterations`, `agent_messages`, `multimodal_candidates/packages` |
| `b2f4c9d10a02` add_swarm_diagnostics_and_human_evaluation | `a17c0de5a001` | **PoC** | sin versionar | `pso_diagnostics`, `sus_participants/responses`, `gold_panel_ratings` |

- Archivos en `alembic/versions/`: 29 tracked + 4 sin seguimiento; 0 ramas alternativas (una sola cabeza también con las 4).
- **El orden del plan (CMG antes que PoC) es técnicamente correcto**: `a17c0de5a001` depende de `928a10b002db`. Sin ellas la cadena queda rota (`Can't locate revision`).
- Los modelos `ExperimentCMGResult` (`app/models/experiment_cmg_result.py`) deben viajar en el mismo commit que `f101101bc75d` (la migración crea la tabla que el modelo define).
- `env.py` solo importa los modelos swarm/SUS; no importa el CMG (no es un defecto: `autogenerate` lo ve vía `app.models`).
- Ninguna migración fue modificada, degradada, eliminada ni generada.

## 5. Auditoría de la biblioteca (`datasets/adaptation_library/`)

### 5.1 Inventario (tamaños, linaje, uso)

Tamaño físico total (inodos únicos): **1 198 MB**; lógico (suma de tamaños de archivo): **2 610 MB**. Caché TTS: 393 mp3 = **383 MB** (0 con `nlink>1`: ningún mp3 de la caché comparte inodo con una versión todavía).

| Versión | Base | Entradas (manifiesto) | Δ vs base (añadidos/cambiados) | Lógico MB | Archivos con `nlink>1` | Usada por |
|---|---|---|---|---|---|---|
| lib-v1-3f931e10 | — | 24 (3 conceptos) | — | 8.1 | 0 | historial (arranque) |
| lib-v2-767b4a53 | v1 | 336 | +312 / 0 | 116.7 | 0 | **rama lateral**: no es ancestro de ninguna versión posterior (constructor duplicado) |
| lib-v3-5fa0acdd | v1 | 384 | +48 / 176 | 136.0 | 0 | historial (ancestro de v4) |
| lib-v4-039dcf58 | v3 | 672 | +288 / 0 | 239.2 | 0 | historial |
| **lib-v5-9ae9ffdd** | v4 | 720 (30 conceptos; py/mmd/txt/mp3) | +48 / 0 | 258.9 | 420 | **`corrida-poc-1`**, `test_corrida_poc_1_preserved`, auditoría F1/PSO poc-1, paquete |
| lib-v6-86516a15 | v5 | 1 029 | +309 / 133 (SVG, C++ 66/90, código corregido) | 290.2 | 1 029 | historial (auditoría semántica) |
| lib-v7-7c046f32 | v6 | 1 047 | +18 / 12 (C++ 75) | 292.0 | 1 041 | historial (auditoría semántica) |
| lib-v8-079928dc | v7 | 1 071 | +24 / 32 (C++ 81, SVG 270) | 295.0 | 1 071 | historial (auditoría semántica) |
| **lib-v9-a0231e9b** | v8 | 1 077 (C++ 87) | +6 / 0 | 295.0 | 1 077 | **`corrida-poc-2`**, auditoría F1 poc-2, paquete |
| **lib-v10-5dd83cd4** | v9 | 1 080 (C++ **90/90**) | +3 / 0 | 295.0 | 1 077 | **última**; ninguna corrida; **no está en el paquete de evidencia** (§7) |

Linaje real: `v1 → v3 → v4 → v5 → v6 → v7 → v8 → v9 → v10`; `v2` cuelga de `v1` y no tiene descendientes. Todas fueron creadas el 2026-09-24 (UTC), es decir la tarde-noche del 2026-09-23 local.
Lo que cambió entre versiones queda en `manifest.json` (`changes` con `reasons`, sha256 nuevo por artefacto).

### 5.2 Respuestas a las 10 preguntas

1. **Evidencia experimental:** `lib-v5-9ae9ffdd` (poc-1) y `lib-v9-a0231e9b` (poc-2). Ambas referenciadas en `run.config.library_version` (JSON y Postgres) y en pruebas.
2. **Necesarias para reproducibilidad:** v5 y v9 (para reproducir poc-1/poc-2 bit a bit) y v10 (última, la que `LibraryStore.open` abre por defecto y con la que corre la suite). Cada versión es **autocontenida** a nivel de archivos (los hardlinks son copias con el mismo inodo; borrar otra versión no rompe la lectura de una). El campo `base_version` es solo linaje; no se probó borrando.
3. **Solo historial de desarrollo:** v1, v2, v3, v4 (pre-v5) y v6, v7, v8 (etapas intermedias entre las corridas; sus auditorías semánticas v6–v8 existen como evidencia de la mejora).
4. **Podrían archivarse eventualmente:** v2 (rama lateral sin descendientes), v1, v3, v4; v6–v8 son historial documentado. **No se recomienda decidirlo ahora** (§ 13-D).
5. **NO deben eliminarse:** v5, v9, v10 (más el manifiesto de cada versión, que contiene el sha256 de toda su lista).
6. **¿Hardlinks seguros?** Sí para contenido inmutable y lectura. Riesgos reales: (a) ninguna versión está protegida contra escritura (`chmod`), así que editar «in place» un archivo modificaría todas las versiones enlazadas; (b) el TTS solo escribe la caché al fallar el acierto (`ag4_text_agent.py:149–165`: si `{key}.mp3` existe lo lee), por lo que hoy no reescribe en el lugar; (c) copias con `cp -r`, `rsync` sin `-H`, `tar` sin preservar enlaces o discos/servicios sin soporte **rompen los enlaces y devuelven el tamaño a 2.6 GB**.
7. **Si luego se modifica una versión:** `LibraryWriter` rompe el enlace antes de escribir (`library.py:251` `path.unlink()`; `os.link` solo al extender), así que el flujo soportado (`extend`) nunca altera una versión sellada ni sus vecinas. Una edición manual «in place» sí propagaría; se detecta con `multimodal.verify <versión>` (sha256 de todos los artefactos) y con `MANIFEST.sha256` del paquete (solo para las dos versiones).
8. **Trazabilidad:** `library_version = lib-vN-<hash del manifiesto>`; el manifiesto contiene `sha256` por entrada y `derived_from` (cadenas código→diagrama→SVG, código→C++, texto→audio) que `LibraryStore` verifica en cada lectura. Los hardlinks no cambian bytes ni hashes.
9. **Versión usada por cada corrida:** poc-1 → `lib-v5-9ae9ffdd`; poc-2 → `lib-v9-a0231e9b` (`config.library_version` en JSON y `swarm_runs.library_version` en Postgres, verificado por `SELECT`).
10. **Versión asociada al paquete de evidencia:** manifiestos de v5 y v9 (idénticos a los actuales, `cmp`); **v10 ausente** por defecto del constructor (§7).

Nota: `git.commit=d31d29c` y `dirty=true` quedaron registrados en el `config` de ambas corridas. Tras cualquier commit, ese hash ya no describe el árbol que las produjo; la trazabilidad exacta depende de `config_hash`, `library_version`, dataset y el paquete con hashes, no del commit.

### 5.3 Tamaño Git-relevante (contenido único por sha256 — lo que Git almacenaría)

| Subconjunto | Blobs únicos | ≈ MB |
|---|---|---|
| Solo v10 | 1 028 | 294 |
| **v5 + v9 + v10** | 1 184 | **305** |
| Cadena v1,v3…v10 (sin v2) | 1 199 | 307 |
| **Todas v1…v10** | 1 366 | **406** |
| + `_tts_cache/` completa | +15 blobs propios (14.7 MB) | ≈ 421 (368 MB de la caché repiten mp3 de versiones) |

Conclusión: Git ya elimina la duplicación; el problema de Git no es el hardlink sino que ≈ 400 MB de mp3 (incomprimibles) entrarían a un remoto GitHub **sin `git-lfs` instalado**.

## 6. Simulación de deduplicación (`dedupe_library`, SIN `--apply`)

Salida real: `archivos 7834 · contenidos únicos 1382 · enlaces a crear 3501 · ahorro 768 MB` — «SIMULACIÓN: no se modificó nada». El plan excluye `manifest.json` y archivos ocultos. La tabla completa por archivo (3 501 filas: archivo, tamaño, sha256, versión, duplicado de, acción) se generó en el scratchpad de la sesión (`dedupe_table.tsv`, no en el repo); se reproduce con `python -m adaptation_swarm.tools.dedupe_library` y el script de análisis. Resumen agregado y muestra:

| Origen conservado → destino | Archivos a enlazar | Naturaleza |
|---|---|---|
| `_tts_cache` → mp3 de v1…v10 | **2 151** | ≈ 2 045 MB lógicos → 1 copia física (coincide con el ahorro) |
| `lib-v10` → `.mmd/.py/.txt` de v2…v9 | 946 | metadatos textuales (≈ 0.5 MB en total) |
| `lib-v1…v4` → `.mmd/.py/.txt` de versiones posteriores | 404 | ídem |
| **Total** | **3 501** | **≈ 768 MB de disco físico** (1198 → ≈ 430 MB) |

Por versión destino: v1 9 · v2 234 · v3 343 · v4 610 · v5 595 · v6 364 · v7 353 · v8 331 · v9 331 · v10 331. Hashes de contenido compartido entre ≥ 2 rutas: 783. Destinos que ya tenían `nlink>1`: 2 008 (los hardlinks v5→v10 de la extensión).

Muestra (6 de 3 501):

| archivo | tamaño | sha256 (16) | versión | duplicado de | acción simulada |
|---|---|---|---|---|---|
| `lib-v1-3f931e10/artifacts/80655903-…/audio_t0a0.mp3` | 364 416 | df5806540294104e | lib-v1 | `_tts_cache/7839804a…417abb1c.mp3` | hardlink→_tts_cache |
| `lib-v1-3f931e10/artifacts/80655903-…/audio_t0a1.mp3` | 419 328 | 1e13ba1690a37990 | lib-v1 | `_tts_cache/3739c1d0…df5b.mp3` | hardlink→_tts_cache |
| `lib-v4-039dcf58/artifacts/ec088842-…/audio_t1a2.mp3` | 968 832 | 0c6dc25b28fadfce | lib-v4 | `_tts_cache/aea197c8…7004b.mp3` | hardlink→_tts_cache |
| `lib-v4-039dcf58/artifacts/ec088842-…/audio_t2a0.mp3` | 1 405 824 | 147db2d1785907a1 | lib-v4 | `_tts_cache/f86bb7eb…90ad.mp3` | hardlink→_tts_cache |
| `lib-v9-a0231e9b/artifacts/a20e470f-…/diagram_c0d1.mmd` | 131 | 2a9e1db5f0e7bd12 | lib-v9 | `lib-v10…/diagram_c0d0.mmd` | hardlink→lib-v10 |
| `lib-v9-a0231e9b/artifacts/a20e470f-…/diagram_c1d1.mmd` | 181 | ea56e268414127a8 | lib-v9 | `lib-v10…/diagram_c1d0.mmd` | hardlink→lib-v10 |

Observaciones sobre la herramienta y el riesgo:
- **Mismo contenido lógico:** el `apply` hace `os.link` a un temporal, verifica el sha256 antes/después y `os.replace` (atómico por archivo). Los bytes de cada ruta no cambian; los manifiestos no se tocan (excluidos).
- **Enlaza también variantes distintas con contenido idéntico** dentro de una misma versión (p. ej. `diagram_c0d1.mmd` y `diagram_c0d0.mmd`); es correcto (sus entradas de manifiesto conservan el mismo sha256), pero acopla inodos entre variantes.
- **Cambia la topología física de la caché**: 2 151 mp3 de versiones quedarán como el mismo inodo que la caché; los 15 mp3 huérfanos (14.7 MB) quedan sin enlazar.
- **Reversibilidad:** lógica total (romper enlaces con copia+`mv` por archivo devuelve 2.6 GB; los hashes no cambian). No hay «deshacer» automático; conviene un listado sha256 previo.
- **Impacto sobre Git:** ninguno (Git almacena contenido; ignora hardlinks). **Sobre evidencia:** ninguno (bytes idénticos; se puede probar con `sha256sum` previo/posterior y `multimodal.verify`). **Sobre reproducibilidad:** ninguno lógico; riesgo operativo solo al copiar la biblioteca sin conservar enlaces.
- Límite de la herramienta: el «mantenido» se elige por orden alfabético de ruta (irrelevante con hardlinks: todos comparten inodo).

## 7. Auditoría del paquete de evidencia (`backend/experiments/evidence_package_2026-09-23/`)

- **Integridad:** 127 archivos + `MANIFEST.sha256` (127 entradas). `LC_ALL=C sha256sum -c` → **127 OK, 0 fallos**; `build_evidence_package --verify` → «VERIFICADO: todos los hashes coinciden». (Nota: con locale español `sha256sum -c` no imprime «OK», sino «La suma coincide»; usar `LC_ALL=C` al automatizar.)
- **Relación con las corridas:** los 8 archivos `adaptation_swarm_*` del paquete son **byte a byte iguales** a los de `experiments/results/`; también `manifest` de v5 y v9 y los 5 archivos de `synthetic_profiles/`. Incluye además exportaciones de Postgres de poc-1 y poc-2 (`db_*_run.json`, `db_*_cycles.csv`), auditorías F1, PSO poc-1, semánticas v5–v9, carga (Locust ×2 configs + JMeter ×2), documentación y entorno.
- **Cobertura temática:** F1 ✔, PSO ✔ (auditoría poc-1; poc-2 vía `pso_diagnostics` en su JSON), carga ✔, configuración ✔ (dentro de cada corrida), biblioteca ✔ parcial, reproducibilidad ✔ (REPRODUCIBILITY.md, `pip_freeze`, `requirements`).

**Defectos encontrados en el paquete:**
1. **Manifiesto «latest» erróneo:** `tools/build_evidence_package.py:63` usa `sorted(p.name …)[-1]`; en orden lexicográfico `lib-v9-…` > `lib-v10-…`, por lo que el paquete contiene v5 y v9 (repetida) y **no** v10. El paquete no contiene el manifiesto de la biblioteca más reciente (C++ 90/90).
2. **Afirmación sin respaldo:** `README_EVIDENCE_INDEX.md` dice «lib-v9/v10: 0/0/0» en la validación semántica; solo existe `library_semantic_audit_lib-v9…json` (`extend.py:250` audita la **base**, no la versión creada). La validación semántica de v10 nunca se generó como archivo. (Diferencia real v10−v9: 3 entradas C++ de un concepto.)
3. **`06_entorno/environment.json`:** `"alembic_head": "FAILED: No 'script_location' key found in configuration."` (se ejecutó `alembic` desde un directorio sin `alembic.ini`).
4. **Política:** `03_informes/` copia informes de auditoría dentro del repo (regla del usuario: auditorías fuera del repo).
5. `06_entorno/git_status.txt` es una instantánea previa a Fase 3 (incluye `d31d29c` + estado antiguo).

**Quedaron FUERA del paquete** (posteriores o no incluidos): `adaptation_swarm/human_eval/` (instrumento SUS, guion v1, protocolo, consentimiento, `templates/*.csv`), `sus_cli import-*`, `GIT-COMMIT-PLAN-2026-09-24.md`, `IMPLEMENTATION-PHASE3-REPORT-2026-09-24.md`, este informe, manifiestos v6–v8/v10, `EVIDENCE_INDEX.md`/`dedupe_library` (código, sí están en el árbol pero no en el paquete).

**¿Conviene `evidence_package_2026-09-24/`? Sí, después de** corregir el orden natural en `build_evidence_package.py`, generar la auditoría semántica de v10 y decidir la política sobre informes. Contenido propuesto: lo de hoy (corridas y auditorías congeladas, sin duplicar carga) + manifiestos v5, v9, **v10** (y opcionalmente v6–v8) + `library_semantic_audit_lib-v10` + `human_eval/` (SUS ES, guion, protocolo, consentimiento, plantillas vacías) + informes Fase 3/3B + `GIT-COMMIT-PLAN` corregido + `environment.json` correcto + `dedupe` (salida de la simulación) + `MANIFEST.sha256`. No sobrescribir el paquete del 09-23.

## 8. Auditoría de reproducibilidad (estática)

`REPRODUCIBILITY.md` + `scripts/repro_db_bootstrap.sh` cotejados contra el código (`config.py`, `run_experiment.py`, Dockerfiles, `requirements*`).

| Componente | Estado | Observación |
|---|---|---|
| Dependencias Python | ✔ | `redis, numpy, mutagen, scipy` fijados; `langgraph, sqlalchemy, fastapi, httpx, pytest…` ya estaban; `locust, psutil` en `requirements-loadtest.txt`. `openai>=1.0.0` **sin fijar** (preexistente) |
| Python | ⚠ | doc: entorno 3.14; el `Dockerfile` del backend usa **3.12-slim** y el del sandbox **3.11-slim**; las versiones fijadas (numpy 2.5.3, scipy 1.18.1) no se comprobaron contra 3.12 |
| Comandos / flags | ✔ | `run_experiment` acepta `--run-label`, `--library-version`, `--sweep`, `--batch-seed`, `--limit`, `--dry-run`, `--no-persist`; existen `analysis.f1_audit`, `pso_audit`, `multimodal.verify`, `profiles.build_dataset`, `tools.bootstrap_preconditions` |
| Variables de entorno | ⚠ | documentadas: `SWARM_SANDBOX_BIN`, `MERMAID_CHROME`, `OPENAI_API_KEY`, `SWARM_API_KEY/RUN_LABEL`; usadas pero no documentadas: `SWARM_REDIS_URL`, `SWARM_LIBRARY_ROOT`, `SWARM_REDIS_PREFIX`, `SWARM_REDIS_MAX_CONNECTIONS`, `SWARM_STREAM_MAXLEN`, `SWARM_SEEN_TTL_SECONDS`, `SWARM_LOG_TTL_SECONDS`, `SWARM_REQUEST_TIMEOUT`, `SWARM_API_PERSIST` (aparece solo en §6) |
| Redis / PostgreSQL | ✔ | `docker-compose.yml` (redis:7-alpine, healthcheck); Postgres por compose |
| OpenAI | ✔ | solo para generar/extender la biblioteca; **pero** algunas pruebas la llaman (doc lo declara) |
| Mermaid / Node / Chrome | ✔ | `package-lock.json` presente (`npm ci`); Chrome del sistema (`MERMAID_CHROME`); Node ≥ 18 declarado, medido 22 |
| C++ / Podman | ✔ | `tools/cpp_sandbox/Dockerfile` (alpine + g++); `--network none` |
| Sandbox Python en Podman/SELinux | ✘ | depende de `runner.py`/`runner_payload.py` **sin versionar** (§3.2-2) |
| Alembic | ⚠ | el script usa `.venv/bin/alembic`, cuyo shebang en esta máquina apunta a otra copia (`<HOME>/Documentos/Proyecto/…/.venv/bin/python`), contradiciendo la propia nota «usar `python -m`». En un venv nuevo funciona; aquí la «verificación desde BD vacía» de la Fase 2 pudo ejecutar `alembic` con ese intérprete. Recomendado `python -m alembic` |
| Cadena Alembic | ⚠ | doc marca `f101101bc75d*`/`928a10b002db*` «sin versionar»: quedará obsoleto tras los commits |
| Dataset | ✔ | `datasets/synthetic_profiles/` (96 KB) con `manifest-v1.json` (sha256) |
| Biblioteca | ✘ (desde clon limpio) | no está en Git (§5); los tests `test_corrida_poc_1_preserved`, `test_library_full_coverage` y las corridas exigen `datasets/adaptation_library/` y filas de Postgres → **no son herméticos**; sin la biblioteca, un clon limpio no reproduce nada |
| Referencia 3.12 vs 3.14 | ⚠ | ver «Python» |
| Evidencia | ⚠ | los JSON de corrida dicen `dirty: true` sobre `d31d29c` |

## 9. Auditoría SUS / panel

Revisado: `human_eval/*`, `metrics/sus.py`, `persistence/human_eval.py`, `sus_cli.py`, `app/models/swarm_human_evaluation.py`.

| Aspecto | Resultado |
|---|---|
| Instrumento | 10 ítems Brooke en español, escala 1–5; marcado «versión a validar/citar» (DEC-16). Puntaje impares (r−1), pares (5−r), ×2.5 ✔ |
| Consentimiento | Plantilla `CONSENT_TEMPLATE.md` **sin revisar por asesor/comité**. BD: `CHECK consent = true`; importación rechaza sin consentimiento |
| Roles | `CHECK role in ('docente_programacion','ingeniero_software')`; el importador ahora valida el rol antes de insertar |
| Privacidad | seudónimo sin `@` ni espacios (validado); sin nombre/correo |
| Tablas | `sus_participants`, `sus_responses` (único por participante+instrumento; ítems 1–5), `gold_panel_ratings` (único por participante+`rule_version`+celda; rating 1–5 opcional) |
| Mínimo 10 | `study_status`: < 10 → «PENDIENTE DE RECOLECCIÓN HUMANA»; `analyze_sus` con n < 10 no calcula nada (probado). Con n ≥ 10: Shapiro → t de una muestra (H1: media > 75) o Wilcoxon; `exceeds_threshold` exige media > 75 **y** p < 0.05 (más estricto que «media > 75»; documentarlo) |
| Panel | κ de Fleiss por celda/global; «PENDIENTE» si n_min < 10 o n desigual; **no exige** que estén las 20 celdas (un panel de 10 evaluadores que valoren 5 celdas se reportaría `COMPLETO`) |
| Atomicidad de importación | **Defecto:** `import_sus_csv`/`import_gold_csv` **validan todas las filas antes de insertar** (probado: una fila mala → 0 inserciones), pero la inserción usa una sesión y un `commit` por participante/respuesta. Fallos en la inserción (seudónimo duplicado en el CSV o ya existente → `IntegrityError`; participante inexistente en `import-gold` → `NoResultFound`) dejan **importaciones parciales**. La docstring/informe de Fase 3 dicen «todo o nada»: solo cierto para validación |
| Datos ficticios | **Ninguno.** `SELECT count(*)`: `sus_participants` 0, `sus_responses` 0, `gold_panel_ratings` 0; `sus_cli status` = PENDIENTE. Las pruebas usan SQLite en memoria (nunca Postgres) |
| Plantillas | `gold_panel_template.csv` con las 20 celdas y la etiqueta esperada visible (`expected_dominant_shown`): es inherente a la pregunta «¿es razonable?», pero sesga; documentar |

**Pendiente para iniciar la recolección real:**
1. Fijar/citar la versión en español del SUS y aprobar el consentimiento (asesor/comité) — DEC-16.
2. Reclutar ≥ 10 docentes de programación / ingenieros; asignar seudónimos.
3. Decidir el artefacto que verán (el guion v1 usa `run_slice --json` + archivos de biblioteca; **no existe visor HTML dedicado** → decidir si se construye o se usa el guion tal cual).
4. Fijar la versión de biblioteca que se muestra (recomendable v10, sin corrida asociada; declararlo).
5. Corregir la importación para que sea transaccional (o aceptar la limitación) y decidir si el panel exige las 20 celdas.
6. Ejecutar sesión → `sus_cli import-sus/import-gold` → `sus_cli status` → informar solo con n ≥ 10.

## 10. Confirmación de resultados experimentales (desde artefactos)

| Resultado | Fuente | Valor | Estado |
|---|---|---|---|
| **F1_adapt** (macro, clases definidas) | `adaptation_swarm_corrida-poc-{1,2}.json` (`summary.f1`) | **0.8031415** ambos; IC95 [0.7114, 0.8766]; accuracy 0.81; macro-4 0.6024; misma matriz `[[42,5,3,0],[5,20,0,0],[4,2,19,0],[0,0,0,0]]` | confirmado |
| **RNF03** F1 ≥ 0.85 | idem | 0.8031 < 0.85 | **NO CUMPLIDO** |
| Completitud | idem | 100/100 completados, 0 fallidos; `stop_reason`: 100 `epsilon`; CR = 1.00 | confirmado |
| **RNF02** T_conv ≤ 15 | idem | `k_stop` máx **4** (poc-1) y **5** (poc-2); media 1.65 y 1.79; `T_conv` máx 60.8/65.8 ms | Cumplido, pero **tautológico** bajo `k_max = 15` (la parada literal por ε con 𝓕 constante a tramos siempre termina antes; CR = 1.00 está inflado por DEC-10) |
| **RNF01** P95 < 2 s (≤ 25 usuarios) | `04_carga/…w1/summary.md`, `…w4/summary.md`; JMeter | **1 worker:** P95@25 = **2 200 ms** (Locust), 2 316 ms (JMeter) → **NO cumplido**. **4 workers:** P95@25 = **1 100 ms** (Locust), 1 123 ms (JMeter) → **cumplido** | según workers |
| **RNF04** ≥ 20 req/s | idem | **1 worker:** 15.8 req/s @25 (16.0 JMeter) → **NO cumplido**. **4 workers:** 40.5 req/s (41.0 JMeter) → **cumplido** | según workers |
| Errores de carga | idem | 0 % en todos los escenarios | — |
| **RNF05** SUS > 75 (n ≥ 10) | BD | 0 respuestas | **PENDIENTE DE RECOLECCIÓN HUMANA** |
| Configuración de ambas corridas | JSON | N=20, w=0.729, c1=c2=1.494, ε=0.001, k_max=15, α/β/γ/δ = .40/.30/.15/.15, semilla 20260923, dataset `profiles-v1`; solo cambia `library_version` | sin cambios |
| BD | `SELECT` | `swarm_runs`: `corrida-poc-1` (lib-v5), `corrida-poc-2` (lib-v9); `swarm_cycles` 100 + 100; `agent_messages` 11 676; `multimodal_packages` 200; `alembic_version` = `b2f4c9d10a02` | intactas |

Salvedades a mantener al citar: la carga se generó en el mismo host que el SUT (8 CPU compartidos); con 4 workers a 1 usuario la latencia es mayor que con 1 worker (100 vs 62 ms; no atribuido); ambas corridas registran `git.dirty = true`.

## 11. Riesgos

| # | Riesgo | Severidad | Origen |
|---|---|---|---|
| R1 | Ejecutar el plan tal cual deja un historial **roto** (CMG sin Kernel; PoC sin sandbox; tests sin sus scripts/resultados) | Alta | §3.2 |
| R2 | `git add datasets/` incorpora 383 MB de `_tts_cache` (no ignorado) y ≈ 400 MB de mp3 a un remoto GitHub sin LFS | Alta | §3.1, §5.3 |
| R3 | Clon limpio no reproduce: biblioteca fuera de Git; tests dependen de BD y biblioteca; sandbox sin versionar | Alta | §8 |
| R4 | Paquete de evidencia sin `lib-v10`, con afirmación semántica de v10 sin archivo y `alembic_head: FAILED` | Media | §7 |
| R5 | Importación SUS/panel no transaccional; panel «completo» sin exigir 20 celdas | Media | §9 |
| R6 | Hardlinks sin protección de escritura y con extensión a la caché: una edición manual propagaría; copiar sin `-H` reexpande a 2.6 GB | Media | §5.2, §6 |
| R7 | `git.commit=d31d29c/dirty=true` en las corridas: el commit no describe el árbol que las produjo | Media | §5.2 |
| R8 | Informes de auditoría copiados dentro del repo (política del usuario: fuera) | Baja | §7 |
| R9 | Instrucciones de reproducción con `.venv/bin/alembic` (shebang ajeno), Python 3.14 vs Dockerfile 3.12, variables SWARM_* sin documentar | Baja | §8 |
| R10 | Presión por «mejorar» F1 (0.8031 < 0.85) al preparar la defensa: todo cambio sería post-hoc | Alta (metodológica) | §10 |

## 12. Recomendaciones

1. Sustituir el plan de commits por el **orden corregido de §3.2** antes de cualquier `git add`; hacer `git add -p` únicamente con la tabla de hunks de §3.3; verificar cada commit con `git diff --cached --stat`, `alembic heads`, `pytest` acotado y `--verify` del paquete.
2. Añadir a `.gitignore` `datasets/adaptation_library/_tts_cache/` **antes** de cualquier `git add` amplio.
3. Decidir (C) la estrategia de la biblioteca **antes** de commitear `datasets/`; hasta entonces versionar solo el resto.
4. No aplicar el dedupe hasta contar con listado sha256 previo y decidir si interesa (ahorro real de disco: ≈ 768 MB; ninguno en Git).
5. Corregir (en una fase de implementación acotada, no aquí): orden natural en `build_evidence_package.py`; generar `library_semantic_audit` de v10; `alembic_head` en `environment.json`; importación SUS/panel transaccional; actualizar `REPRODUCIBILITY.md` (`python -m alembic`, variables SWARM_*, estado «versionado»).
6. Mantener v1–v10 y la caché intactas; archivar/depurar solo tras decisión explícita con este análisis.
7. No tocar F1/gold/pesos/PSO/regla de parada; toda mejora futura se declara post-hoc con corrida nueva y `run_label` nuevo.
8. Siguiente frente real: SUS + panel (§9), no más código.

## 13. Decisiones que requieren aprobación explícita

## DECISIONES QUE REQUIEREN APROBACIÓN

| # | Decisión | Impacto | Beneficio | Riesgo | Reversibilidad | Recomendación técnica | Comando que se ejecutaría después (NO ejecutado) |
|---|---|---|---|---|---|---|---|
| **A** | Aplicar `dedupe_library --apply` | Reemplaza 3 501 archivos por hardlinks (incl. 2 151 mp3 hacia `_tts_cache`); disco físico 1198 → ≈ 430 MB | Libera ≈ 768 MB en este disco (370 GB libres: no es necesidad) | Bajo lógico (hash verificado antes/después por archivo). Acopla inodos: edición «in place» propaga; copias sin `-H` reexpanden; **cero beneficio en Git** | Lógica total (romper enlaces por copia+`mv`); sin «deshacer» automático | **Diferir.** Beneficio bajo; hacerlo solo tras listado sha256 previo y si el disco lo exigiera | `find datasets/adaptation_library -type f -print0 \| sort -z \| xargs -0 sha256sum > /tmp/pre_dedupe.sha` → `python -m adaptation_swarm.tools.dedupe_library --apply` → `sha256sum -c /tmp/pre_dedupe.sha` (con `LC_ALL=C`) → `python -m adaptation_swarm.multimodal.verify lib-v5-9ae9ffdd` (y v9, v10) |
| **B** | Ejecutar el plan de commits | Crea ≈ 11 commits en `feat/pretest-m1-v4`; el árbol deja de estar sucio | Historia reproducible; ancla del código que produjo las corridas | **Alta si se ejecuta el plan original** (historial roto, `_tts_cache`, secretos no detectados: 0); media con el orden corregido de §3.2 (los `add -p` con `e` pueden equivocarse) | Reversible mientras no se haga `push` (`git reset` solo con permiso explícito; commits nuevos no destruyen archivos) | **Aprobar solo el orden corregido**, por commit, con revisión de `git diff --cached` antes de cada uno; commit del Kernel y del sandbox primero; E1 y `CLAUDE.md` aparte | Ej. (no ejecutar): `git add backend/runtime/…` → `git commit -m "feat(agents): campos experimentales R16-R19 …"` → … → `git add -p backend/app/models/__init__.py` (con `e`) → …; verificación: `python -m alembic heads` (= `b2f4c9d10a02`) |
| **C** | Estrategia Git para la biblioteca (~1.2 GB físicos; ≈ 406 MB únicos) | Define si los mp3/SVG entran al repo o a un almacén externo | Reproducibilidad desde un clon | Normal en Git sin LFS (400 MB en GitHub: lento, difícil de revertir tras `push`); externo: dependencia operativa | Alta si aún no hay `push` | **Opción (a):** en Git solo `datasets/adaptation_library/lib-v*/manifest.json` (con sha256) + `.gitignore` de `_tts_cache/` y de binarios; publicar los binarios de **v5, v9, v10 (≈ 305 MB)** como asset/almacén externo con hash y un script `restore`. Alternativa (b): Git LFS solo para v5+v9+v10. No versionar la caché | `echo 'datasets/adaptation_library/_tts_cache/' >> .gitignore` (siempre); para (a): `git add datasets/adaptation_library/lib-v*/manifest.json`; para (b): instalar `git-lfs` → `git lfs track "datasets/adaptation_library/lib-v5-*/**/*.mp3"` … |
| **D** | Archivar versiones antiguas (p. ej. v1, v2, v3, v4; v6–v8) | Mueve/comprime versiones fuera de la ruta activa | Menos ruido; v2 es una rama lateral sin uso | Pérdida de trazabilidad de desarrollo si se descarta sin hash/informe; sin evidencia de que sean innecesarias | Reversible si se archiva con manifiesto y sha256 (no si se borra) | **No decidir ahora.** Si se decide luego: archivar (nunca borrar) v2 primero; conservar manifiestos y sus auditorías; **nunca** v5, v9, v10 | `tar --hard-dereference`… (definir tras la decisión); mover, no `rm`; verificar hashes antes/después |
| **E** | Regenerar un paquete de evidencia actualizado (`evidence_package_2026-09-24/`) con Fase 3/`human_eval` | Nuevo directorio (~5 MB), no sobrescribe el del 09-23 | Incluye v10, `human_eval/`, informes de Fase 3/3B y entorno corregido; resuelve los 5 defectos de §7 | Congelar un paquete antes de corregir el orden de versiones y generar la auditoría semántica de v10 lo dejaría con los mismos defectos | Total (es solo un directorio nuevo) | **Aprobar después de**: corregir orden natural de versiones, auditoría semántica de v10, `alembic_head`, y decidir política de informes (dentro/fuera del repo) | `python -m adaptation_swarm.tools.build_evidence_package --out backend/experiments/evidence_package_2026-09-24` (tras la corrección) y `--verify` |

## 14. Checklist final de seguridad

| Pregunta | Respuesta | Evidencia |
|---|---|---|
| ¿Se modificó algún archivo no autorizado? | **NO** | `git status --short` idéntico antes/después (101 entradas); ningún archivo del repo más nuevo que la instantánea inicial (excl. `.git`, `.venv`, `node_modules`, `__pycache__`) |
| ¿Se hizo algún commit? | **NO** | `HEAD` = `d31d29c` |
| ¿Se hizo `git add`? | **NO** | `.git/index` con mtime `2026-09-23 15:27:39` (previo a esta fase); 0 stashes |
| ¿Se hizo `reset` / `clean` / `restore` / `checkout` / `rm`? | **NO** | idem |
| ¿Se aplicó dedupe? | **NO** | solo simulación («SIMULACIÓN: no se modificó nada»); 0 hardlinks nuevos (`_tts_cache` sigue con `nlink=1`) |
| ¿Se eliminó algún archivo? | **NO** | 11 entradas en `datasets/adaptation_library/` (10 versiones + `_tts_cache`), igual que antes; paquete 127/127 |
| ¿Se modificó alguna corrida? | **NO** | sha256 de los 8 `adaptation_swarm_*` idénticos al snapshot inicial y al paquete; `swarm_runs`/`swarm_cycles` sin cambios (100 + 100) |
| ¿Se modificó F1? | **NO** | 0.8031415 en ambos JSON |
| ¿Se modificó el gold? | **NO** | `gold-v1.jsonl`, `gold-table-gold-v1.json` idénticos (snapshot) |
| ¿Se modificó PSO? | **NO** | `adaptation_swarm/pso/` no fue tocado en esta fase |
| ¿Se modificó la regla de parada? | **NO** | idem (`ε=0.001`, `k_max=15` en ambas configs) |
| ¿Se modificó documentación de tesis, Master Spec, Decision Closure o Decision Register? | **NO** | solo se leyeron/citaron; solo se creó este informe |
| ¿Se migró/generó/degradó alguna migración? | **NO** | `alembic heads/history/current` únicamente |
| ¿Se insertaron datos SUS/panel? | **NO** | 0/0/0 |
| ¿Se ejecutó una nueva corrida? | **NO** | — |

Estado de esta fase: `PRE-COMMIT-PRE-DEDUPE-AUDIT-2026-09-24.md` creado; el informe permite decidir A–E con la evidencia de §3–§9.
