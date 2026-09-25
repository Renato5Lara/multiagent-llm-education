# Corridas congeladas de la PoC `adaptation_swarm` (`corrida-poc-1` y `corrida-poc-2`)

Resultados de los 100 casos sintéticos (unidad de análisis: caso = perfil × concepto) con la configuración cerrada de DECISION-CLOSURE.
**No se editan ni se re-ejecutan sobre el mismo `run_label`.** Los hashes de abajo son la fuente de verdad: si un archivo cambia, `tests/adaptation_swarm/test_frozen_runs_preserved.py` falla.

Verificación, sin PostgreSQL, Redis, audio ni red (desde `backend/`):

    python -m pytest tests/adaptation_swarm/test_frozen_runs_preserved.py
    python -m adaptation_swarm.analysis.compare_runs corrida-poc-1 corrida-poc-2

## Lo que estos resultados NO permiten afirmar
- **F1_adapt = 0.8031 (IC95 0.711–0.877) queda por debajo del objetivo de la asesoría (≥ 0.85).** No se declara cumplimiento. Con la definición cerrada no se ajustaron pesos, gold ni regla de parada para modificarlo.
- Ambas corridas se ejecutaron con el commit `d31d29c` de la rama `feat/pretest-m1-v4` y el **árbol de trabajo sucio** (`dirty: true`): los resultados se **verifican** recalculando desde los datos guardados, pero no se reproducen desde ese commit por sí solo. Volver a ejecutar ciclos exige Redis, la biblioteca con audio y SVG, y `run_experiment.py`.
- La latencia de ciclo guardada es en proceso, sin HTTP: no mide L_resp ni el throughput de la asesoría.
- `poc-1` usa `lib-v5` y `poc-2` usa `lib-v9`; la única variable que difiere es la versión de biblioteca. La etiqueta predicha no cambió en ningún caso.
- `*_f1_audit.json` y `*_pso_audit.json` se generaron con `analysis/f1_audit.py` y `analysis/pso_audit.py`, que leen PostgreSQL (`swarm_cycles`, `swarm_iterations`); esos generadores no están en este commit. Sus resultados se comprueban contra los JSON de corrida. `poc-2` no tiene auditoría PSO aparte: su diagnóstico va en `summary.pso_diagnostics`.

## Manifiesto (semilla, versiones, configuración PSO, métricas y hashes)

```json
{
  "schema": "frozen-runs-v1",
  "spec_version": "2026-09-23",
  "batch_seed": 20260923,
  "dataset": {
    "version": "v1",
    "profiles_file": "datasets/synthetic_profiles/profiles-v1.jsonl",
    "profiles_sha256": "005b5a82ae85b4e83e1b9a931578fd60e9c6789a6e407928fdba6674fc1ccd15",
    "gold_file": "datasets/synthetic_profiles/gold-v1.jsonl",
    "gold_sha256": "3bc437678e71e94e58540c3406d3323e1d1383ea26828e3f6a6b2c65d66df288",
    "gold_rule_version": "gold-v1",
    "n_cases": 100
  },
  "pso": {
    "n_particles": 20,
    "w": 0.729,
    "c1": 1.494,
    "c2": 1.494,
    "v_max": 1.0,
    "k_max": 15,
    "epsilon": 0.001,
    "init_low": 0.0,
    "init_high": 2.0
  },
  "fitness_weights": {
    "alpha": 0.4,
    "beta": 0.3,
    "gamma": 0.15,
    "delta": 0.15
  },
  "f1_target_asesoria": 0.85,
  "runs": {
    "corrida-poc-1": {
      "library_version": "lib-v5-9ae9ffdd",
      "library_manifest": "datasets/adaptation_library/lib-v5-9ae9ffdd/manifest.json",
      "library_manifest_sha256": "60526cd8c2af1d9008c7ad17a2ce1cd7fc1e234165fe8ae31b22112cfe592d8d",
      "executed_with": {
        "commit": "d31d29c819151239e932c1d3c28e56dd364507d0",
        "branch": "feat/pretest-m1-v4",
        "dirty": true
      },
      "metrics": {
        "n": 100,
        "completed": 100,
        "f1_adapt": 0.8031415252818244,
        "f1_ci95_bootstrap": [
          0.711409200194325,
          0.8766285036613435
        ],
        "macro_f1_all4": 0.6023561439613683,
        "accuracy": 0.81,
        "CR": 1.0,
        "k_stop_mean": 1.65,
        "k_stop_max": 4,
        "mean_gap_to_global_optimum": 0.006752578960547307
      },
      "f1_target_met": false,
      "artifacts": {
        "adaptation_swarm_corrida-poc-1.json": "7e1037f1f7e2522868bb62076a104f4bcb9c7346128b76d71f0c5e6aa8d7bd6a",
        "adaptation_swarm_corrida-poc-1_cases.csv": "3bcf9dd3998d713c7fd03f302c27ffcae2115173f36f455510f8f8ed43f82428",
        "adaptation_swarm_corrida-poc-1_f1_audit.json": "008885f0ecebac5400005d281bad5ecea53de077015de97cbd2a5418266b0aea",
        "adaptation_swarm_corrida-poc-1_pso_audit.json": "f0730e6da5f5b8a688efabd6661291b645b5330b9c144284714a64bd8ee290c5"
      }
    },
    "corrida-poc-2": {
      "library_version": "lib-v9-a0231e9b",
      "library_manifest": "datasets/adaptation_library/lib-v9-a0231e9b/manifest.json",
      "library_manifest_sha256": "08436553d3c010c4ad38eee1079c85e631ba3605ec2a598b63352b850ab44156",
      "executed_with": {
        "commit": "d31d29c819151239e932c1d3c28e56dd364507d0",
        "branch": "feat/pretest-m1-v4",
        "dirty": true
      },
      "metrics": {
        "n": 100,
        "completed": 100,
        "f1_adapt": 0.8031415252818244,
        "f1_ci95_bootstrap": [
          0.711409200194325,
          0.8766285036613435
        ],
        "macro_f1_all4": 0.6023561439613683,
        "accuracy": 0.81,
        "CR": 1.0,
        "k_stop_mean": 1.79,
        "k_stop_max": 5,
        "mean_gap_to_global_optimum": 0.013608115254933566
      },
      "f1_target_met": false,
      "artifacts": {
        "adaptation_swarm_corrida-poc-2.json": "a2c67f91e1fc580953c9cd67c3433691039e2e7e7130e141321bfb56870ce6cb",
        "adaptation_swarm_corrida-poc-2_cases.csv": "b17c5d478603df838e0df79b3f78b4031c861d351b8badd804c02be60fe6ce59",
        "adaptation_swarm_corrida-poc-2_f1_audit.json": "6b31a898e95a9effe41286e022b72a4e1392c3b216958da7979933d4876c382b"
      }
    }
  }
}
```
