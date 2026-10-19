# Resultado del objetivo general (N6, 2026-10-06)

## Objetivo general (sin modificar)
«Determinar el efecto de una arquitectura de software multiagente basada en inteligencia de enjambre sobre la eficiencia computacional, la precisión de adaptación y la usabilidad técnica en la adaptación de contenido multimodal, mediante simulaciones controladas y evaluación de usuarios expertos.»

Fuentes: solo `backend/experiments/oe_n1_2026-10-05/`, `oe_n2_2026-10-05/`, `oe_n3_2026-10-06/`, `oe_n4_2026-10-06/`, `oe_n5_2026-10-06/` (referenciadas por ruta; no se duplican). No se ejecutó ninguna campaña nueva. No hay índice ni puntuación compuesta.

## Qué muestra cada objetivo
- **OE1 (parcial).** La arquitectura es funcional y confiable en su configuración de referencia: RF01, RF02, RF04, RF05 y RF06 se cumplen; REL-C (100 % de ciclos completados) y REL-D (20/20 pares idénticos) también. RF03 (90,5 %) falla solo porque la condición `sequential` desactiva a propósito el despacho concurrente (con despacho concurrente: 8200/8200). En eficiencia, RNF02 se cumple (k_stop máximo 8 ≤ 15), RNF01 se cumple solo agregado (P95 en proceso 1319 ms) y no a carga 25, y RNF04 no se cumple (14,98 req/s < 20). RNF03 no se cumple con el F1 v2 histórico (0,6407) y RNF05 no está medido. La relación entre cumplimiento de requisitos y desempeño (Spearman por condición, n = 14) refleja la carga más que un efecto del cumplimiento; el puntaje de cumplimiento (0,78–0,89) no tiene agregación aprobada.
- **OE2 (parcial).** Frente a `decision_table`, el swarm tuvo mayor latencia (P95 entre 5 y 22 veces) y menor throughput (0,06 a 0,16 veces) en las cuatro cargas (1, 5, 10, 25 usuarios); las ocho hipótesis de la familia fueron significativas tras Holm (80 corridas, `cold_per_run`, persistencia OFF). Las medianas del indicador operacional de tiempo hasta la configuración final fueron 67,4 ms (swarm) y 0,008 ms (`decision_table`). `T_conv` solo existe para el swarm (mediana 62,8 ms); el indicador común (TTFC) no es `T_conv` y su validación metodológica está pendiente, así que **no se presenta como una comparación homogénea de tiempo de convergencia**. **OE2 no demuestra una ventaja de eficiencia computacional del swarm; muestra lo contrario frente a este baseline.** Descriptivamente, el swarm tarda menos que la búsqueda exhaustiva (67,4 ms frente a 78,3 ms).
- **OE3 (demostrado).** La configuración interna sí afecta `T_conv` y la eficiencia. El despacho concurrente reduce `T_conv` ≈ 37 % sin cambiar la solución. Difundir g_best cuesta ≈ 13 ms y ≈ 11 mensajes por ciclo sin mejorar la calidad. La partícula heurística de arranque reduce iteraciones (1,5 frente a 1,9) y la brecha frente al óptimo (0,015 frente a 0,026). Duplicar réplicas casi no cambia nada. El mecanismo sin componente social (`cognitive`) es el más rápido pero duplica la brecha; `pso` y `social` son equivalentes. La configuración de referencia no es la mejor de las 48: sin difusión de g_best conserva la calidad y es ≈ 21 % más rápida. La peor es sin heurística, `cognitive` y despacho secuencial.
- **OE4 (demostrado).** Con N = 20 y seis cargas (1, 5, 10, 25, 50, 100 usuarios), el artefacto es estable (0 errores y 0 timeouts en 60 corridas) pero su capacidad es casi fija: throughput de 10,6 req/s a 1 usuario y ≈ 15,3–15,9 req/s desde 5 usuarios (nunca ≥ 20). `T_conv` y latencia crecen en proporción a la carga (P95 de 121 ms a 10 114 ms; `T_conv` HTTP de 66 ms a 4 035 ms) sin cambiar las iteraciones (k_stop 1,76). El P95 supera 2 s entre 10 y 25 usuarios (10/10 corridas por debajo a 10 usuarios; 0/10 a 25) y la mayor degradación aparece con 100 usuarios.
- **OE5 (parcial).** *Precisión:* F1_adapt v3 = 0,8156 (IC95 0,8111–0,8201), por debajo de 0,85; es evidencia experimental provisional porque la regla v3 no está aprobada y el gold no fue validado por el panel; los errores principales son audio y texto sobrantes (falsos positivos) y código o diagrama omitidos. *Usabilidad:* 0 evaluadores reales ⇒ no hay puntuación SUS y no puede determinarse si supera 75. El SUS = 85 que aparece en una prueba de software es un vector TEST de verificación de la fórmula, no un resultado de usuarios.

## Efecto sobre las tres dimensiones del objetivo general
| Dimensión | Evidencia | Qué se pudo determinar | Estado |
|---|---|---|---|
| Eficiencia computacional | OE2 + OE3 + OE4 | Costo alto frente a una tabla de decisión estática (latencia y throughput peores, significativos); la configuración interna lo modifica (prescindir de la difusión de g_best reduce `T_conv` ≈ 21 % frente a la referencia; el despacho secuencial lo aumentaría ≈ 60 %); capacidad fija ≈ 15–16 req/s y degradación desde 10–25 usuarios | Determinado (efecto desfavorable frente al baseline; condicionado por la configuración y la carga) |
| Precisión de adaptación | OE1 + OE5/F1 | F1 v3 provisional 0,8156 (< 0,85); en OE1 RNF03 se evaluó con el F1 v2 histórico 0,6407 (otra definición, no combinable) | Determinado de forma provisional |
| Usabilidad técnica | OE5/SUS | Nada: 0 evaluadores | **Pendiente** |

## Respuesta al objetivo general
La evidencia actual permite determinar el efecto de la arquitectura sobre la eficiencia computacional y, de forma provisional, sobre la precisión de adaptación; no permite todavía determinarlo sobre la usabilidad técnica.
- La arquitectura multiagente con enjambre es **funcional y estable**: sin errores ni timeouts hasta 100 usuarios, ciclos completados al 100 %, resultados reproducibles con la misma semilla.
- Su **configuración interna tiene efectos medibles y grandes** en el tiempo de convergencia (protocolo, mecanismo) y moderados en la calidad (heurística de arranque, mecanismo).
- Su **desempeño computacional se degrada con la carga**: capacidad ≈ 15–16 req/s y P95 > 2 s a partir de 25 usuarios.
- **Frente al `decision_table` tiene mayor costo computacional** (mayor latencia, menor throughput y mayor tiempo operacional hasta la configuración final), con diferencias significativas. Con estos datos no se puede afirmar que la arquitectura sea superior en eficiencia.
- La **precisión** provisional (F1 v3 0,8156) está por debajo de la meta de 0,85 que el proyecto usa; la **usabilidad (SUS frente a 75) queda pendiente de evaluadores reales**.

## Limitaciones (las registradas en N1–N5)
- Todas las ejecuciones son experimentales y no oficiales; las decisiones internas de protocolo (corridas independientes, escala log, Welch, Holm m = 8, `cold_per_run`, bloques aleatorizados, unidad = corrida) no están aprobadas por el asesor; siguen pendientes el estadístico de latencia, la hipótesis formal de OE2, B1, B5, B13 y P6.
- Hardware: una sola máquina (i7-12700K, 20 vCPU, 31,75 GiB) y el generador de carga comparte host con el servidor; no es el hardware objetivo aprobado (P6).
- F1 v3 es provisional (regla v3 no aprobada, gold sin validar por el panel); F1 v2 (0,6407) es otra definición. Una ejecución provisional con la semilla oficial de K = 10 ya muestra el valor antes de sellar la regla.
- Sin evaluadores: SUS, panel y validación humana pendientes; consentimiento y versión en español del SUS sin validar.
- Un único baseline convencional (`decision_table`), simple y de reglas estáticas; no representa a «sistemas convencionales» como clase.
- `T_conv` y TTFC no son equivalentes: el tiempo de convergencia del convencional (decisión sin iteración) no es homogéneo con el del swarm.
- Carga cerrada: latencia y throughput no son evidencia independiente (throughput ≈ usuarios / latencia media); OE4 usó política de servidor `reuse` y OE2 `cold_per_run`.
- OE1 se midió en proceso (sin HTTP) y su puntaje de cumplimiento no tiene agregación aprobada; OE3 con 1 usuario, N = 20 y 5 corridas por condición; OE4 con N = 20 fijo.
- N4 requirió repetir la campaña tras corregir un error de análisis (`ZeroDivisionError`); los crudos del intento fallido no se usan.

## Pendientes reales
1. Evaluadores reales (≥ 10) para el SUS y el panel del gold: aplicar el protocolo de `oe_n5_2026-10-06/instrumento/`.
2. Aprobación de la regla v3 y validación del gold para que F1 sea oficial.
3. Decisiones del asesor aún abiertas: estadístico de latencia, unidad estadística definitiva, hipótesis formal de OE2, B1, B5, B13 y P6; hasta entonces la campaña oficial sigue bloqueada.
4. Si se quiere una conclusión oficial: repetir OE2/OE4 en el hardware aprobado.
5. Incorporar los resultados al documento de tesis (no se modificó ningún DOCX).

## Evidencia
Ver `MATRIZ_CUMPLIMIENTO.md`, `RESUMEN_POR_OE.md`, `tabla_consolidada.csv` y `SHA256SUMS` (hash de cada archivo referenciado de N1–N5).
Gráficos existentes: `oe_n2_2026-10-05/oe2_latencia_throughput.png`, `oe_n3_2026-10-06/oe3_efectos_marginales.png`, `oe_n4_2026-10-06/oe4_usuarios_vs_{tconv,p95,throughput}.png`.
