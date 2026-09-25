# Fase 3E — Implementación no destructiva de la Decisión C y paquete de evidencia (2026-09-24)

**ESTRATEGIA CERRADA: D híbrida.** **MECANISMO EXTERNO DEL AUDIO: PENDIENTE.**
Rama `feat/pretest-m1-v4` @ `d31d29c`; árbol dirty (esperado). Sin commits, `add`, `reset`, `clean`, dedupe, borrados ni movimientos; sin MP3 en el repositorio; sin proveedor externo ni Git LFS.

## 1. Alcance
Implementar de forma aditiva lo que la Decisión C (DECISION-CLOSURE §14) permite sin resolver el mecanismo externo: `.gitignore`, inventario/verificación de la biblioteca, clasificación de tests, copia sellada local del audio, constructor seguro del paquete de evidencia y generación de `evidence_package_2026-09-24`.

## 2. Estado inicial (instantánea previa)
HEAD `d31d29c`; `git status --short` (100 entradas + el archivo de auditoría v10 de 3C); sha256 de: `adaptation_swarm_*` (corridas, casos, auditorías F1/PSO, sensibilidad), auditorías semánticas, `synthetic_profiles/*` (gold/dataset), los 10 manifiestos, los 128 archivos del paquete 2026-09-23 y `pso/`, `gold/`, `fitness/`; inventario de la biblioteca (7 844 archivos con tamaño e inodo); sha256 de los documentos de autoridad (Closure/Master/Register…); `git diff --stat` 16 archivos.

## 3. Cambios implementados

### 3.1 `.gitignore` (archivo rastreado; único cambio: 6 líneas añadidas al final)
```
datasets/adaptation_library/_tts_cache/
datasets/adaptation_library/lib-v*/artifacts/**/*.mp3
```
(con comentario que remite a la Decisión C). Verificado con `git ls-files --others --ignored --exclude-standard` y `git check-ignore -v`:
| | Archivos |
|---|---|
| **Ignorados** | 2 151 mp3 de versiones (`audio_t*a*.mp3`) + 393 archivos de `_tts_cache/` |
| **Visibles (versionables)** | 10 `manifest.json`, 717 `.py`, 399 `.cpp`, 2 151 `.mmd`, 717 `.txt`, 1 305 `.svg` |
| mp3 visibles / caché visible | 0 / 0 |
`manifest.json` y `.svg` no coinciden con ninguna regla (`check-ignore` sin salida). No se usó `git rm` ni ninguna operación sobre archivos.

### 3.2 Inventario y verificación — `adaptation_swarm/tools/library_inventory.py` (nuevo)
Solo lectura; calcula todo desde los archivos y manifiestos (nada escrito a mano). Ordena versiones **numéricamente**. Por versión: `version`, `directory`, `base_version`, sha256 del manifiesto y coherencia del hash con el nombre de la versión, archivos en disco, entradas, conteo por modalidad (código, C++, texto, `.mmd`, SVG, audio), bytes, presencia e integridad de audio y SVG, archivos no listados y corridas que la usaron. Los estados **no se confunden**: por artefacto `ok` / `absent` / `hash_mismatch`; por modalidad `presence` = completa | parcial | ausente y `integrity` = hash_correcto | hash_incorrecto | no_verificable. Las salidas `library_inventory.json/.md` son deterministas (sin marcas de tiempo) y no se sobrescriben. CLI: `--out DIR`, `--check` (exit 1 ante hash incorrecto o manifiesto alterado), `--require-complete` (además exit 1 si falta algo), `--no-hash`.
- `multimodal/verify.py` (modificado): un archivo ausente ya **no** aborta con excepción ni se cuenta como hash incorrecto: `missing_files` aparte; exit 0 íntegra · 1 hash incorrecto/conceptos incompletos · 2 solo faltan archivos.

Resultado real (`--check --require-complete`, exit 0; 10 versiones; 2.9 s con caché por inodo):

| versión | archivos | código | C++ | texto | .mmd | SVG (n/MB/presencia/integridad) | audio (n/MB/presencia/integridad) | usada por |
|---|---|---|---|---|---|---|---|---|
| lib-v1 | 25 | 3 | 0 | 3 | 9 | 0 / — / no_aplica | 9 / 8.0 / completa / hash_correcto | — |
| lib-v2 | 337 | 42 | 0 | 42 | 126 | 0 | 126 / 116.2 / completa / hash_correcto | — |
| lib-v3 | 385 | 48 | 0 | 48 | 144 | 0 | 144 / 135.4 / completa / hash_correcto | — |
| lib-v4 | 673 | 84 | 0 | 84 | 252 | 0 | 252 / 238.1 / completa / hash_correcto | — |
| **lib-v5** | 721 | 90 | 0 | 90 | 270 | 0 | 270 / 257.7 / completa / hash_correcto | **corrida-poc-1** |
| lib-v6 | 1 030 | 90 | 66 | 90 | 270 | 243 / 30.7 / completa / hash_correcto | 270 / 257.9 / completa / hash_correcto | — |
| lib-v7 | 1 048 | 90 | 75 | 90 | 270 | 252 / 32.5 / completa / hash_correcto | 270 / 257.9 | — |
| lib-v8 | 1 072 | 90 | 81 | 90 | 270 | 270 / 35.5 / completa / hash_correcto | 270 / 257.9 | — |
| **lib-v9** | 1 078 | 90 | 87 | 90 | 270 | 270 / 35.5 / completa / hash_correcto | 270 / 257.9 / completa / hash_correcto | **corrida-poc-2** |
| **lib-v10** (latest) | 1 081 | 90 | 90 | 90 | 270 | 270 / 35.5 / completa / hash_correcto | 270 / 257.9 / completa / hash_correcto | — |
Los 10 `manifest_id_ok = sí`; 0 archivos no listados; hash_incorrecto: ninguno; ausentes: ninguno. Caché TTS: 393 archivos (383.3 MB), 15 huérfanos (14.7 MB).

### 3.3 Clasificación de tests (`requires_library_audio`) — sin skip genérico
- Se identificaron **ejecutando la suite (sin `test_persistence`) contra una biblioteca de symlinks sin mp3** (en el scratchpad, ya eliminada): **27 casos** dependen físicamente del audio (8 en `test_cycle_integration`, `test_package_validation` completo —5 pruebas, 14 casos con parámetros—, 2 en `test_api_adaptation`, 1 en `test_agents_library`, 1 en `test_library_full_coverage`, 1 en `test_corrida_poc_1_preserved`); los otros **189 pasan sin audio**, incluidos PSO, fitness y gold/F1.
- `conftest.py`: marcador registrado; **encabezado de pytest** que informa si la biblioteca está completa; con archivos **ausentes** las pruebas marcadas se omiten con una razón explícita que cuenta los que faltan por versión; `SWARM_REQUIRE_LIBRARY=1` las hace **fallar** en ausencia; un archivo **presente con hash incorrecto nunca se omite** (la prueba corre y falla).
- Documentado en `tests/adaptation_swarm/LIBRARY_TESTS.md` (por qué necesitan biblioteca y audio, condición externa, evidencia que produce cada prueba, cómo ejecutarlas y restaurar). Evidencia: sin audio → 189 passed, 27 skipped, 0 failed; sin audio con `SWARM_REQUIRE_LIBRARY=1` → fallan como antes; con biblioteca completa → 0 skipped.
- El comportamiento experimental no cambió: solo se añadieron marcadores; ninguna prueba fue modificada ni debilitada.

### 3.4 Copia sellada del audio — `tools/seal_audio.py` (nuevo) y ejecución
COPIA ADICIONAL, no movimiento: copia byte a byte (sin reflink ni enlaces duros), verifica el sha256 de cada mp3 contra su manifiesto **antes** (se niega a sellar audio ausente o corrupto) y **después** de copiar, comprueba que el inodo de la copia difiere del original, no sobrescribe (`open('xb')`) y se niega a escribir dentro del repositorio; marca la copia de solo lectura (solo la copia).
- **Ubicación (fuera del repo):** `<HOME>/Documentos/2026-20/Tesis II/Biblioteca sellada 2026-09-24/`
- **Contenido:** los 2 151 mp3 de las **10 versiones** (v5, v9 y v10 incluidas) en su ruta relativa, los 10 `manifest.json`, `library_inventory.json/.md`, `README-SEALED.md`, **`SHA256SUMS`** (2 164 entradas).
- **Tamaño:** 2.0 GB (2 044 743 552 bytes de mp3), copia física independiente.
- **Verificación:** `LC_ALL=C sha256sum -c SHA256SUMS` → 2 164 OK, 0 fallos; `seal_audio --verify` → `ok: true` (0 ausentes, 0 hash incorrecto, 0 discrepancias contra manifiestos); 0 archivos con permiso de escritura; inodos distintos de los originales.
- **Declaración explícita (README-SEALED.md y paquete):** «copia sellada local; NO constituye todavía almacenamiento externo de preservación institucional».
- Originales: inventario tras el sellado idéntico (7 844 archivos, mismos tamaños e inodos; sin hardlinks nuevos; `_tts_cache` con `nlink=1`).

### 3.5 Constructor seguro — `build_evidence_package.py` (modificado)
- `--out` **obligatorio** (sin destino por defecto: sin él, `error: --out es obligatorio`, exit 2).
- Rechaza el paquete histórico `evidence_package_2026-09-23` por nombre **y** por ruta resuelta (`../` incluidos) y cualquier directorio existente.
- **`--dry-run`** (nuevo): ejecuta `preflight` completo **sin escribir nada** — destino nuevo, última versión numérica, inventario con hashes (falla si hay hash incorrecto o manifiesto alterado), versión de biblioteca de ambas corridas, head real de Alembic y, con `--sealed-copy`, verificación de la copia sellada.
- Nuevo `07_biblioteca/` (inventario, `library_map.json`, manifiestos de las versiones de las corridas y de la última, `audio_sha256_<versión>.txt` derivado de los manifiestos, copia de `SHA256SUMS`/README de la copia sellada y `sealed_copy.json`); `06_entorno/human_eval_status.json` (lectura de BD); se copian `human_eval/` y `LIBRARY_TESTS.md`; las versiones de las corridas se **derivan** de los JSON (ya no están codificadas).
- **`--check DIR`** (nuevo): además de los hashes, comprueba hechos (§3.6).
- Estructura: se conservó la numeración existente y se añadió `07_biblioteca/` (trazabilidad equivalente a la propuesta `04_library`).

### 3.6 Paquete `evidence_package_2026-09-24` (generado tras el dry-run)
`backend/experiments/evidence_package_2026-09-24/`: **151 archivos + `MANIFEST.sha256`** (6.8 MB, **0 mp3**). Generado con `--out experiments/evidence_package_2026-09-24 --sealed-copy "<copia sellada>"`.
Contenido: `01_datos_de_entrada` (dataset y gold) · `02_corridas_y_auditorias` (corridas congeladas, auditorías F1/PSO, **auditorías semánticas v5…v10** incluida la de v10, exportación de Postgres) · `03_informes` (copias congeladas de los informes de `Auditoria Tesis/`; **no** hace que esa carpeta pase a Git) · `04_carga` · `05_documentacion` (ADR, REPRODUCIBILITY, LIBRARY_TESTS, `human_eval/` con plantillas vacías) · `06_entorno` · `07_biblioteca` · `README_EVIDENCE_INDEX.md` (índice ampliado con la sección de biblioteca/Decisión C) · `MANIFEST.sha256`.
El informe de esta fase **no** está en el paquete (se escribe después de generarlo); el índice lo declara.

## 4. Validación del paquete

| Comprobación | Resultado |
|---|---|
| `--verify` (MANIFEST.sha256) | «VERIFICADO: todos los hashes coinciden» |
| `--check` (hechos) | «CONSISTENTE: hashes y hechos verificados» |
| latest = `lib-v10-5dd83cd4` | ✔ (mapa, entorno e inventario coinciden con el máximo numérico) |
| `corrida-poc-1` = `lib-v5-9ae9ffdd`; `corrida-poc-2` = `lib-v9-a0231e9b` | ✔ (JSON, mapa y manifiestos presentes) |
| Alembic head = `b2f4c9d10a02` | ✔ (dinámico; igual al head vivo) |
| F1 = 0.8031415 (ambas corridas) | ✔ (tolerancia 1e-6) |
| Corridas del paquete = resultados vivos | ✔ (sha256 idéntico) |
| Participantes humanos | ✔ 0 participantes, 0 respuestas, 0 valoraciones (PENDIENTE DE RECOLECCIÓN HUMANA) |
| Sin audio en el paquete | ✔ 0 mp3 |
| Copia sellada verificada al generar | ✔ `ok: true` |
| Documentos del paquete = fuentes vivas (índice, REPRODUCIBILITY, LIBRARY_TESTS) | ✔ idénticos al generar; **excepción posterior:** `LIBRARY_TESTS.md` de la fuente se corrigió después («5 pruebas, 14 casos» en lugar de «6 pruebas, 13 casos»), por lo que la copia del paquete conserva esa imprecisión numérica (el recuento total de 27 casos era y es correcto) |
| Paquete 2026-09-23 | ✔ intacto (`--verify` OK; conserva su estado histórico, incluido su `alembic_head: FAILED`, sin `07_biblioteca`) |

## 5. Tests
- Nuevos: `test_library_inventory.py` (14: orden numérico, presencia/ausencia/hash incorrecto, parcial/no listados, manifiesto alterado, hashing por inodo y determinismo, no sobrescritura, presencia rápida, inventario real, `verify` con audio ausente, copia sellada independiente/aditiva, rechazo de audio incompleto/corrupto y destino dentro del repo, verificación que separa ausente de discrepancia) y `test_evidence_and_tools.py` (+4: `--out` obligatorio y paquete histórico protegido, dry-run que no escribe, paquete 09-24 consistente y 09-23 intacto, `validate_package` detecta un hecho alterado).
- Suite completa con biblioteca completa y **`SWARM_REQUIRE_LIBRARY=1`**: **223 passed**, 0 skipped, 0 failed (5 deseleccionados: `test_persistence.py`).
- **`test_persistence.py` no se ejecutó** en esta fase porque escribe (y borra) filas de prueba en PostgreSQL y la fase prohíbe modificarlo; no cambió desde 3C (210 passed incluía esas 5). Estado de la BD antes/después: `swarm_runs` 2, `swarm_cycles` 100+100, `swarm_iterations` 544, `agent_messages` 11 676, `multimodal_candidates` 3 597, `multimodal_packages` 200, SUS/panel 0/0/0, `alembic_version` = `b2f4c9d10a02` (idénticos a los medidos en 3B).

## 6. Estado de reproducibilidad
`REPRODUCIBILITY.md §9` actualizado: estrategia D, `.gitignore` ya aplicado, «aún no se ha commiteado» la biblioteca, herramientas y códigos de salida, pruebas marcadas, copia sellada local (no institucional), y que **verificar ≠ reproducir**: los resultados congelados se verifican sin biblioteca; volver a ejecutar ciclos exige audio y SVG presentes. Un clon con la biblioteca commiteada traerá manifiestos y artefactos no-audio pero **no** el audio.

## 7. Estado de la Decisión C
**ESTRATEGIA CERRADA: D híbrida** (dentro de Git: manifiestos + `.py`/`.cpp`/`.mmd`/texto/SVG; fuera: mp3 y `_tts_cache/`). Ninguna versión eliminada; v5, v9 y v10 íntegras (incluido su audio) y respaldadas por la copia sellada local.

## 8. Mecanismo externo del audio: PENDIENTE
No se eligió proveedor, ni Git LFS, ni almacenamiento institucional; no se publicó audio ni se subió ningún mp3. Falta: (a) requisito de publicación (asesor/jurado); (b) almacenamiento con retención asegurada; (c) viabilidad/cuota de Git LFS; (d) términos de OpenAI TTS/LLM en repositorio público; (e) política de retención de v1–v4 y v6–v8. Mientras tanto la protección del audio es el original + la **copia sellada local** (misma máquina/disco: protege contra borrado o edición accidental, **no** contra la pérdida del disco).

## 9. Integridad antes/después (check final)
- [x] F1 = 0.8031415 (poc-1 y poc-2)
- [x] gold intacto (`gold-v1.jsonl`, `gold-table-gold-v1.json`: hash idéntico)
- [x] PSO / fitness intactos (todos los `.py` de `pso/`, `gold/`, `fitness/`: hash idéntico); regla de parada intacta (ε, `k_max` en las configs)
- [x] corrida-poc-1 y corrida-poc-2 intactas (JSON, casos, auditorías; BD sin cambios)
- [x] 10 versiones presentes (v5, v9, v10 incluidas); biblioteca con los **mismos 7 844 archivos, tamaños e inodos**; 393 archivos en `_tts_cache` (sin enlaces)
- [x] ningún MP3, SVG, código ni manifest eliminado o modificado (10 manifiestos con hash idéntico)
- [x] sin `dedupe --apply` (0 hardlinks nuevos)
- [x] sin `git add` (`.git/index` con mtime `2026-09-23 15:27:39`), sin commit (HEAD `d31d29c`), sin reset, sin clean, 0 stashes
- [x] PostgreSQL sin cambios (recuentos idénticos; solo lecturas)
- [x] Master Spec, Decision Register, Decision Closure y documentos de tesis: hash idéntico al inicio de la fase
- [x] paquete 2026-09-23: 128 archivos con hash idéntico
Único cambio en `git status`: `M .gitignore` y `?? backend/experiments/evidence_package_2026-09-24/`; `git diff --stat` pasa de 16 a 17 archivos (+6 líneas de `.gitignore`).

## 10. Archivos
**Creados:** `backend/adaptation_swarm/tools/library_inventory.py`, `backend/adaptation_swarm/tools/seal_audio.py`, `backend/tests/adaptation_swarm/test_library_inventory.py`, `backend/tests/adaptation_swarm/LIBRARY_TESTS.md`, `backend/experiments/evidence_package_2026-09-24/` (151 archivos + MANIFEST), copia sellada `Tesis II/Biblioteca sellada 2026-09-24/` (fuera del repo), este informe.
**Modificados:** `.gitignore` (+6 líneas), `backend/adaptation_swarm/tools/build_evidence_package.py`, `backend/adaptation_swarm/multimodal/verify.py`, `backend/adaptation_swarm/EVIDENCE_INDEX.md`, `backend/adaptation_swarm/REPRODUCIBILITY.md`, `backend/tests/adaptation_swarm/conftest.py`, marcadores en `test_cycle_integration.py`, `test_package_validation.py`, `test_api_adaptation.py`, `test_agents_library.py`, `test_library_full_coverage.py`, `test_corrida_poc_1_preserved.py`, y 4 pruebas nuevas en `test_evidence_and_tools.py`.
**NO modificados:** biblioteca (artefactos y manifiestos), `_tts_cache`, corridas y resultados (`experiments/results`), dataset/gold, `pso/`, `gold/`, `fitness/`, paquete 2026-09-23, PostgreSQL, Master Spec, Decision Register, DECISION-CLOSURE (sin cambios en esta fase), documentos de tesis, y ningún archivo rastreado salvo `.gitignore`.

## 11. Observaciones
- **Imprecisión conocida en la copia de `05_documentacion/LIBRARY_TESTS.md` del paquete** (ver §4): dice «6 pruebas, 13 casos» para `test_package_validation`; lo correcto es 5 pruebas y 14 casos (27 casos en total, sin cambio). No se regeneró el paquete para no borrar/sobrescribir; se corregirá al generar el siguiente.
- El paquete 2026-09-24 contiene `06_entorno/git_status.txt` tomado antes de crearlo (no lista el propio paquete) y no incluye este informe.
- `--check` fija `EXPECTED_F1 = 0.8031415` y «0 humanos» como valores esperados al generar; tras la recolección humana habrá que llamar a `validate_package(..., expect_no_humans=False)`.
- El paquete sigue dependiendo de rutas absolutas locales para copiar los informes (`AUDIT_DIR`) y de la copia sellada local; en otra máquina hay que ajustarlas.
- Antes de commitear: el plan de commits corregido (Kernel, sandbox, `.gitignore`, biblioteca no-audio) sigue pendiente; `.gitignore` ya está listo.

## 12. Siguiente acción exacta
Revisar este informe y `evidence_package_2026-09-24/` (`README_EVIDENCE_INDEX.md`, `07_biblioteca/`). Si son conformes: (1) cerrar la parte abierta de la Decisión C con la evidencia (a)–(e) cuando esté disponible, y (2) escribir el **plan de commits corregido** (Kernel R16–R19 → sandbox Podman/SELinux → CMG → tablas swarm → `adaptation_swarm` → endpoint → tests → dataset+resultados → biblioteca manifiestos+no-audio → ADR → loadtest → paquete de evidencia), sin ejecutar ningún commit hasta su aprobación.
