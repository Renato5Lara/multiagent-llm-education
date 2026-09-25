# Análisis de sensibilidad del PSO (`adaptation_swarm_sensitivity.json`)

Barrido pre-registrado de DECISION-CLOSURE §6.2 y DEC-08: **α ∈ {0.3, 0.4, 0.5}** (β, γ, δ reescalados proporcionalmente para conservar α+β+γ+δ = 1) y **N ∈ {10, 20, 30}** partículas, con el resto de parámetros PSO y la semilla de la corrida principal. Cada configuración procesa los mismos 100 casos sintéticos sobre `lib-v5-9ae9ffdd`.

**Es evidencia complementaria, no una corrida principal.** No modifica ni sustituye `corrida-poc-1` ni `corrida-poc-2` (ver `adaptation_swarm_frozen_runs.md`):
- Las entradas de referencia (`alpha=0.4(ref)` y `N=20(ref)`) coinciden con `corrida-poc-1`: F1_adapt = 0.8031, CR = 1.00, k_stop medio 1.65 y misma distribución de etiquetas.
- **F1_adapt de la corrida principal sigue siendo 0.8031 y no alcanza el objetivo 0.85 de la asesoría.** Ninguna de las 6 configuraciones lo alcanza (máximo 0.8164, con α = 0.3). Esas variaciones no se adoptan: la configuración de referencia (0.40 / 0.30 / 0.15 / 0.15, N = 20) no cambia, y un cambio requeriría una decisión formal nueva, que se reportaría como post-hoc.
- Lo que se observa es estabilidad: la concordancia de las etiquetas predichas con la referencia es 0.99–1.00 y CR = 1.00 en todas.

Limitaciones que no se ocultan:
- Se ejecutó con el commit `d31d29c` de la rama `feat/pretest-m1-v4` y el árbol de trabajo sucio (`dirty: true`), y solo sobre `lib-v5`.
- El orden respecto de la corrida principal (DECISION-CLOSURE pide el barrido antes de los 100 casos definitivos) solo se apoya en las marcas de tiempo de los archivos (sensibilidad 20:28:25, `corrida-poc-1` 20:28:47 del 2026-09-23), que no son una prueba criptográfica.
- El archivo guarda solo métricas agregadas por configuración; no guarda los casos individuales.

Verificación, sin PostgreSQL, Redis, audio ni red (desde `backend/`):

    python -m pytest tests/adaptation_swarm/test_sensitivity_preserved.py

Las pruebas comprueban el hash, la estructura, los parámetros evaluados y la coherencia interna, y **re-ejecutan en proceso** el motor PSO versionado (sin bus) para cada configuración: los resultados guardados se reproducen exactamente.

## Manifiesto

```json
{
  "schema": "sensitivity-v1",
  "artifact": {
    "file": "backend/experiments/results/adaptation_swarm_sensitivity.json",
    "sha256": "d59ff801b331286e952509da95418f8aaf717b2549942c22a061dd307261c906"
  },
  "batch_seed": 20260923,
  "n_cases": 100,
  "library_version": "lib-v5-9ae9ffdd",
  "library_manifest_sha256": "60526cd8c2af1d9008c7ad17a2ce1cd7fc1e234165fe8ae31b22112cfe592d8d",
  "dataset": {
    "profiles_sha256": "005b5a82ae85b4e83e1b9a931578fd60e9c6789a6e407928fdba6674fc1ccd15",
    "gold_sha256": "3bc437678e71e94e58540c3406d3323e1d1383ea26828e3f6a6b2c65d66df288"
  },
  "grid": {
    "alpha": [0.3, 0.4, 0.5],
    "n_particles": [10, 20, 30],
    "entries": ["alpha=0.3", "alpha=0.4(ref)", "alpha=0.5", "N=10", "N=20(ref)", "N=30"]
  },
  "reference_entries_match_run": "corrida-poc-1",
  "is_main_run": false,
  "f1_target_asesoria": 0.85,
  "f1_max_over_grid": 0.8164434090467868,
  "f1_target_met_by_any_configuration": false,
  "executed_with": {
    "commit": "d31d29c819151239e932c1d3c28e56dd364507d0",
    "branch": "feat/pretest-m1-v4",
    "dirty": true
  }
}
```
