# Fase 3C — Corrección de entregables y evidencia (2026-09-24)

Alcance: corregir los defectos detectados en `PRE-COMMIT-PRE-DEDUPE-AUDIT-2026-09-24.md`. No es desarrollo del sistema.
Rama `feat/pretest-m1-v4` @ `d31d29c`; árbol dirty (esperado). Sin commits, `add`, `reset`, `clean`, dedupe ni archivado.
Estados: **VERIFICADO** (ejecutado y comprobado) · **IMPLEMENTADO** · **NO EJECUTADO** (por instrucción).

## 1. Defectos originales

| # | Defecto (auditoría pre-commit §7/§9/§8) | Estado |
|---|---|---|
| 1 | `build_evidence_package.py` elegía la «última» biblioteca con `sorted(nombre)[-1]` → `lib-v9` > `lib-v10`; el paquete no contiene el manifiesto de v10 | **CORREGIDO** |
| 2 | No existía auditoría semántica de `lib-v10`; el índice afirmaba «v9/v10: 0/0/0» | **CORREGIDO** (auditoría real generada; índice reescrito) |
| 3 | `environment.json` guardaba `alembic_head: "FAILED: No 'script_location'…"` (Alembic corrido desde un directorio sin `alembic.ini`) | **CORREGIDO** |
| 4 | `sus_cli import-sus/import-gold`: validación completa pero inserción con commits parciales | **CORREGIDO** (una transacción) |
| 5 | `REPRODUCIBILITY.md`: Python 3.14/3.12 confuso, `.venv/bin/alembic`, variables `SWARM_*` sin documentar, biblioteca «versionada» sin aclarar que no está en un clon limpio | **CORREGIDO** |
| 6 | Índice de evidencia con una afirmación sin archivo detrás | **CORREGIDO** (mismo cambio que 2) |

## 2. Correcciones realizadas

### 2.1 Selección de la última biblioteca — `tools/build_evidence_package.py`
- Nueva `latest_library_version(lib)`: reutiliza `multimodal.versioning.latest_version` (regex `lib-v(\d+)-hash8`, orden por **entero**), exige que exista `manifest.json` y falla (`SystemExit`) si no.
- `build()` la llama al inicio, antes de crear el directorio, y la registra en `06_entorno/environment.json` (`library_latest`). Los manifiestos copiados son v5, v9 y la última (sin duplicados: `dict.fromkeys`).
- Medido sobre la biblioteca real: `latest_library_version(...)` → `lib-v10-5dd83cd4`.

### 2.2 Auditoría semántica real de `lib-v10-5dd83cd4`
Generada con la herramienta existente (sin escribir conclusiones a mano):

`python -m adaptation_swarm.multimodal.extend --base lib-v10-5dd83cd4 --audit-only`
→ `AUDITORÍA lib-v10-5dd83cd4: código 0/90 · texto 0/90 · diagramas 0/270 con hallazgos`

Archivo: `backend/experiments/results/library_semantic_audit_lib-v10-5dd83cd4.json` (`sha256 9a640781…4312`; `concepts: 30`, `per_concept: {}`).
`--audit-only` solo lee la versión y escribe el JSON: no crea versiones ni modifica la biblioteca (verificado: 10 versiones + `_tts_cache`, manifiestos idénticos).
La auditoría es una re-ejecución determinista de los validadores semánticos (sin LLM); el test la recomputa en vivo y exige igualdad con el archivo.

Resumen de todas las auditorías existentes (código / texto / diagramas con hallazgos):

| versión | código | texto | diagramas |
|---|---|---|---|
| lib-v5 | 53/90 | 6/90 | 15/270 |
| lib-v6 | 8/90 | 3/90 | 0/270 |
| lib-v7 | 5/90 | 0/90 | 8/270 |
| lib-v8 | 0/90 | 0/90 | 0/270 |
| lib-v9 | 0/90 | 0/90 | 0/270 |
| **lib-v10** | **0/90** | **0/90** | **0/270** |

Nota: el archivo de v9 lo generó `extend` al extender v9→v10 (audita la *base*); el de v10 es propio.

### 2.3 `environment.json` — head real de Alembic
- Nueva `alembic_head(back=BACK)`: ejecuta `sys.executable -m alembic heads` con `cwd=backend/`, extrae la revisión con `^([0-9a-f]+) \(head\)` y exige exactamente **una** cabeza. Si no puede, lanza `RuntimeError`; **nunca** guarda texto de error como valor.
- Nueva `collect_environment(library_latest)` (mismo contenido que antes + `alembic_head` dinámico y `library_latest`); `build()` la ejecuta **antes** de crear el directorio, de modo que un fallo no deja un paquete a medias.
- `pip freeze` usa `sys.executable` (no un `.venv/bin/python` fijo).
- Valor obtenido dinámicamente: `b2f4c9d10a02` (no hay ningún valor codificado en el código).

### 2.4 Importación SUS/panel transaccional — `persistence/human_eval.py`
- Se extrajeron los constructores de filas (`_validated_participant`, `_sus_row`, `_gold_row`) sin cambiar las reglas de los métodos públicos (`register_participant`, `add_sus_response`, `add_gold_rating`, mismos mensajes y excepciones).
- `import_sus_csv` e `import_gold_csv`: se **conserva** la validación previa completa de todas las filas; luego inserta **todo en una sola sesión/transacción** con `flush()` por fila (para que las violaciones de unicidad/CHECK aparezcan dentro de la transacción) y `commit()` único; cualquier excepción → `rollback()` y se relanza.
- Demostrado que la lógica anterior dejaba parciales: replicando el bucle anterior con `[V01, V02, V01]`, quedaban **2 participantes y 2 respuestas** tras el `IntegrityError`; con el código nuevo quedan **0** (tests C/D).
- No se tocaron modelos ni migraciones; no se insertó nada en PostgreSQL (tests sobre SQLite en memoria).

### 2.5 `REPRODUCIBILITY.md` (y `scripts/repro_db_bootstrap.sh`)
- Versiones de Python separadas: backend en contenedor 3.12 (`backend/Dockerfile`), sandbox de Python 3.11 (`app/sandbox/docker/Dockerfile`), entorno local de desarrollo con el que se produjeron los resultados 3.14.7. Se declara que **3.14 no es un requisito** y que **no se ha verificado** la instalación/pruebas de las dependencias fijadas bajo 3.12.
- `python -m alembic` en lugar de `.venv/bin/alembic` (con la razón: shebang que puede apuntar a otra copia del repo). El bootstrap (`scripts/repro_db_bootstrap.sh`) se cambió en consecuencia (3 líneas) y se **probó de extremo a extremo** en una base temporal (`upao_repro_3c`, creada y eliminada por mí): `OK: esquema en b2f4c9d10a02 (head)`, 32 ids de conceptos realineados; `alembic_version = b2f4c9d10a02`, `concepts = 32`, `swarm_runs = 0`. La base `upao_mas_edu` no se tocó; tras el drop solo quedan `postgres`, `upao_mas_edu`, `template0/1`.
- Nueva §8 con las variables de entorno, **obligatorias** (`DATABASE_URL`, `OPENAI_API_KEY` solo para generar/extender, `SWARM_API_KEY` solo para el endpoint) y **opcionales con su default** (`SWARM_REDIS_URL`, `SWARM_REDIS_PREFIX`, `SWARM_REDIS_MAX_CONNECTIONS`, `SWARM_STREAM_MAXLEN`, `SWARM_SEEN_TTL_SECONDS`, `SWARM_LOG_TTL_SECONDS`, `SWARM_REQUEST_TIMEOUT`, `SWARM_LIBRARY_ROOT`, `SWARM_SANDBOX_BIN`, `SWARM_API_PERSIST`, `SWARM_API_RUN_LABEL`, `MERMAID_CHROME`, y las de carga). Los valores se tomaron del código (`config.py`, `api/router.py`, `render.py`, `app/core/config.py`). La variable que el encargo llamaba «RUN_LABEL» es `SWARM_API_RUN_LABEL` en el código.
- Nueva §9 «Qué NO está autocontenido en un clon limpio»: `datasets/adaptation_library/` **no** está en Git ni en un clon; v5 y v9 son el mínimo para reproducir las corridas; el mecanismo de recuperación **aún no está decidido** (sin inventar almacenamiento externo ni elegir Git/LFS); tests/exportación que leen filas reales de Postgres; servicios/binarios externos; `git.dirty=true` en las corridas.
- Se reemplazó la marca «* sin versionar» de la cadena Alembic por un estado con fecha (2026-09-24).

### 2.6 Índice de evidencia — `adaptation_swarm/EVIDENCE_INDEX.md`
La línea «lib-v9/v10: 0/0/0» se sustituyó por la tabla real de las 6 auditorías (§2.2), cada cifra leída de su archivo, con la aclaración de qué audita cada archivo (base vs. propia) y cómo se generó el de v10. **El paquete 2026-09-23 no se editó** (su `README_EVIDENCE_INDEX.md` conserva la frase antigua y su `environment.json` conserva `FAILED`; quedan como estado histórico congelado y serán superados por el paquete siguiente).

## 3. Archivos

**Creado:** `backend/experiments/results/library_semantic_audit_lib-v10-5dd83cd4.json` (salida de la herramienta).

**Modificados (todos dentro de rutas ya sin seguimiento, salvo el script):**
- `backend/adaptation_swarm/tools/build_evidence_package.py`
- `backend/adaptation_swarm/persistence/human_eval.py`
- `backend/adaptation_swarm/REPRODUCIBILITY.md`
- `backend/adaptation_swarm/EVIDENCE_INDEX.md`
- `backend/scripts/repro_db_bootstrap.sh` (sin seguimiento)
- `backend/tests/adaptation_swarm/test_evidence_and_tools.py` (+4 pruebas)
- `backend/tests/adaptation_swarm/test_sus_panel.py` (+5 pruebas)

`git diff --stat` (archivos tracked) sigue en 16 archivos, +454/−31: ninguna de estas correcciones tocó un archivo rastreado.

## 4. Tests nuevos (9)

| Prueba | Demuestra |
|---|---|
| `test_latest_library_version_numeric_order` | con `lib-v1/v2/v9/v10` el orden lexicográfico antiguo da `v9`; la función da `lib-v10`; sin `manifest.json` → `SystemExit` |
| `test_latest_library_version_of_the_real_library_is_the_highest_number` | sobre la biblioteca real devuelve el número máximo |
| `test_v10_semantic_audit_exists` | el archivo existe, es de `lib-v10-5dd83cd4`, 30 conceptos, **igual a una re-auditoría en vivo**; el índice lo cita y ya no contiene «lib-v9/v10: 0/0/0» |
| `test_environment_json_reports_real_alembic_head` | `alembic_head()` = head obtenido por un `alembic heads` independiente; `collect_environment()` no contiene «FAILED»; fuera de `backend/` lanza `RuntimeError` |
| `test_import_sus_case_a_valid_csv_inserts_every_row` | CSV válido → 3 participantes + 3 respuestas |
| `test_import_sus_case_b_invalid_row_inserts_nothing` | fila inválida en validación → 0 filas |
| `test_import_sus_case_c_error_during_insertion_rolls_back_everything` | fallo simulado al insertar la 3.ª respuesta (con 2 participantes ya enviados a la BD) → 0 filas |
| `test_import_sus_case_d_duplicates_roll_back_everything` | seudónimo repetido en el CSV, y seudónimo ya existente → sin importación parcial |
| `test_import_gold_case_e_unknown_participant_rolls_back_everything` | participante inexistente y celda repetida → la valoración válida previa tampoco queda insertada |

Sin `skip`/`xfail`; no se modificó ninguna prueba existente. Los vectores numéricos de las pruebas SUS son de formato, no respuestas de personas; SQLite en memoria.

## 5. Resultados de tests

- Nuevas + módulos afectados: `test_sus_panel.py` + `test_evidence_and_tools.py` → **24 passed**.
- Suite completa: `python -m pytest tests/adaptation_swarm -q` → **210 passed** (201 previos + 9 nuevos), 1 warning preexistente.
- Prueba de humo del bootstrap en BD temporal: OK (§2.5).

## 6–9. Auditoría v10, environment.json, atomicidad, reproducibilidad

Ver §2.2–§2.5. Estado: auditoría v10 real **0/0/0**; `environment.json` reportará `b2f4c9d10a02` (obtenido dinámicamente; **no se generó un paquete nuevo**, así que ese archivo se comprobó vía la función y su test); importación SUS/panel **transaccional**; reproducibilidad **actualizada y probada** en BD temporal.

## 10. Cambios del índice de evidencia
Ver §2.6.

## 11. Hashes antes/después (sha256 de 174 archivos en el snapshot previo vs. 175 en el posterior)

Comparados: `adaptation_swarm_*` (corridas, casos, auditorías F1/PSO, sensibilidad), `library_semantic_audit_*` previas, `synthetic_profiles/*` (incluye `gold-v1.jsonl` y `gold-table-gold-v1.json`), los 10 `manifest.json` de biblioteca (v1…v10, incluidos v5/v9/v10), los 127+1 archivos del paquete 2026-09-23 y todos los `.py` de `adaptation_swarm/{pso,gold,fitness}/`.
Resultado de `diff`: **una sola diferencia — el archivo nuevo** `library_semantic_audit_lib-v10-5dd83cd4.json`. Ninguna línea existente cambió.

Hashes de referencia (16 primeros caracteres, idénticos antes y después): poc-1 `7e1037f1f7e25228`, poc-1 cases `3bcf9dd3998d713c`, poc-1 F1-audit `008885f0ecebac54`, poc-1 PSO-audit `f0730e6da5f5b8a6`, poc-2 `a2c67f91e1fc5809`, poc-2 cases `b17c5d478603df83`, poc-2 F1-audit `6b31a898e95a9eff`, sensibilidad `d59ff801b331286e`.

## 12–14. Confirmaciones experimentales
- **F1_adapt = 0.8031** (0.8031415 en `adaptation_swarm_corrida-poc-1.json` y `-2.json`, sin cambios; RNF03 sigue **NO cumplido**).
- **corrida-poc-1 intacta** (JSON, casos, auditorías F1/PSO por hash; `swarm_runs`/`swarm_cycles` sin cambios; `test_corrida_poc_1_preserved` pasa).
- **corrida-poc-2 intacta** (JSON, casos, auditoría F1 por hash; 100 ciclos en Postgres).
- Gold, PSO, fitness, regla de parada (ε, `k_max`) y pesos: los archivos de `pso/`, `gold/`, `fitness/` y las tablas gold tienen hash idéntico.
- Paquete `evidence_package_2026-09-23`: `VERIFICADO: todos los hashes coinciden`; **no se generó** `evidence_package_2026-09-24`.

## 15–17. Datos humanos, dedupe, Git
- Datos humanos: `sus_cli status` → `participants: 0`, `sus_responses: 0`, PENDIENTE DE RECOLECCIÓN HUMANA; las pruebas usan SQLite en memoria.
- Dedupe: **no se ejecutó** (`_tts_cache` sin enlaces duros; biblioteca con las mismas 10 versiones + caché).
- Git: HEAD = `d31d29c`; `.git/index` con mtime `2026-09-23 15:27:39` (sin `add`); 0 stashes; `git status --short` idéntico salvo el archivo nuevo de auditoría.

## Observaciones (no corregidas por estar fuera del alcance)
- El valor por defecto de `--out` de `build_evidence_package.py` sigue siendo `evidence_package_2026-09-23`; es inofensivo mientras ese directorio exista (el constructor no sobrescribe), pero conviene exigir `--out` explícito al generar el paquete siguiente.
- `AUDIT_DIR` (informes) está codificado como ruta absoluta en el mismo archivo; el paquete siguiente copiará informes desde `Auditoria Tesis/` según lo acordado (copia congelada; los informes no pasan a Git).
- Aparecen directorios `.impeccable/` (caché de un hook de otra herramienta, p. ej. `datasets/adaptation_library/.impeccable/hook.cache.json`, creado la noche anterior); no son de este trabajo y la herramienta de dedupe ignora archivos ocultos.
- Pendiente para fases posteriores (decisión del usuario): decisión C (biblioteca), plan de commits corregido (defectos §3.2 de la auditoría pre-commit: Kernel, sandbox, `.gitignore` de `_tts_cache`), nuevo paquete de evidencia y recolección humana SUS/panel.

## Check final

- [x] F1 no cambió (0.8031)
- [x] gold no cambió
- [x] PSO no cambió
- [x] regla de parada no cambió
- [x] corrida-poc-1 intacta
- [x] corrida-poc-2 intacta
- [x] biblioteca no modificada físicamente (manifiestos idénticos; solo se leyó)
- [x] ningún dato humano insertado
- [x] ningún commit
- [x] ningún `git add`
- [x] ningún `reset`
- [x] ningún `clean`
- [x] ningún `dedupe --apply`
- [x] ningún archivo de tesis modificado
- [x] Master Spec intacto
- [x] Decision Closure intacto
- [x] Decision Register intacto
