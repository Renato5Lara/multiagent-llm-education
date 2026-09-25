# Diagnóstico del PSO — corrida-poc-1 (solo lectura; no modifica nada)

Ciclos analizados: 100 · k_stop: media 1.65, mediana 1.0, máx 4

## Qué hace el enjambre
- g_best **nunca cambió después de la inicialización** en 48/100 ciclos.
- Iteración del primer cambio de g_best (k → nº de ciclos): {None: 48, 1: 52}
- Actualizaciones de g_best tras k=0: media 0.88 (máx 4).
- Actualizaciones de p_best tras k=0: media 25.6 por ciclo.
- Ciclos en los que la búsqueda mejoró 𝓕 respecto de la mejor partícula inicial: **52/100** (mejora media 0.0066, máx 0.0550).
- Partículas duplicadas (misma S decodificada): media 16.6%.

## Por iteración (promedio sobre ciclos que llegaron a esa iteración)

| k | S únicas | % duplicadas | 𝓕 distintas | σ(𝓕) | dist. media x (L2) | dist. media S (L1) |
|---|---|---|---|---|---|---|
| 0 | 19.9 | 0.5 | 19.8 | 0.0725 | 2.26 | 5.98 |
| 1 | 14.1 | 29.3 | 14.0 | 0.0397 | 1.25 | 2.48 |
| 2 | 15.6 | 21.9 | 15.6 | 0.0329 | 1.38 | 2.78 |
| 3 | 14.6 | 26.9 | 14.4 | 0.0269 | 1.54 | 2.55 |
| 4 | 13.2 | 33.8 | 13.0 | 0.0231 | 1.48 | 2.39 |

Lectura: 𝓕 es constante a tramos sobre S=φ(x) y la regla de parada literal `|ΔF|<ε` se cumple en cuanto una iteración no mejora g_best. No se modificó ninguna regla (DEC-10); cualquier cambio requeriría una decisión formal nueva.
