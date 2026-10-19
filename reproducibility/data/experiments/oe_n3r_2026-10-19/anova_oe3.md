# OE3 — efectos principales (ANOVA factorial por corrida; término → p; η² parcial)

## t_conv_ms (n = 240 corridas, log; inferencia: permutation (Freedman–Lane); residuos normales: False)

| término | p | η² parcial | significativo |
|---|---|---|---|
| f_heuristic_seed | 0.001 | 0.716 | sí |
| f_dispatch | 0.001 | 0.991 | sí |
| f_broadcast_gbest | 0.001 | 0.957 | sí |
| f_mechanism | 0.001 | 0.960 | sí |
| f_heuristic_seed:f_mechanism | 0.001 | 0.432 | sí |
| f_dispatch:f_broadcast_gbest | 0.001 | 0.483 | sí |
| f_dispatch:f_mechanism | 0.001 | 0.472 | sí |
| f_broadcast_gbest:f_mechanism | 0.001 | 0.186 | sí |
| f_heuristic_seed:f_dispatch | 0.004 | 0.048 | sí |
| f_heuristic_seed:f_broadcast_gbest | 0.017 | 0.031 | sí |
| f_heuristic_seed:f_dispatch:f_mechanism | 0.028 | 0.038 | sí |
| f_replicas | 0.116 | 0.015 | no |

- f_heuristic_seed: False = 62.2, True = 58.59
- f_replicas: 1 = 60.51, 2 = 60.23
- f_dispatch: batch = 49.73, sequential = 73.29
- f_broadcast_gbest: False = 55.22, True = 65.99
- f_mechanism: cognitive = 52.94, pso = 64.48, social = 64.45

## k_stop (n = 240 corridas, escala original; inferencia: permutation (Freedman–Lane); residuos normales: False)

| término | p | η² parcial | significativo |
|---|---|---|---|
| f_heuristic_seed | 0.001 | 0.893 | sí |
| f_mechanism | 0.001 | 0.983 | sí |
| f_heuristic_seed:f_mechanism | 0.001 | 0.808 | sí |
| f_replicas | 1 | 0.000 | no |
| f_dispatch | 1 | 0.000 | no |
| f_broadcast_gbest | 1 | 0.000 | no |

- f_heuristic_seed: False = 1.912, True = 1.528
- f_replicas: 1 = 1.72, 2 = 1.72
- f_dispatch: batch = 1.72, sequential = 1.72
- f_broadcast_gbest: False = 1.72, True = 1.72
- f_mechanism: cognitive = 1, pso = 2.094, social = 2.066

## gap_vs_optimum (n = 240 corridas, escala original; inferencia: permutation (Freedman–Lane); residuos normales: False)

| término | p | η² parcial | significativo |
|---|---|---|---|
| f_heuristic_seed | 0.001 | 0.970 | sí |
| f_mechanism | 0.001 | 0.986 | sí |
| f_heuristic_seed:f_mechanism | 0.001 | 0.935 | sí |
| f_replicas | 1 | 0.000 | no |
| f_dispatch | 1 | -0.000 | no |
| f_broadcast_gbest | 1 | 0.000 | no |

- f_heuristic_seed: False = 0.0261, True = 0.01495
- f_replicas: 1 = 0.02053, 2 = 0.02053
- f_dispatch: batch = 0.02053, sequential = 0.02053
- f_broadcast_gbest: False = 0.02053, True = 0.02053
- f_mechanism: cognitive = 0.03227, pso = 0.01447, social = 0.01483

## n_messages (n = 240 corridas, escala original; inferencia: permutation (Freedman–Lane); residuos normales: False)

| término | p | η² parcial | significativo |
|---|---|---|---|
| f_heuristic_seed | 0.001 | 0.741 | sí |
| f_broadcast_gbest | 0.001 | 0.994 | sí |
| f_mechanism | 0.001 | 0.957 | sí |
| f_heuristic_seed:f_broadcast_gbest | 0.001 | 0.451 | sí |
| f_heuristic_seed:f_mechanism | 0.001 | 0.384 | sí |
| f_broadcast_gbest:f_mechanism | 0.001 | 0.852 | sí |
| f_heuristic_seed:f_broadcast_gbest:f_mechanism | 0.001 | 0.293 | sí |
| f_replicas | 1 | 0.000 | no |
| f_dispatch | 1 | 0.000 | no |

- f_heuristic_seed: False = 53.55, True = 52.12
- f_replicas: 1 = 52.84, 2 = 52.84
- f_dispatch: batch = 52.84, sequential = 52.84
- f_broadcast_gbest: False = 47.4, True = 58.28
- f_mechanism: cognitive = 50, pso = 54.27, social = 54.24

## F (n = 240 corridas, escala original; inferencia: permutation (Freedman–Lane); residuos normales: False)

| término | p | η² parcial | significativo |
|---|---|---|---|
| f_heuristic_seed | 0.001 | 0.970 | sí |
| f_mechanism | 0.001 | 0.986 | sí |
| f_heuristic_seed:f_mechanism | 0.001 | 0.935 | sí |
| f_replicas | 1 | -0.000 | no |
| f_dispatch | 1 | -0.000 | no |
| f_broadcast_gbest | 1 | -0.000 | no |

- f_heuristic_seed: False = 0.4671, True = 0.4782
- f_replicas: 1 = 0.4726, 2 = 0.4726
- f_dispatch: batch = 0.4726, sequential = 0.4726
- f_broadcast_gbest: False = 0.4726, True = 0.4726
- f_mechanism: cognitive = 0.4609, pso = 0.4787, social = 0.4783
