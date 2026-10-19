# OE4 — ejecución N4 (2026-10-06) — resultado

**Naturaleza:** ejecución EXPERIMENTAL no oficial (`environment_class = TECHNICALLY_COMPATIBLE_P6_PENDING`), commit `cec0e06` + una corrección en `oe/factorial.py` (ver abajo). Decisiones internas no aprobadas por el asesor: unidad estadística = corrida; el estadístico de latencia (P95 frente a media), B5 y P6 siguen PENDING. El experimento es independiente de OE2 (no incluye `decision_table`).

## Diseño
- Swarm con N = 20 (configuración de referencia de OE3), persistencia OFF, timeout de cliente 30 s, calentamiento 10 s + ventana estacionaria 60 s, Locust en el mismo host.
- Cargas 1, 5, 10, 25, 50 y 100 usuarios; **10 corridas independientes por carga = 60 corridas**, semilla propia por corrida, orden aleatorizado por bloques, Redis aislado.
- Política de servidor: `reuse` (por defecto fuera de OE2): el servidor no se reinicia entre corridas con el mismo N; cada corrida tiene su calentamiento. OE2 usó `cold_per_run`. Es una diferencia de protocolo a tener presente.
- Complemento en proceso: `runner oe4` con las mismas cargas, 5 lotes de 100 perfiles por carga (3 000 ciclos), para T_conv y k_stop.
- Cargas 1–25: régimen de contraste; 50 y 100: estrés (descriptivo). Ninguna corrida con generador saturado; las 60 comparables.
- Errores y timeouts: 0 y 0 en las 60 corridas.

## Resultados por carga (media de 10 corridas HTTP; T_conv en proceso: mediana por ciclo)
| Usuarios | T_conv HTTP (ms) | T_conv proceso (ms) | k_stop | P50 (ms) | Media (ms) | P95 (ms) | Throughput (req/s) |
|---|---|---|---|---|---|---|---|
| 1 | 66,0 | 62,4 | 1,76 | 91,1 | 93,9 | 120,6 | 10,6 |
| 5 | 217,3 | 209,0 | 1,76 | 297,0 | 313,9 | 476,9 | 15,9 |
| 10 | 425,5 | 398,5 | 1,76 | 604,3 | 635,6 | 971,8 | 15,7 |
| 25 | 1 015,7 | 862,6 | 1,76 | 1 514,4 | 1 603,0 | 2 456,6 | 15,6 |
| 50 | 2 031,2 | 1 767,3 | 1,76 | 2 946,8 | 3 256,7 | 4 986,5 | 15,4 |
| 100 | 4 035,1 | 3 862,9 | 1,76 | 5 574,6 | 6 535,5 | 10 113,9 | 15,3 |

Las DE y los IC95 por carga están en `resumen_oe4.json` y `tabla_por_carga.csv` (dispersión entre corridas pequeña: P95 con DE ≈ 3 % de la media a carga 1 y ≈ 6 % a carga 100).

## Estadística
- **Efecto de la carga** (Kruskal–Wallis sobre 6 grupos de 10): T_conv, P50, media y P95: H = 57,4, p = 4,2e-11 (los grupos están completamente separados: ninguna corrida de una carga se solapa con otra). Throughput: H = 43,3, p = 3,2e-8. ANOVA de una vía con permutación (`campaign/analysis.json`, N de un solo nivel): carga con η² ≈ 1,00 para latencia y T_conv y 0,99 para throughput.
- **Tendencia:** Spearman carga–P95 ρ = 0,986 (p = 6e-47).
- **Cargas consecutivas** (Welch sobre log, Holm m = 5): P95 y T_conv aumentan significativamente en todos los pasos (×3,95 de 1 a 5 usuarios y ×2,0–2,5 en cada paso siguiente; las cargas se duplican, la latencia se duplica). Throughput: solo cambia de 1 a 5 usuarios (×1,5; p Holm = 4e-20); de 5 a 100 no hay diferencia detectable (25→50: p Holm = 0,073).

## Tendencias
- **T_conv:** crece casi proporcionalmente a la carga (66 → 4 035 ms) sin cambiar el número de iteraciones (k_stop constante en 1,76): el aumento es tiempo de espera/cola por concurrencia, no más iteraciones del algoritmo.
- **Latencia:** crece casi linealmente con los usuarios (P95 ≈ 100 ms × usuarios): 121 → 10 114 ms.
- **Throughput:** sube de 10,6 a ≈ 15,9 req/s entre 1 y 5 usuarios y luego queda en una meseta (15,3–15,9 req/s), con una leve caída hacia carga 100. Es saturación del servicio: con usuarios en bucle cerrado, más usuarios solo alargan la cola (throughput ≈ usuarios / latencia media).
- **Estabilidad:** ninguna corrida con error o timeout hasta 100 usuarios; el límite de 30 s no se alcanza (P95 máximo 10,1 s).

## Punto de degradación
- El sistema se satura ya a 5 usuarios (meseta de throughput); a partir de ahí toda la carga adicional se convierte en latencia.
- **La latencia P95 supera los 2 000 ms entre 10 y 25 usuarios:** 10/10 corridas por debajo a 10 usuarios y 0/10 a 25 (interpolando linealmente, ≈ 20 usuarios; no se midió esa carga).
- **El throughput nunca alcanza 20 req/s** en ninguna corrida (0/60), con ninguna carga.
- Mejor desempeño de latencia: 1 usuario (P95 121 ms). Mejor throughput: 5 usuarios en adelante (≈ 15,9 req/s, sin diferencia significativa entre 5 y 100). Mayor degradación: 100 usuarios (P95 10,1 s, T_conv 4,0 s).

## Conclusión específica de OE4
Se pudo medir y comparar el desempeño computacional del artefacto bajo seis condiciones de carga. El artefacto mantiene la estabilidad funcional (sin errores ni timeouts hasta 100 usuarios) pero su capacidad de servicio es prácticamente fija, ≈ 15–16 req/s desde 5 usuarios, y por tanto el tiempo de convergencia y la latencia crecen en proporción a la concurrencia. Cumple L_resp P95 < 2 s hasta 10 usuarios y no a partir de 25; no cumple throughput ≥ 20 req/s en ninguna carga. El umbral práctico de degradación está entre 10 y 25 usuarios (≈ 20 por interpolación).

## Cambio de código necesario
`oe/factorial.py`: `factorial_anova` dividía por cero con un factor de un solo nivel (aquí `swarm_N` fijo en 20). Se omite el término sin grados de libertad y se informa `single_level_factors`; prueba de regresión en `test_oe_campaign_prep.py`. Debido a ese error el primer intento de la campaña (60/60 corridas ejecutadas) falló al escribir el análisis y sus registros no llegaron a guardarse; se repitió la campaña completa. Los crudos del intento fallido están en `failed_attempt1_zerodiv/` y NO se usan como resultado.

## Limitaciones
- Una sola máquina y un solo generador en el mismo host; política `reuse` (no `cold_per_run`).
- Con carga cerrada, latencia y throughput no son evidencia independiente (Little); el límite de 20 req/s es el de RNF04 aplicado a una medición de bucle cerrado.
- N fijo en 20; no se varió la configuración interna (OE3) ni la persistencia (OE2/B5).
- Unidad estadística = corrida (decisión interna, no aprobada por el asesor); P6 y el estadístico de latencia pendientes.
