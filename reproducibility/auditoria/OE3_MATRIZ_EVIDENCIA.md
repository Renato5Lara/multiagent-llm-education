# OE3 — matriz de evidencia y estado

**OE3 (literal):** «Determinar el efecto de la configuración de los roles de los agentes, los protocolos de comunicación y los mecanismos de inteligencia de enjambre sobre el tiempo de convergencia y la eficiencia de la adaptación de contenidos multimodales.»
Meta asociada: modelo de 5 agentes con PSO discreto; CR ≥ 98 %. El OE3 **no tiene hipótesis estadística formulada** en la tesis.

**Estado: ABIERTO (evidencia parcial pero sólida para los efectos sobre T_conv y la brecha; faltan un índice de eficiencia aprobado y la ejecución oficial).** No se declara cumplido.

## Campañas
| | N3 | N3-R (nueva, 2026-10-19) |
|---|---|---|
| Diseño | factorial completo 2×2×2×2×3 = 48 condiciones × 5 lotes × 100 perfiles = 24 000 observaciones | **idéntico**; semillas nuevas (`batch_seed` 26101901), orden por bloques aleatorizados, `--seed-per-batch`, N = 20, 1 usuario, calentamiento 10 |
| Ejecución | 2026-10-06, commit `cec0e06` | 2026-10-19, commit `265a4f4`, mismo equipo, Redis aislado (puerto 56379) |
| Resultado | 240 corridas, 0 fallos | 240 corridas, 0 fallos (24 000 ok) |
| Cadena observaciones→corridas | recalculada, dif. máx. 1,4·10⁻¹⁴ | recalculada, dif. máx. 7,1·10⁻¹⁵ |
| Estatus | exploratoria, no oficial | **exploratoria, no oficial**; no se combina con N3 en ningún cuadro de la tesis |

## Componentes del objetivo
| Componente | Operacionalización en el estudio | Evidencia | Resultado | Falta |
|---|---|---|---|---|
| Roles de los agentes | heurística de arranque (AG1) y réplicas de consumidores | N3, N3-R | heurística: T_conv ×0,94 (5/5 lotes en ambas campañas), brecha −0,011, `k_stop` menor; réplicas: efecto mínimo (×0,99; 4/5 lotes) | no hay una definición independiente de «rol»; la operacionalización es la del propio estudio |
| Protocolos de comunicación | despacho por lotes/secuencial; difusión de `g_best` | N3, N3-R | despacho secuencial ×1,60 (N3) y ×1,47 (N3-R) sobre T_conv, sin cambio de solución; difusión ×1,20 (≈ 13 ms y ≈ 11 mensajes) sin mejora de calidad | la magnitud del efecto del despacho varía entre campañas (1,60 frente a 1,47): sensible al régimen del equipo |
| Mecanismos de enjambre | PSO, social, cognitivo | N3, N3-R | cognitivo ≈ 17 % más rápido (razón 1,21 de PSO frente a cognitivo) pero con brecha más del doble (0,032 frente a 0,0143); PSO ≈ social (×0,998; 3/5 lotes) | el menor T_conv del cognitivo es búsqueda truncada, no eficiencia |
| Tiempo de convergencia | `T_conv` (ms) | N3, N3-R | efectos replican en 21 de 21 contrastes evaluados | `T_conv` es una medición exploratoria, no TTFC |
| Eficiencia de la adaptación | brecha respecto del óptimo, `k_stop`, mensajes | N3, N3-R | brecha y `k_stop` replican casi exactamente | **no existe un índice de eficiencia aprobado**; crearlo aquí sería inventar un criterio |
| Efecto por factor e interacciones | ANOVA tipo III con permutación (999) | Tabla 13/14 (N3); `oe3_robustez.py`, `oe3_replicacion.py` | interacciones significativas (p. ej. despacho × difusión, heurística × mecanismo) en N3 y N3-R | el ANOVA de N3-R no se incorporó a ninguna tabla de la tesis |
| Robustez | consistencia entre lotes, leave-one-batch-out, pruebas por rangos con Holm (las «candidatas» del plan, ejecutadas como análisis exploratorio) | `outputs/oe3_robustez*.json`, `tables/oe3_robustez*` | despacho, difusión, heurística y mecanismo: mismo signo en 5/5 lotes y significativos con Holm; réplicas: significativo en rangos pareados pero de magnitud ≈ 1 % | semillas y lotes sí replican; equipo único |

## Qué NO está demostrado
- Causalidad fuera del modelo en proceso (sin HTTP, N = 20, 1 usuario, un solo equipo).
- Comportamiento con más carga o más tamaño de enjambre (eso es el OE4).
- Cumplimiento de la meta CR ≥ 98 %: la Tabla 15 es el resultado **histórico v2** (K10), no de N3.
- Eficiencia en sentido agregado (índice aprobado inexistente).

## Para cerrar el OE3
1. Aprobar (asesor/autor) una definición de eficiencia y su regla de decisión; después recalcularla desde `runs_oe3.csv` y `runs_oe3.csv` de N3-R.
2. Ejecución oficial (condiciones objetivo y ≥ 10 réplicas por condición, como recomienda la propia tesis): no es posible en este equipo.
3. Decidir si el resultado de N3-R se incorpora a la tesis (nuevo cuadro de réplica); el DOCX **no** se modificó.
