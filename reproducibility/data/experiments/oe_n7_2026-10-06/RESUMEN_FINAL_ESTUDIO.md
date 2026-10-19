# Resumen final del estudio (N7, 2026-10-06)

Estado: resultados consolidados de N1–N6. **Ejecuciones experimentales, no oficiales**; resultados bloqueados (no se recalcularon). La redacción académica de la tesis se hará aparte; este archivo y `MATRIZ_RESULTADOS_TESIS.md` son la fuente.

## 1. Objetivo general (sin modificar)
«Determinar el efecto de una arquitectura de software multiagente basada en inteligencia de enjambre sobre la eficiencia computacional, la precisión de adaptación y la usabilidad técnica en la adaptación de contenido multimodal, mediante simulaciones controladas y evaluación de usuarios expertos.»

## 2. OE1 — Parcialmente demostrado
Relación entre el cumplimiento de requisitos y el desempeño (14 condiciones, 9 500 ciclos en proceso). Funcionalidad: RF01, RF02, RF04, RF05, RF06 cumplidos; RF03 en 90,5 % (falla solo en la ablación `sequential`; con despacho concurrente 8200/8200). Confiabilidad: REL-C 100 %, REL-D 20/20. Eficiencia: RNF02 cumplido (k_stop máx. 8); RNF01 cumplido solo agregado (P95 1 319 ms; a carga 25 supera 2 000 ms); RNF04 no cumplido (14,98 req/s en proceso). Calidad: RNF03 no cumplido con el F1 v2 histórico (0,6407); RNF05 sin medir. La relación cumplimiento–desempeño (Spearman, n = 14) refleja la carga; el puntaje de cumplimiento (0,78–0,89) no tiene agregación aprobada. Fuente: `oe_n1_2026-10-05/RESULTADO_OE1.md`.

## 3. OE2 — Parcialmente demostrado
Swarm (N = 20) frente a `decision_table`, 80 corridas HTTP (cargas 1, 5, 10, 25; `cold_per_run`; persistencia OFF; 0 errores y 0 timeouts). El swarm tuvo mayor latencia (P95 ×5,05, ×17,8, ×21,7, ×12,8) y menor throughput (×0,159, ×0,065, ×0,058, ×0,062); las 8 hipótesis fueron significativas tras Holm. Tiempo hasta la configuración final (TTFC, en proceso): 67,4 ms frente a 0,008 ms (razón 7 668). `T_conv` existe solo para el swarm (mediana 62,8 ms); TTFC no equivale a `T_conv`, así que el tiempo de convergencia no se compara de forma homogénea. Un único baseline convencional. **No hay evidencia de ventaja de eficiencia computacional del swarm frente a este baseline.** Descriptivamente, el swarm tarda menos que la búsqueda exhaustiva (67,4 frente a 78,3 ms). Fuente: `oe_n2_2026-10-05/RESULTADO_OE2.md`.

## 4. OE3 — Demostrado
Factorial completo de 48 condiciones × 5 lotes (240 corridas, 1 usuario, N = 20). El despacho concurrente reduce `T_conv` ≈ 37 % frente al secuencial sin cambiar la solución; la difusión de g_best suma ≈ 13 ms y ≈ 11 mensajes sin mejorar la calidad; la heurística de arranque reduce iteraciones (1,51 frente a 1,91) y la brecha (0,0150 frente a 0,0258); las réplicas casi no tienen efecto (η² = 0,03); el mecanismo `cognitive` es el más rápido (63,3 ms) pero con el doble de brecha (0,0320); `pso` y `social` son equivalentes. La configuración de referencia no es la mejor: sin difusión de g_best conserva la calidad con ≈ 21 % menos `T_conv`. Peor: sin heurística, `cognitive` y despacho secuencial. Fuente: `oe_n3_2026-10-06/RESULTADO_OE3.md`.

## 5. OE4 — Demostrado
Swarm N = 20, 6 cargas (1, 5, 10, 25, 50, 100), 60 corridas HTTP, 0 errores y 0 timeouts. Throughput 10,6 req/s a 1 usuario y ≈ 15,3–15,9 req/s desde 5 usuarios (nunca ≥ 20; sin diferencia detectable de 5 a 100). P95 de 121 ms a 10 114 ms, `T_conv` HTTP de 66 ms a 4 035 ms, con k_stop constante (1,76): el aumento es espera, no iteraciones. El P95 supera 2 s entre 10 y 25 usuarios (10/10 corridas por debajo a 10; 0/10 a 25); mayor degradación a 100. Fuente: `oe_n4_2026-10-06/RESULTADO_OE4.md`.

## 6. OE5 — Parcialmente demostrado
*Precisión:* F1_adapt v3 = 0,8156 (IC95 0,8111–0,8201; por perfil mediana 0,806, DE 0,142), por debajo de 0,85; **provisional** (la regla v3 no está aprobada y el gold no fue validado por el panel). Errores principales: audio y texto sobrantes, código o diagrama omitidos. *Usabilidad:* **0 evaluadores reales; sin puntuación SUS; no puede determinarse si supera 75** (el SUS = 85 de una prueba es un vector TEST). Instrumento, protocolo, cálculo y plantillas listos. Fuente: `oe_n5_2026-10-06/RESULTADO_OE5.md`.

## 7. Resultado integrado
- **Demostrado:** el efecto de la configuración interna (roles, protocolo, mecanismo) sobre el tiempo de convergencia y la calidad; el efecto de la carga sobre `T_conv`, latencia y throughput; el funcionamiento y la estabilidad (sin errores ni timeouts hasta 100 usuarios, ciclos 100 % completados, reproducibilidad con la misma semilla); el comportamiento comparativo frente al baseline (mayor costo computacional).
- **Parcial / provisional:** la precisión (F1 v3 0,8156 provisional); OE1 (RNF03 y RNF05, y relación condicionada por la carga); OE2 (indicador de convergencia no homogéneo y un único comparador).
- **Pendiente:** el SUS y la evaluación humana; todo lo que dependa de la aprobación de la regla v3.
- **Efecto sobre las tres dimensiones:** eficiencia computacional determinada (desfavorable frente al baseline, degradada con la carga, modificable por la configuración); precisión determinada de forma provisional; usabilidad no determinada. No se construyó ningún índice compuesto.

## 8. Limitaciones
Ejecuciones no oficiales y decisiones internas de protocolo no aprobadas por el asesor; una sola máquina con el generador en el mismo host (no es el hardware aprobado, P6); F1 v3 provisional y semilla oficial de K = 10 ya usada antes de sellar la regla; sin evaluadores (SUS y panel pendientes; consentimiento y versión en español del SUS sin validar); un único baseline convencional simple; `T_conv` y TTFC no equivalentes; carga cerrada (latencia y throughput no independientes); OE4 con política `reuse` y OE2 con `cold_per_run`; OE1 en proceso y sin agregación aprobada del puntaje; OE3 a 1 usuario con 5 corridas por condición y N = 20; N4 repetido tras un error de análisis (`ZeroDivisionError`, ya corregido y con prueba de regresión).

## 9. Pendientes
1. ≥ 10 evaluadores reales: SUS y panel (protocolo en `oe_n5_2026-10-06/instrumento/`).
2. Aprobación de la regla v3 y validación del gold para que el F1 pueda ser oficial.
3. Decisiones del asesor abiertas: estadístico de latencia, unidad estadística definitiva, hipótesis formal de OE2, B1, B5, B13, P6; la campaña oficial sigue bloqueada.
4. Repetir OE2 y OE4 en el hardware aprobado si se busca una conclusión oficial.
5. Trasladar los resultados a la tesis (no se modificó ningún DOCX).

## 10. Archivos fuente
`backend/experiments/` — `oe_n1_2026-10-05/`, `oe_n2_2026-10-05/`, `oe_n3_2026-10-06/`, `oe_n4_2026-10-06/`, `oe_n5_2026-10-06/`, `oe_n6_2026-10-06/` (matriz de cumplimiento, resultado del objetivo general, tabla consolidada) y esta carpeta (`MATRIZ_RESULTADOS_TESIS.md`, `manifest.json`, `SHA256SUMS`). Gráficos: `oe_n2_2026-10-05/oe2_latencia_throughput.png`, `oe_n3_2026-10-06/oe3_efectos_marginales.png`, `oe_n4_2026-10-06/oe4_usuarios_vs_{tconv,p95,throughput}.png`. Los archivos de N1–N6 se referencian por ruta y hash; no se duplicaron.

## Estado de verificación (N7)
Suite `tests/adaptation_swarm`: 1100 passed, 18 failed, 5 errors, 6 skipped; los 23 fallos son los preexistentes (`test_cpp_render` 9 failed + 5 errors, `test_agents_library` 3, `test_sprint_modules_safeguards` 3, `test_library_full_coverage` 1, `test_library_inventory` 1, `test_library_sandbox_integration` 1; no se investigaron en esta fase) y ninguno afecta a N1–N6.
