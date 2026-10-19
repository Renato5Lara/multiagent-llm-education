# OE3 — ejecución N3 (2026-10-06) — resultado

**Naturaleza:** ejecución EXPERIMENTAL no oficial (`environment_class = TECHNICALLY_COMPATIBLE_P6_PENDING`); commit `cec0e06`; sin cambios de código. Estado PENDING de `statistical_unit_performance` y de la definición de eficiencia (aprobada solo como T_conv; PARTIAL): la unidad usada es la corrida (decisión de este análisis, no aprobada por el asesor).

## Diseño
Factorial completo 2×2×2×2×3 = 48 condiciones, carga 1 usuario, N = 20 partículas; 5 lotes con semilla propia (`--seed-per-batch`), 100 perfiles, K = 1, orden aleatorizado por bloques → 240 corridas (condición × lote), 24 000 ciclos, sin errores. Comando: `runner oe3 --design full --batches 5 --k 1 --concurrency 1 --seed-per-batch --order randomized-blocks`.

| Dimensión de OE3 | Factor (real en la arquitectura) | Niveles |
|---|---|---|
| Roles de los agentes | `heuristic_seed` (rol de AG1 en el arranque) | con / sin |
| | `replicas` (consumidores por agente) | 1 / 2 |
| Protocolo de comunicación | `dispatch` | batch / sequential |
| | `broadcast_gbest` | con / sin |
| Mecanismo de enjambre | `mechanism` | pso / cognitive / social |

Respuestas: tiempo de convergencia (`t_conv_ms`, log; `k_stop`) y eficiencia de adaptación (brecha frente al óptimo, 𝓕 final y mensajes). Análisis: ANOVA factorial por corrida con interacciones (`oe/factorial.py`); residuos no normales ⇒ p por permutación (999; el p mínimo posible es 0,001).

## Efectos (marginales)
| Factor | T_conv (ms) | k_stop | brecha vs óptimo | mensajes |
|---|---|---|---|---|
| dispatch: batch / sequential | **56,8 / 90,6** (p = 0,001; η² = 0,98) | 1,71 / 1,71 (sin efecto) | sin efecto | sin efecto |
| broadcast_gbest: no / sí | **65,5 / 78,5** (p = 0,001; η² = 0,88) | sin efecto | sin efecto | 47,2 / 58,0 |
| heuristic_seed: sí / no | 69,4 / 74,1 (p = 0,001; η² = 0,50) | **1,51 / 1,91** | **0,0150 / 0,0258** | 51,7 / 53,5 |
| replicas: 1 / 2 | 72,2 / 71,3 (p = 0,015; η² = 0,03; efecto mínimo) | sin efecto | sin efecto | sin efecto |
| mechanism: pso / social / cognitive | 76,5 / 76,3 / **63,3** (p = 0,001) | 2,08 / 2,05 / **1,00** | 0,0143 / 0,0147 / **0,0320** | 54,0 / 53,9 / 49,9 |

Interacciones significativas: `heuristic_seed × mechanism` (T_conv, k_stop, brecha), `dispatch × broadcast`, `dispatch × mechanism`, `broadcast × mechanism` (T_conv), y de mensajes. Con interacción, los efectos principales se leen de forma condicional (`anova_oe3.md`).

## Lectura por factor (qué cambia y qué no)
- **Protocolo (dispatch):** el despacho `sequential` aumenta T_conv ≈ 60 % sin cambiar la solución ni el número de iteraciones: es puro costo de tiempo. El despacho concurrente (`batch`) es mejor.
- **Protocolo (broadcast_gbest):** difundir el mejor global añade ≈ 11 mensajes por ciclo y ≈ 13 ms de T_conv **sin mejorar k_stop ni la calidad** de la solución.
- **Roles (heuristic_seed):** la partícula heurística inicial reduce k_stop (1,5 vs 1,9) y la brecha (0,015 vs 0,026), con T_conv algo menor. Es el único factor de roles con efecto de calidad.
- **Roles (replicas):** doblar consumidores no cambia la solución ni k_stop y solo desplaza T_conv ~1 ms (η² = 0,03). Efecto prácticamente nulo.
- **Mecanismo:** `cognitive` (sin información social) converge en 1 iteración y es el más rápido (63 ms), pero con la peor calidad (brecha 0,032, el doble). `pso` y `social` son equivalentes en calidad (0,0143 vs 0,0147) y en tiempo.

## Mejor y peor configuración
- **Referencia del proyecto** (batch, broadcast sí, h1, pso, 1 réplica): T_conv 65,5 ms, k_stop 1,76, brecha 0,0118.
- **Más rápida:** batch · sin broadcast · h1 · `cognitive` · 1 réplica: 43,7 ms (k_stop 1,0) pero brecha 0,0212 (≈ 80 % peor que la referencia).
- **Mejor compromiso tiempo/calidad:** batch · sin broadcast · h1 · `pso` (o `social`) · 1 réplica: 51,8 ms con la **misma calidad que la referencia** (brecha 0,0118; k_stop 1,76; 47,2 mensajes). Es ≈ 21 % más rápida que la referencia.
- **Mayor calidad (menor brecha 0,0118):** las configuraciones con h1 y `pso`, con o sin broadcast; entre ellas la sin broadcast es más rápida.
- **Más lenta:** sequential · broadcast sí · h0 · `social`/`pso`: ≈ 106–109 ms (k_stop ≈ 2,4).
- **Peor calidad:** h0 · `cognitive` (brecha 0,0428, 𝓕 0,450) en cualquier despacho.

## Conclusión específica de OE3
La configuración interna del enjambre sí modifica el tiempo de convergencia y la eficiencia de la adaptación, con efectos grandes en el protocolo y el mecanismo, moderado en la heurística de arranque y mínimo en las réplicas:
1. **Roles:** la heurística de arranque importa (menos iteraciones, mejor solución); duplicar consumidores no.
2. **Protocolo:** el despacho concurrente reduce T_conv ≈ 37 %; la difusión de g_best cuesta tiempo y mensajes sin beneficio de calidad.
3. **Mecanismo:** quitar la componente social acelera la convergencia pero degrada la solución al doble de brecha; PSO completo y la variante social puramente son equivalentes.
La configuración de referencia del proyecto no es la mejor de las 48: prescindir de la difusión de g_best conserva la calidad y acorta T_conv alrededor de una quinta parte.

## Limitaciones
- 5 corridas por condición (la corrida agrega 100 perfiles); p por permutación con piso en 0,001; muchas interacciones significativas.
- Todo a 1 usuario, N = 20 y un solo hardware; sin HTTP. No se varió N (OE4) ni la carga.
- El tamaño de efecto de T_conv puede inflarse porque el tiempo en proceso tiene varianza muy baja entre corridas (DE ≈ 2 ms).
- La brecha frente al óptimo y 𝓕 son la misma señal (𝓕 final); la eficiencia usa además T_conv y mensajes. Sin F1 externo.
- Decisión interna: la unidad estadística es la corrida; la definición de eficiencia (solo T_conv aprobada) está PARTIAL.

## Archivos
`run/` (observaciones, lotes, provenance, checksums, logs), `runs_oe3.csv`, `tabla_por_configuracion.csv`, `anova_oe3.{json,md}`, `oe3_efectos_marginales.png`, `analyze_oe3.py`, `SHA256SUMS`.
