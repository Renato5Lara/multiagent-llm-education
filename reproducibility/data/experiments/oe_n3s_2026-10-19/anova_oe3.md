# OE3 — efectos principales (ANOVA factorial por corrida; término → p; η² parcial)

## t_conv_ms (n = 240 corridas, log; inferencia: F; residuos normales: True)

| término | p | η² parcial | significativo |
|---|---|---|---|
| f_dispatch | 1.36e-211 | 0.993 | sí |
| f_mechanism | 4.38e-146 | 0.969 | sí |
| f_broadcast_gbest | 2.26e-145 | 0.968 | sí |
| f_heuristic_seed | 8.49e-69 | 0.799 | sí |
| f_heuristic_seed:f_mechanism | 1.78e-34 | 0.555 | sí |
| f_dispatch:f_broadcast_gbest | 2.46e-34 | 0.541 | sí |
| f_dispatch:f_mechanism | 4.07e-30 | 0.506 | sí |
| f_broadcast_gbest:f_mechanism | 1.03e-08 | 0.174 | sí |
| f_replicas | 0.000153 | 0.072 | sí |
| f_heuristic_seed:f_dispatch | 0.00124 | 0.053 | sí |
| f_heuristic_seed:f_dispatch:f_mechanism | 0.00352 | 0.057 | sí |
| f_heuristic_seed:f_broadcast_gbest | 0.00651 | 0.038 | sí |

- f_heuristic_seed: False = 62.24, True = 58.4
- f_replicas: 1 = 60.56, 2 = 60.02
- f_dispatch: batch = 49.54, sequential = 73.38
- f_broadcast_gbest: False = 55.23, True = 65.82
- f_mechanism: cognitive = 53.1, pso = 64.36, social = 64.13

## k_stop (n = 240 corridas, escala original; inferencia: permutation (Freedman–Lane); residuos normales: False)

| término | p | η² parcial | significativo |
|---|---|---|---|
| f_heuristic_seed | 0.001 | 0.847 | sí |
| f_mechanism | 0.001 | 0.971 | sí |
| f_heuristic_seed:f_mechanism | 0.001 | 0.736 | sí |
| f_replicas | 1 | 0.000 | no |
| f_dispatch | 1 | 0.000 | no |
| f_broadcast_gbest | 1 | 0.000 | no |

- f_heuristic_seed: False = 1.912, True = 1.505
- f_replicas: 1 = 1.708, 2 = 1.708
- f_dispatch: batch = 1.708, sequential = 1.708
- f_broadcast_gbest: False = 1.708, True = 1.708
- f_mechanism: cognitive = 1, pso = 2.08, social = 2.045

## gap_vs_optimum (n = 240 corridas, escala original; inferencia: permutation (Freedman–Lane); residuos normales: False)

| término | p | η² parcial | significativo |
|---|---|---|---|
| f_heuristic_seed | 0.001 | 0.939 | sí |
| f_mechanism | 0.001 | 0.973 | sí |
| f_heuristic_seed:f_mechanism | 0.001 | 0.886 | sí |
| f_replicas | 1 | 0.000 | no |
| f_dispatch | 1 | 0.000 | no |
| f_broadcast_gbest | 1 | 0.000 | no |

- f_heuristic_seed: False = 0.02576, True = 0.01496
- f_replicas: 1 = 0.02036, 2 = 0.02036
- f_dispatch: batch = 0.02036, sequential = 0.02036
- f_broadcast_gbest: False = 0.02036, True = 0.02036
- f_mechanism: cognitive = 0.03202, pso = 0.01434, social = 0.01472

## n_messages (n = 240 corridas, escala original; inferencia: permutation (Freedman–Lane); residuos normales: False)

| término | p | η² parcial | significativo |
|---|---|---|---|
| f_heuristic_seed | 0.001 | 0.694 | sí |
| f_broadcast_gbest | 0.001 | 0.988 | sí |
| f_mechanism | 0.001 | 0.915 | sí |
| f_heuristic_seed:f_broadcast_gbest | 0.001 | 0.322 | sí |
| f_heuristic_seed:f_mechanism | 0.001 | 0.351 | sí |
| f_broadcast_gbest:f_mechanism | 0.001 | 0.742 | sí |
| f_heuristic_seed:f_broadcast_gbest:f_mechanism | 0.001 | 0.193 | sí |
| f_replicas | 1 | 0.000 | no |
| f_dispatch | 1 | 0.000 | no |

- f_heuristic_seed: False = 53.49, True = 51.71
- f_replicas: 1 = 52.6, 2 = 52.6
- f_dispatch: batch = 52.6, sequential = 52.6
- f_broadcast_gbest: False = 47.18, True = 58.02
- f_mechanism: cognitive = 49.86, pso = 54, social = 53.93

## F (n = 240 corridas, escala original; inferencia: permutation (Freedman–Lane); residuos normales: False)

| término | p | η² parcial | significativo |
|---|---|---|---|
| f_heuristic_seed | 0.001 | 0.939 | sí |
| f_mechanism | 0.001 | 0.973 | sí |
| f_heuristic_seed:f_mechanism | 0.001 | 0.886 | sí |
| f_replicas | 1 | 0.000 | no |
| f_dispatch | 1 | 0.000 | no |
| f_broadcast_gbest | 1 | 0.000 | no |

- f_heuristic_seed: False = 0.4674, True = 0.4782
- f_replicas: 1 = 0.4728, 2 = 0.4728
- f_dispatch: batch = 0.4728, sequential = 0.4728
- f_broadcast_gbest: False = 0.4728, True = 0.4728
- f_mechanism: cognitive = 0.4611, pso = 0.4788, social = 0.4784
