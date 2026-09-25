# Paquete de evidencia final: `evidence_package_2026-09-24-final/`

Instantánea de la evidencia de la PoC `adaptation_swarm` generada el 2026-09-24 (153 archivos: 152 listados en `MANIFEST.sha256` más el propio manifiesto; 6.8 MB; sin audio). Esta nota está **fuera** del paquete para no alterar lo que su `MANIFEST.sha256` congela.
Los paquetes `evidence_package_2026-09-23/` y `evidence_package_2026-09-24/` son versiones previas del mismo material; **no** se versionan (siguen en disco).

## Verificación (sin PostgreSQL, Redis, OpenAI, TTS ni red; desde `backend/`)
    python -m adaptation_swarm.tools.build_evidence_package --verify experiments/evidence_package_2026-09-24-final    # hashes
    python -m adaptation_swarm.tools.build_evidence_package --check  experiments/evidence_package_2026-09-24-final    # hashes + hechos
    python -m pytest tests/adaptation_swarm/test_evidence_and_tools.py
`MANIFEST.sha256` lista los 152 archivos (ninguno sobra ni falta). Generar un paquete nuevo exige `--out` (nuevo), `--audit-dir` (informes `.md`, sin valor por defecto) y, opcionalmente, `--sealed-copy`.

## Contraste con lo versionado (2026-09-24)
- Datos de entrada (5), corridas, auditorías F1/PSO y sensibilidad (8): **idénticos** a `datasets/synthetic_profiles/` y `experiments/results/` en Git. Manifiestos de biblioteca (3): idénticos a `datasets/adaptation_library/`; las listas `audio_sha256_*` coinciden con esos manifiestos.
- **F1_adapt = 0.8031415** en ambas corridas, **por debajo del objetivo 0.85**; sensibilidad máxima **0.8164** (tampoco lo alcanza). `db_corrida-poc-N_cycles.csv` (exportación de PostgreSQL) coincide con los JSON de corrida.
- Carga: los 85 archivos de `04_carga/` son idénticos a `loadtest/results/` (versionado después, en el commit de `loadtest/`): 1 worker 15.8 req/s y P95 2.2 s a 25 usuarios; 4 workers 40.5 req/s y P95 1.1 s. **SUS y panel: 0 respuestas** (`06_entorno/human_eval_status.json`).
- Sin MP3, cachés, binarios, secretos ni datos de estudiantes. Duplicados por contenido: 24 CSV de carga (12 `*_failures.csv` y 12 `*_exceptions.csv`, solo con cabecera), conservados como salida de Locust.

## Redacción de rutas personales (única modificación posterior a la generación)
Se sustituyó el prefijo del directorio personal del usuario (`/home/<usuario>` o `/var/home/<usuario>`) por `<HOME>` en 4 copias y se actualizaron **solo** sus 4 líneas de `MANIFEST.sha256`. Los originales de `Auditoria Tesis/` no se tocaron.

| archivo del paquete | sha256 original | sha256 redactado |
|---|---|---|
| `07_biblioteca/sealed_copy/sealed_copy.json` | `73277c40925dcb125d343ade46bb542988ccfaa42ee0e379c8e030b2e39779b5` | `1d5129e86bcf4e1a34246a2b4d97aab7f5dfce6efdbaabd6ae60dba1d968a26b` |
| `03_informes/IMPLEMENTATION-PHASE1-REPORT-2026-09-23.md` | `4a487000407c4bd1513757fef6ad5109b276a673d170385bc6e2a773d9d41eb9` | `43a854fa287fe11e4274a4e965cdd6d53b413ef54e75a147827ca33d3496b44f` |
| `03_informes/PRE-COMMIT-PRE-DEDUPE-AUDIT-2026-09-24.md` | `4db93beccf8a16b463bf04df1f4829dbbeaffda053036ab0cc9ad88885d06003` | `586103ebeaef2276d43b73ccd77fcb8704694e52f0a4f85669debc40a91cf55e` |
| `03_informes/IMPLEMENTATION-PHASE3E-REPORT-2026-09-24.md` | `c1cda1cf572a04519702695b021d06c9877d207e1235080c3acb2db0b674a713` | `e123f6bc05094b1ca62aab31693c13635a341a41e3d9dd951aabf5435dc5b1a1` |

`build_evidence_package` ya no lleva una ruta personal fija; un paquete futuro con `--sealed-copy` volvería a escribir la ruta local de la copia sellada en `sealed_copy.json` (redactarla antes de versionar).

## Qué copias internas quedaron superadas por el estado actual de Git
Son instantáneas de la generación: el paquete no se reescribe, y esta lista es la que manda.
- `05_documentacion/REPRODUCIBILITY.md` y `05_documentacion/README.md`: dicen que la biblioteca y las migraciones «aún no están versionadas» y «130+ pruebas». Hoy la biblioteca (`3a93f2b`) y las cuatro migraciones están en Git; las versiones vigentes son `backend/adaptation_swarm/REPRODUCIBILITY.md` y `README.md`.
- `README_EVIDENCE_INDEX.md`: igual que `backend/adaptation_swarm/EVIDENCE_INDEX.md` salvo el aviso de estado en Git y la línea de sensibilidad que este último añadió después; sin contradicciones.
- `03_informes/GIT-COMMIT-PLAN-2026-09-24.md` (plan «NO EJECUTADO», rama `feat/pretest-m1-v4`), `GIT-CLASSIFICATION-2026-09-23-fase2.md` y `PRE-COMMIT-PRE-DEDUPE-AUDIT-2026-09-24.md`: informes de proceso históricos. Lo ejecutado en `feat/adaptation-swarm-poc`: `ad97675`, `2e3bf02`, `0961b58`, `dee4f5c`, `3a93f2b`, `1079039`, `311d846`, `7279c82`, `10995c6`, `367cd8c`, `dafbae0`.
- `LIBRARY_TESTS.md` y `ADR-0019.md`: idénticos a los versionados.

Las corridas siguen registrando `git.dirty = true` sobre `d31d29c`: los resultados se **verifican** (recalculando desde los datos guardados), pero no se reproducen desde ese commit por sí solo.
