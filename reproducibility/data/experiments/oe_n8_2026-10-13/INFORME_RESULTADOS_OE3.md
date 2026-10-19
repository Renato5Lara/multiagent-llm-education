# INFORME DE RESULTADOS — OE3 (efecto de la configuración interna)

Fecha: 2026-10-13 · Ejecución analizada: campaña N3 (`oe_n3_2026-10-06/`), **experimental, no oficial** · Re-análisis independiente: `scripts/oe3_reanalysis.py` → `oe3_reanalysis/`.

## 1. Objetivo (sin modificar)
«Determinar el efecto de los roles de los agentes, los protocolos de comunicación y los mecanismos de inteligencia de enjambre sobre el tiempo de convergencia y la eficiencia de la adaptación multimodal.»

## 2. Diseño realmente ejecutado
Factorial **completo** 2×2×2×2×3 = 48 condiciones × 5 lotes = **240 corridas** (24 000 ciclos), 1 usuario, N = 20, 100 perfiles por lote. Unidad experimental = lote (cada fila de `runs_oe3.csv` resume 100 perfiles). Diseño balanceado verificado (48 celdas × 5).

| Factor | Niveles | Dimensión de OE3 |
|---|---|---|
| `heuristic_seed` | no / sí | rol (heurística de inicialización de AG1) |
| `replicas` | 1 / 2 | rol (réplicas de consumidores) |
| `dispatch` | batch / sequential | protocolo de comunicación |
| `broadcast_gbest` | no / sí | protocolo (difusión de información global) |
| `mechanism` | pso / social / cognitive | mecanismo de enjambre (c1, c2) |

Respuestas: `t_conv_ms` (tiempo de convergencia del algoritmo), `k_stop`, `gap_vs_optimum` (calidad frente a la búsqueda exhaustiva), `n_messages`, 𝓕. Nota: `gap_vs_optimum` y 𝓕 son función determinista una de otra (mismos estadísticos F y p); no son respuestas independientes.

## 3. Modelo estadístico y supuestos
ANOVA tipo II (OLS) con 5 efectos principales y las 10 interacciones de dos factores (gl residuales = 219). `t_conv` se analiza en escala log. Se reportan η² parcial y p con corrección de Holm dentro de cada respuesta (15 términos), y como comprobación robusta el ANOVA sobre rangos.

Diagnóstico de residuos (`oe3_reanalysis.json`): R² ≥ 0,977 en todas las respuestas. T_conv (log): Shapiro W = 0,979 (p = 0,0015; asimetría −0,02, curtosis −0,45): desviación leve. `k_stop` y brecha: no normales (W ≈ 0,83; curtosis exceso 2,3–2,8; `k_stop` además heterocedástico, Levene p = 1e-8) por ser discretas y tener dependencia con el mecanismo. **Las conclusiones de significación coinciden entre el ANOVA paramétrico y el de rangos** (la única diferencia: el efecto principal de réplicas sobre T_conv, Holm p = 0,058 paramétrico vs 0,049 en rangos, es un caso límite con η² parcial = 0,03, sin interés práctico). Se recomienda interpretar tamaños de efecto, no los p-valores (todos ≪ 1e-30 por efectos muy grandes con residuo mínimo).

## 4. Resultados (medias de 240 corridas; η² parcial del ANOVA)
| Factor | Nivel (n = corridas) | T_conv (ms) | k_stop | Brecha | Mensajes | η² parcial sobre T_conv |
|---|---|---|---|---|---|---|
| dispatch | batch (120) / sequential (120) | 57,5 / 91,2 | 1,71 / 1,71 | 0,0204 / 0,0204 | 52,6 / 52,6 | **0,979** |
| broadcast_gbest | no / sí | 68,0 / 80,8 | 1,71 / 1,71 | 0,0204 / 0,0204 | 47,2 / 58,0 | 0,874 |
| mechanism | pso / social / cognitive (80 c/u) | 78,8 / 78,7 / 65,7 | 2,08 / 2,05 / 1,00 | 0,0143 / 0,0147 / 0,0320 | 54,0 / 53,9 / 49,9 | 0,871 |
| heuristic_seed | no / sí | 76,9 / 71,8 | 1,91 / 1,50 | 0,0258 / 0,0150 | 53,5 / 51,7 | 0,483 |
| replicas | 1 / 2 | 74,9 / 73,9 | 1,71 / 1,71 | 0,0204 / 0,0204 | 52,6 / 52,6 | 0,031 (Holm p = 0,058) |

(El informe N3 original reporta batch 56,8 vs sequential 90,6 ms; el re-análisis desde `runs_oe3.csv` da 57,5 y 91,2. Diferencia ≤ 1,3 %, no explicada en el archivo de N3 —probablemente una agregación distinta—; no altera ninguna conclusión.)

**Interacciones** (T_conv, Holm p < 0,05): dispatch×broadcast (η² parcial 0,27), dispatch×mechanism (0,26), heuristic×mechanism (0,22), broadcast×mechanism (0,06). Por tanto los efectos principales **no son aditivos**: el costo de la difusión de g_best y el de cambiar de mecanismo dependen del despacho. (La afirmación previa de que las interacciones «no se estimaron» deja de ser válida para N3: se estiman aquí.)

## 5. Lectura sustantiva
1. **Protocolo.** El despacho concurrente reduce T_conv ≈ 37 % sin cambiar la solución (k_stop, brecha y 𝓕 idénticos entre dispatch). La difusión de g_best añade ≈ 13 ms y ≈ 11 mensajes sin mejorar k_stop ni brecha (η² ≈ 0 en ambas): en esta configuración y escala no aporta calidad.
2. **Roles.** La heurística de inicialización reduce iteraciones (1,91 → 1,50) y brecha (0,0258 → 0,0150), con un efecto pequeño en T_conv (≈ −5 ms). Las réplicas de consumidores prácticamente no actúan.
3. **Mecanismo.** `pso` y `social` son equivalentes (78,8 vs 78,7 ms; brecha 0,0143 vs 0,0147). `cognitive` es el más rápido (65,7 ms) pero con la brecha más del doble (0,0320). **Cautela:** con `cognitive` k_stop = 1 en el 100 % de los casos (DE = 0): el criterio de parada literal (Δ𝓕 < ε con k_stop = 1) detiene la búsqueda tras la primera iteración, de modo que su menor T_conv refleja una búsqueda truncada y no una convergencia más eficiente. Es decir, «más rápido» aquí es coherente con «peor solución».
4. **Eficiencia.** La configuración de referencia no es la mejor: sin difusión de g_best mantiene la calidad con menos T_conv (N3 informa ≈ 21 % para la configuración de referencia; el efecto marginal promedio recalculado es −16 %, 68,0 vs 80,8 ms). Las configuraciones más desfavorables combinan despacho secuencial, sin heurística y `cognitive`.

## 6. Qué se alcanzó y qué no
Se determinó el efecto de los tres grupos de factores sobre T_conv y sobre la eficiencia (brecha, mensajes) con tamaños de efecto e interacciones. Es resultado **experimental**, con 5 corridas por condición, un usuario, N = 20 y 100 perfiles sintéticos; no se generaliza a otras cargas o N. «Eficiencia de la adaptación» no tiene definición operacional aprobada (se reportan componentes, sin índice compuesto).

## 7. Limitaciones
Una sola máquina y sesión; 5 lotes por condición; las corridas no son réplicas independientes de perfiles (comparten el mismo conjunto de 100); respuesta discreta `k_stop` con residuos no normales (mitigado con ANOVA de rangos); sin variación de N ni de carga (ver OE4); decisión de la unidad estadística (lote) no aprobada por el asesor.

## 8. Reproducción
```
cd backend/experiments/oe_n8_2026-10-13
<python con pandas/statsmodels/scipy/matplotlib> scripts/oe3_reanalysis.py   # lee ../oe_n3_2026-10-06/runs_oe3.csv
# ejecución original: python -m adaptation_swarm.oe.runner oe3 --label ... (ver oe_n3_2026-10-06/run.log, commit cec0e06)
```
Salidas: `oe3_reanalysis/oe3_anova.csv`, `oe3_marginales.csv`, `oe3_medias_por_condicion.csv`, `oe3_reanalysis.json`, `oe3_efectos_marginales.png`. Entorno de análisis: Python 3.12, numpy/scipy 1.18, pandas 3.0, statsmodels 0.15, matplotlib 3.11 (`requirements_analisis.txt`).
