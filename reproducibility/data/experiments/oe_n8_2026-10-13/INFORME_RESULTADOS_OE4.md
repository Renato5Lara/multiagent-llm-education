# INFORME DE RESULTADOS — OE4 (desempeño computacional bajo distintas condiciones) — actualizado 2026-10-15 (N11 completa)

Evidencia: N4 (`oe_n4_2026-10-06/`, N = 20), N8 (`oe_n8_2026-10-13/`, N = 10 y 30), N8b (`oe_n10_2026-10-14_n20/`, N = 20 repetida con el protocolo de N8) y **N11 (`oe_n11_2026-10-14_3N/`, los tres N aleatorizados en una sola campaña, ahora completa: 179 válidas + 1 inválida de 180)**. Todo **experimental, no oficial**.

> **Cambio de conclusión (2026-10-15).** N11 **no reproduce** la anomalía «N = 10 más lento que N = 20». En una misma campaña aleatorizada el orden es N = 10 < N = 20 ≲ N = 30 en latencia. El contraste N8 vs N8b comparaba dos **regímenes de rendimiento del equipo** distintos (§5). La causa física del cambio de régimen **no se aísla** (§5).

## 1. Objetivo (sin modificar)
«Medir y comparar el desempeño computacional del artefacto bajo diferentes condiciones de simulación, utilizando tiempo de convergencia, latencia y throughput.»

## 2. Campañas ejecutadas y su estado
| Campaña | Diseño | Corridas válidas | Estado |
|---|---|---|---|
| N4 (2026-10-06) | N = 20; 6 cargas × 10; margen 5 s | 60/60 | Completa |
| N8 (2026-10-13) | N = 10 y 30; 6 cargas × 10; `--start-margin 20`; Redis en Docker | 120/120 | Completa |
| **N8b (2026-10-14)** | N = 20; 6 cargas × 10; mismo comando y parámetros que N8; diario incremental | **60/60** (60 `completed`, 0 fallos) | Completa |
| **N11 (2026-10-14/15)** | Los tres N aleatorizados en bloques (6 cargas × 3 N × 10 réplicas = 180); `--start-margin 20`; mismos parámetros que N8/N8b | **179/180 válidas** (179 `completed`, 1 `invalid`: `u100\|N10-r01`, `no_requests`, sin métricas, excluida); 0 errores, 0 timeouts | **Completa** en dos tramos de ejecución: A = ejecuciones 1–17 (primer lanzamiento, detenido por baja memoria) y B = 18–180 (reanudada con `--resume` tras reiniciar Docker Desktop). El tramo B tiene 162 corridas válidas y 8–10 por celda (§3b) |
Todas: 0 errores y 0 timeouts en las corridas válidas; 0 generador saturado; persistencia OFF; política `reuse`; Locust en el mismo host. Diferencias de entorno entre N8 y N8b: sesión distinta (≈ 14 h de diferencia), contenedores Docker auxiliares activos en ambas, muestreo de recursos solo en N8b (188 muestras: memoria libre 7,7–10,7 GiB; carga de CPU 0–66 %, media 34 %; `oe_n10_2026-10-14_n20/recursos.csv`); la sesión de N8 no tiene registro de recursos. **No se afirma que el entorno sea idéntico.**

## 3. Resultados por N y carga (medias de 10 corridas; P95 ms · throughput req/s · T_conv HTTP ms)
| Usuarios | N = 10 (N8) | N = 20 (N8b) | N = 30 (N8) |
|---|---|---|---|
| 1 | 173 · 7,9 · 88 | 119 · 10,6 · 62 | 209 · 6,1 · 126 |
| 5 | 658 · 11,2 · 305 | 473 · 15,9 · 215 | 883 · 8,1 · 425 |
| 10 | 1 364 · 11,3 · 609 | 970 · 15,9 · 422 | 1 873 · 7,8 · 835 |
| 25 | 3 391 · 11,1 · 1 478 | 2 418 · 15,8 · 1 003 | 4 637 · 7,7 · 1 976 |
| 50 | 6 686 · 11,0 · 2 939 | 4 874 · 15,8 · 1 973 | 8 779 · 7,8 · 3 796 |
| 100 | 13 542 · 10,9 · 5 916 | 9 895 · 15,6 · 3 953 | 17 943 · 7,8 · 7 618 |
(`oe4_nvar/oe4_nvar_descriptivos.csv`; DE e IC por celda en los CSV.) **Esta tabla combina campañas de regímenes distintos (§5); el contraste entre N no debe leerse de aquí sino de §3b.**

### 3b. N11: los tres N en una misma campaña, tramo B (ejecuciones 18–180; P95 ms · throughput req/s · T_conv HTTP ms; n = corridas por celda)
| Usuarios | N = 10 | N = 20 | N = 30 |
|---|---|---|---|
| 1 | 105 · 12,6 · 48 (9) | 122 · 10,7 · 62 (9) | 127 · 9,9 · 68 (9) |
| 5 | 367 · 20,1 · 165 (9) | 452 · 16,2 · 210 (9) | 499 · 14,4 · 234 (9) |
| 10 | 842 · 19,0 · 367 (9) | 947 · 16,0 · 417 (9) | 1 058 · 14,0 · 462 (9) |
| 25 | 1 890 · 20,0 · 813 (9) | 2 616 · 15,2 · 1 082 (9) | 2 598 · 13,7 · 1 102 (9) |
| 50 | 3 864 · 19,4 · 1 664 (9) | 5 033 · 15,3 · 2 039 (9) | 5 003 · 13,7 · 2 147 (10) |
| 100 | 7 658 · 19,3 · 3 353 (8) | 10 465 · 14,9 · 4 145 (9) | 10 485 · 13,8 · 4 255 (9) |
(`oe4_n11/oe4_n11_descriptivos_tramoB.csv`; todas las celdas con n ≥ 8; las 17 corridas del tramo A se analizan aparte.)

**Contrastes dentro del tramo B** (unidad = corrida; Welch sobre log; Holm por métrica sobre 18 contrastes; razón de medias geométricas; `oe4_n11/oe4_n11_contrastes.csv`):
| Contraste | P95 (razón; rango en 6 cargas) | Throughput | T_conv HTTP | Significativas tras Holm (de 6 cargas) | g de Hedges (P95) |
|---|---|---|---|---|---|
| N = 20 vs N = 10 | ×1,15–1,36 | ×0,75–0,86 | ×1,16–1,30 | P95 5/6; throughput 5/6; T_conv 5/6 | 0,9 a 6,0 |
| N = 30 vs N = 10 | ×1,22–1,38 | ×0,68–0,79 | ×1,27–1,42 | 6/6 en las tres métricas | 1,7 a 6,3 |
| N = 30 vs N = 20 | ×0,99–1,12 | ×0,87–0,93 | ×1,03–1,12 | P95 2/6; throughput 4/6; T_conv 3/6 | −0,1 a 2,2 |
La única celda no significativa en N20 vs N10 es 10 usuarios (P95: ×1,15, IC95 0,98–1,33, p Holm 0,37; throughput: ×0,86, IC95 0,74–1,00, p Holm 0,12; T_conv: ×1,16, p Holm 0,24). Con 100 usuarios N20 vs N10 es ×1,36 (IC95 1,26–1,48). Las IC95 son de Welch por celda con n = 8–10: son amplias donde la varianza es mayor.
**Modelo conjunto (todo N11, `log y ~ N × carga + tramo`):** efecto de N muy significativo (η² parcial: P95 0,63; throughput 0,74; T_conv 0,71); el tramo es un factor aún mayor (η² 0,71–0,78); interacción N × carga no significativa a 0,05 (P95 p = 0,059; throughput 0,29; T_conv 0,23). Con bloque de réplica añadido el efecto de N se mantiene (η² 0,72–0,80). **Análisis principal = tramo B** porque N11 estaba balanceada en N en ese tramo; los contrastes que mezclan ambos tramos sin ajuste pierden potencia (solo 2/6 y 1/6 significativas en N20 vs N10) y se conservan en el CSV (`scope = todo`) como sensibilidad, no como resultado.
Deriva dentro del tramo B: Spearman entre el orden de ejecución y el residuo del modelo, P95 ρ = −0,09 (p = 0,26), throughput ρ = 0,13 (p = 0,09), T_conv ρ = −0,12 (p = 0,13): no se detecta deriva sistemática, con la salvedad de que el diseño no permite descartarla.

## 4. Contrastes ENTRE campañas (N8 y N8b) — confundidos con el régimen del equipo (§5); el contraste válido de N es el de §3b
(unidad = corrida; Welch sobre log; Holm por tipo de contraste y métrica, m = 6 cargas)
| Contraste | P95 (razón, rango sobre las 6 cargas) | Throughput | T_conv HTTP | p Holm máx. |
|---|---|---|---|---|
| N = 30 vs N = 10 (ambos N8, misma sesión) | ×1,21–1,37 | ×0,69–0,77 | ×1,29–1,42 | ≤ 2e-7 |
| N = 20 (N8b) vs N = 10 (N8) | **×0,69–0,73** | **×1,35–1,43** | ×0,67–0,70 | ≤ 2e-8 |
| N = 30 (N8) vs N = 20 (N8b) | ×1,76–1,93 | ×0,49–0,57 | ×1,92–2,03 | ≤ 8e-11 |
| **Sesión** con N = 20 fijo: N8b vs N4 | ×0,98–1,00 | ×0,99–1,03 | ×0,94–0,99 | P95 y throughput: ninguna significativa (mín. p Holm 0,077); T_conv: diferencia pequeña pero significativa (≤ 6 %) |

### Corrección de interpretaciones anteriores
1. La primera versión atribuía «N = 10 más lento que N = 20» a un efecto de sesión de N4. N8b lo refutó para N = 20 (N8b/N4 = 0,98–1,03: ese nivel se reproduce).
2. La segunda versión (2026-10-14) declaraba la relación **no monótona** («N = 20 mejor que N = 10 y N = 30») y la anomalía «real en los datos de N8». **N11 lo corrige:** en una misma campaña aleatorizada N = 10 es el más rápido; la no monotonicidad provino de comparar entre campañas.

## 5. La anomalía N = 10 vs N = 20: qué muestra N11
**Hallazgo 1 — la anomalía no se reproduce dentro de una campaña.** En N11 (tramo B) N = 20 vs N = 10 da P95 ×1,15–1,36 y throughput ×0,75–0,86 (5/6 cargas significativas tras Holm): **N = 10 es más rápido**, lo contrario del contraste N8 vs N8b (P95 ×0,69–0,73, throughput ×1,35–1,43). La razón N = 30 vs N = 10 sí se reproduce entre campañas (N8: P95 ×1,21–1,37, throughput ×0,69–0,77; N11-B: P95 ×1,22–1,38, throughput ×0,68–0,79).

**Hallazgo 2 — N11 contiene un cambio de régimen global.** Entre el tramo A (ejecuciones 1–17) y el tramo B (18–180), ajustando por carga, P95 y T_conv HTTP bajan a ×0,60–0,62 y el throughput sube a ×1,61–1,63; la razón es prácticamente la misma para N = 10, 20 y 30 (P95: 0,62, 0,62, 0,61; throughput: 1,61, 1,62, 1,63; `oe4_n11/oe4_n11_cambio_regimen_A_B.csv`). Es un escalado multiplicativo común, no un efecto de N.

**Hallazgo 3 — N8 se parece al régimen A y N8b al régimen B** (razón campaña previa / N11 por N, ajustada por carga; ~1 = mismo régimen; `oe4_n11/oe4_n11_regimen_de_campanias_previas.csv`). N8 con N = 10: 1,07 (P95) y 0,93 (throughput) frente al tramo A, pero 1,73 y 0,58 frente al B. N8 con N = 30: 1,06 y 0,93 frente al A; 1,74 y 0,57 frente al B. N8b con N = 20: 0,98 y 1,02 frente al B; 0,61 y 1,65 frente al A. Si N8 estuvo en régimen A y N8b en régimen B, el cociente cruzado esperado de throughput N = 10 sobre N = 20 es el cociente dentro de un régimen dividido por ≈ 1,6: en N11-B vale 1,17–1,34, es decir ≈ 0,73–0,84 esperado, frente a 0,70–0,74 observado entre N8 y N8b (`oe4_n11/oe4_n11_sintesis_entre_campanias.csv`). **El contraste N8 vs N8b es compatible con una diferencia de régimen del equipo y no del tamaño del enjambre.** Es una explicación compatible, no una prueba.

**Qué NO se establece.**
- **La causa del cambio de régimen no está aislada.** Lo medido: memoria libre en el tramo A 7,2–10,0 GiB (media 9,2) con CPU media 29 % (`recursos.csv`); en el tramo B 9,3–15,1 GiB (media 11,9) (`memguard_tramoB.log`, otro instrumento, sin CPU). Entre tramos se reinició Docker Desktop. Son candidatos (presión de memoria, estado de Docker/WSL, otros procesos), **no explicaciones demostradas**.
- **La clasificación en regímenes A/B es posterior a los datos (post hoc).** El tramo A tiene solo 17 corridas (5–6 por N); que N8 se parezca al A descansa en razones ajustadas por carga con una muestra pequeña.
- El régimen no fue una variable aleatorizada. Dentro del tramo B (análisis principal) el diseño sí es de bloques aleatorizados y balanceado en N.

**Consecuencia para OE4 (objetivo sin modificar).** En una campaña única el efecto del tamaño del enjambre sobre latencia y throughput es **monótono**: más partículas, más latencia y menos throughput (N = 30 vs N = 10: P95 ×1,2–1,4 en ambas campañas; N = 30 vs N = 20: ×1,0–1,1, con solo 2/6 cargas significativas en P95). **No se declara mejor ningún N:** esta campaña HTTP no mide la calidad de la solución (brecha, F) por N, y un enjambre menor es más rápido pero puede converger a una solución peor (eso se evalúa en OE3/N1, no aquí). Las iteraciones son coherentes con el orden: k_stop medio por petición (N8/N8b) N = 10: 1,55; N = 20: 1,78; N = 30: 1,91. Las cifras de N8, N8b y N4 se conservan tal como se midieron.

## 6. Efecto de la carga (consistente en N = 10, 20 y 30)
- P95 y T_conv HTTP crecen casi proporcionalmente con los usuarios (Spearman carga–P95 ρ = 0,986 en cada N; Kruskal–Wallis p = 4,2e-11 en cada N). ANOVA carga×N sobre log P95: η² parcial N = 0,98, carga = 0,999, interacción = 0,23 (`oe4_nvar_anova.csv`; referencia, con la salvedad de la sesión de N8).
- Throughput: meseta desde 5 usuarios. N8/N8b: N = 10: 10,9–11,3; N = 20: 15,6–15,9; N = 30: 7,7–8,1 req/s; **ninguna de esas 180 corridas alcanza 20 req/s**. **N11 (tramo B): N = 10: 19,0–20,1 req/s (desde 5 usuarios); N = 20: 14,9–16,2; N = 30: 13,7–14,4. 18 corridas de N11 (todas N = 10, tramo B; por carga: 5 usuarios 5 corridas, 10 usuarios 5, 25 usuarios 5, 50 usuarios 1, 100 usuarios 2) alcanzan ≥ 20 req/s (máx. 21,99); las medias de celda llegan a 20,1 (5 usuarios) y 20,0 (25 usuarios).** RNF04 (≥ 20 req/s con error < 1 %) se alcanza por tanto en corridas aisladas de N = 10 en el régimen B, no de forma sostenida ni con N = 20/30, y no se alcanza en el régimen A.
- Ley de Little (1961): en carga cerrada throughput ≈ usuarios / latencia media; latencia y throughput no son evidencia independiente. T_conv HTTP incluye espera en cola; no es el T_conv del algoritmo (k_stop no cambia con la carga) ni la latencia de una petición.
- RNF01 (P95 < 2 s): en N8/N8b se cumple en 1, 5 y 10 usuarios y se incumple en 25, 50 y 100 para N = 10, 20 y 30 (N = 30 a 10 usuarios: 1 873 ms). **En N11 (tramo B)** N = 10 también lo cumple a 25 usuarios (media de celda 1 890 ms; 8/9 corridas < 2 s) y N = 20 y N = 30 lo cumplen hasta 10 usuarios (media ≤ 1 058 ms) y no a 25 (≈ 2 600 ms). El umbral práctico está entre 10 y 25 usuarios, y depende de N y del régimen del equipo.
- 0 errores y 0 timeouts en las corridas válidas de las tres campañas; P95 máximo 17,9 s (N = 30, 100 usuarios) < timeout de 30 s.

## 7. N11: ejecución, reanudación e integridad
Primer lanzamiento: ejecuciones 1–17 completas, 18 fallida (`u50|N30-r00`), 19 inválida (`u100|N10-r01`, `no_requests`); detenido por baja memoria. Reanudación (`--resume`, mismo `--campaign-id`, plan y semillas) el 2026-10-14 tras iniciar Docker Desktop: conservó las 17 completas y la inválida («ya medida (diario): se conserva»), re-ejecutó la fallida y completó el resto sin errores. Estado final del diario: 179 `completed`, 1 `invalid`, 0 `failed`, 0 `interrupted`; 181 entradas para 180 corridas (la entrada `failed` fue superada por su re-ejecución; manda la última entrada de cada `run_id`). Diario previo a la reanudación conservado en `campaign.journal_pre_resume_19runs.jsonl` (SHA-256 `fa63d4b1cb74635aab6e8d86bd65149f782d68103dec80ee930fef3974c05c72`).
**La corrida inválida no se repitió**: la reanudación conserva las `invalid`. Se excluye de los análisis (sin métricas) y se registra; la celda N = 10 / 100 usuarios tiene 8 válidas en el tramo B y 9 en total.
Dos intentos previos de reanudar se rechazaron antes de ejecutar nada («faltan datos de provenance: `software.redis_server`»: variables de entorno sin exportar); no escribieron ninguna corrida. Un guardián de memoria (detener si < 1,5 GiB libres) no se activó. Al terminar: `official_valid = false` por un hueco de provenance (igual que N8/N8b).

## 8. Resumen
Se midió el desempeño en 3 tamaños de enjambre × 6 cargas con N8, N8b y N11 (más N4), sin errores ni timeouts. Sólido: estabilidad hasta 100 usuarios; latencia lineal en la carga y meseta de throughput; N = 30 más lento que N = 10 (P95 ×1,2–1,4), reproducido en dos campañas; en una campaña única el orden es N = 10 < N = 20 ≲ N = 30 en latencia. **La anomalía N8/N8b es compatible con un cambio de régimen del equipo (≈ ×1,6 en throughput) cuya causa física no se aísla.** Metas: RNF04 (≥ 20 req/s) lo alcanzan **18 corridas individuales de N = 10 en el régimen B** (máx. 21,99 req/s) y las medias de celda 20,1 (5 usuarios) y 20,0 (25 usuarios), pero no de forma sostenida ni con N = 20 o N = 30; RNF01 (P95 < 2 s) se cumple con N = 10 hasta 25 usuarios (media de celda 1 890 ms; 8/9 corridas) y hasta 10 usuarios con N = 20 y N = 30.

## 9. Limitaciones y recursos externos
Hardware objetivo 8 vCPU/32 GB no disponible (el equipo local i7-12700K, 20 hilos, 31,7 GiB, generador en el mismo host **no es equivalente**); N11 tiene dos tramos con régimen distinto y no muestreó CPU en el tramo B; sin registro de recursos en N8; la clasificación de regímenes es posterior a los datos; no se midió la calidad de la solución por N en HTTP; decisiones del asesor abiertas (P95 vs media, unidad estadística, P6); `official_valid = false` en todas las campañas.

## 10. Reproducción
```
# N8b: ../.venv/Scripts/python.exe -m adaptation_swarm.oe.http_campaign oe4 --campaign-id n10-oe4-n20 --out-dir experiments/oe_n10_2026-10-14_n20/campaign --runs 10 --users 1,5,10,25,50,100 --particles 20 --start-margin 20
# N11 (desde backend/): docker start adaptation_swarm_test_redis adaptation_swarm_test_postgres; set -a; source tests/adaptation_swarm/integration_env/test.env; set +a; export SWARM_REQUIRE_LIBRARY=1 PYTHONUTF8=1
../.venv/Scripts/python.exe -m adaptation_swarm.oe.http_campaign oe4 --campaign-id n11-oe4-3n --out-dir experiments/oe_n11_2026-10-14_3N/campaign --runs 10 --users 1,5,10,25,50,100 --particles 10,20,30 --start-margin 20            # primer lanzamiento; la reanudación ejecutada es el mismo comando + --resume
cd experiments/oe_n8_2026-10-13 && <python análisis> scripts/oe4_nvar_analysis.py      # N8, N8b y N4 -> oe4_nvar/
cd experiments/oe_n8_2026-10-13 && <python análisis> scripts/oe4_n11_analysis.py       # N11 (+ N8 y N8b para el régimen) -> oe4_n11/
```
Entorno de análisis: Python 3.12.10 con `requirements_analisis.txt` (numpy, scipy 1.18.1, pandas 3.0.6, statsmodels 0.15.0, matplotlib 3.11.2). Salidas de N11: `oe4_n11/{oe4_n11_descriptivos,oe4_n11_descriptivos_tramoB,oe4_n11_contrastes,oe4_n11_anova,oe4_n11_cambio_regimen_A_B,oe4_n11_regimen_de_campanias_previas,oe4_n11_sintesis_entre_campanias}.csv`, `oe4_n11.json`, `oe4_n11_carga_N.png`, `_salida.txt`. Persistencia: `RunJournal` y `--resume`; margen de inicio `--start-margin`; pruebas `test_oe_campaign_journal.py` y `test_oe_start_margin.py` (11 pasan, 2026-10-14).
