# OE3 — matriz de evidencia y estado

**OE3 (literal):** «Determinar el efecto de la configuración de los roles de los agentes, los protocolos de comunicación y los mecanismos de inteligencia de enjambre sobre el tiempo de convergencia y la eficiencia de la adaptación de contenidos multimodales.»
Meta asociada: modelo de 5 agentes con PSO discreto; CR ≥ 98 %. El OE3 **no tiene hipótesis estadística formulada** en la tesis.

**Estado: ABIERTO — efectos determinados y replicados en condiciones exploratorias (3 campañas, un solo equipo); no cumplido en sentido confirmatorio/oficial.** Falta la ejecución oficial (hardware objetivo, ≥ 10 réplicas) y una hipótesis estadística formulada. No se declara cumplido.

## Campañas
| | N3 | N3-R (nueva, 2026-10-19) |
|---|---|---|
| Diseño | factorial completo 2×2×2×2×3 = 48 condiciones × 5 lotes × 100 perfiles = 24 000 observaciones | **idéntico**; semillas nuevas (`batch_seed` 26101901), orden por bloques aleatorizados, `--seed-per-batch`, N = 20, 1 usuario, calentamiento 10 |
| Ejecución | 2026-10-06, commit `cec0e06` | 2026-10-19, commit `265a4f4`, mismo equipo, Redis aislado (puerto 56379) |
| Resultado | 240 corridas, 0 fallos | 240 corridas, 0 fallos (24 000 ok) |
| Cadena observaciones→corridas | recalculada, dif. máx. 1,4·10⁻¹⁴ | recalculada, dif. máx. 7,1·10⁻¹⁵ |
| Estatus | exploratoria, no oficial | **exploratoria, no oficial**; no se combina con N3 en ningún cuadro de la tesis |

**N3-S (control, 2026-10-19):** repite N3 con **las mismas semillas** (`batch_seed` 26093001), preregistrado antes de ejecutar (`PRE_REGISTRO_N3S.md`). Resultado: T_conv de N3-S ≈ N3-R (cociente 0,999) y ≈ 0,84 × N3 (IC95 0,82–0,86); brecha, `k_stop`, mensajes y F **idénticos a N3** (determinismo). Veredicto preregistrado: **H_sesión** — la diferencia de ≈ 16 % entre N3 y N3-R no depende de las semillas; la causa concreta (estado del equipo el 6 de octubre o versión del código) no es recuperable porque la carga de aquella sesión no se registró.

## Componentes del objetivo
| Componente | Operacionalización en el estudio | Evidencia | Resultado | Falta |
|---|---|---|---|---|
| Roles de los agentes | heurística de arranque (AG1) y réplicas de consumidores | N3, N3-R | heurística: T_conv ×0,94 (5/5 lotes en ambas campañas), brecha −0,011, `k_stop` menor; réplicas: efecto mínimo (×0,99; 4/5 lotes) | no hay una definición independiente de «rol»; la operacionalización es la del propio estudio |
| Protocolos de comunicación | despacho por lotes/secuencial; difusión de `g_best` | N3, N3-R | despacho secuencial ×1,60 (N3) y ×1,47 (N3-R) sobre T_conv, sin cambio de solución; difusión ×1,20 (≈ 13 ms y ≈ 11 mensajes) sin mejora de calidad | la magnitud del efecto del despacho varía entre campañas (1,60 frente a 1,47): sensible al régimen del equipo |
| Mecanismos de enjambre | PSO, social, cognitivo | N3, N3-R | cognitivo ≈ 17 % más rápido (razón 1,21 de PSO frente a cognitivo) pero con brecha más del doble (0,032 frente a 0,0143); PSO ≈ social (×0,998; 3/5 lotes) | el menor T_conv del cognitivo es búsqueda truncada, no eficiencia |
| Tiempo de convergencia | `T_conv` (ms) | N3, N3-R | efectos replican en 21 de 21 contrastes evaluados | `T_conv` es una medición exploratoria, no TTFC |
| Eficiencia de la adaptación | **T_conv (la tesis lo declara el único indicador aprobado de eficiencia, §6.3.6)**; CR, k_stop, brecha y mensajes se usan como indicadores **complementarios** (no aprobados como eficiencia): **indicadores que la tesis ya define** (Tabla 1, dimensión Eficiencia; Metas 3 y 4): iteraciones (`k_stop` ≤ 15), ms (T_conv) y CR ≥ 98 %; más calidad (brecha) y mensajes como contexto | N3, N3-R, N3-S (`oe3_eficiencia.py`) | **CR = 100 %** y `k_stop` máx. ≤ 8 en las tres campañas; 6 contrastes con el mismo veredicto en las tres: despacho por lotes, sin difusión de g_best y con heurística **dominan** (más rápido sin perder calidad); cognitivo vs PSO = **compromiso** (T_conv −17 %, `k_stop` −52 %, brecha +123 %); social = PSO y réplicas = sin diferencia relevante | la tesis (§7.1) sigue diciendo que no hay un **índice compuesto** aprobado; no se creó uno. La regla de clasificación (umbral 5 %) se fijó conociendo los efectos agregados de N3; lo independiente es que coincide en N3-R y N3-S. CR mide parada por tolerancia, no calidad |
| Efecto por factor e interacciones | ANOVA tipo III con permutación (999) | Tabla 13/14 (N3); `oe3_robustez.py`, `oe3_replicacion.py` | interacciones significativas (p. ej. despacho × difusión, heurística × mecanismo) en N3 y N3-R | el ANOVA de N3-R no se incorporó a ninguna tabla de la tesis |
| Robustez | consistencia entre lotes, leave-one-batch-out, pruebas por rangos con Holm (las «candidatas» del plan, ejecutadas como análisis exploratorio) | `outputs/oe3_robustez*.json`, `tables/oe3_robustez*` | despacho, difusión, heurística y mecanismo: mismo signo en 5/5 lotes y significativos con Holm; réplicas: significativo en rangos pareados pero de magnitud ≈ 1 % | semillas y lotes sí replican; equipo único |

## Qué NO está demostrado
- Causalidad fuera del modelo en proceso (sin HTTP, N = 20, 1 usuario, un solo equipo).
- Comportamiento con más carga o más tamaño de enjambre (eso es el OE4).
- Cumplimiento de la meta CR ≥ 98 %: la Tabla 15 es el resultado **histórico v2** (K10), no de N3.
- Eficiencia en sentido agregado (índice aprobado inexistente).

## Para cerrar el OE3
1. (Opcional) aprobar un índice compuesto de eficiencia si el autor lo desea; los indicadores individuales de la tesis ya se evalúan.
2. Ejecución oficial (condiciones objetivo y ≥ 10 réplicas por condición, como recomienda la propia tesis): no es posible en este equipo.
3. Decidir si el resultado de N3-R se incorpora a la tesis (nuevo cuadro de réplica); el DOCX **no** se modificó.
