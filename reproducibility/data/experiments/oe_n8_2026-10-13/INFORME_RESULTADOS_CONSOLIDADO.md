# INFORME DE RESULTADOS CONSOLIDADO OE1–OE5 (actualizado 2026-10-15, N11 completada)

Todas las ejecuciones son **experimentales y no oficiales** (hardware objetivo P6 no disponible; decisiones del asesor abiertas). No se modificó D2.6, ningún documento de tesis ni experimento histórico (SHA-256 de N1–N7 verificados: 0 diferencias). Índice de entregables al final (§9).

## 0. Novedades de la continuación
| Frente | Resultado |
|---|---|
| N8b (OE4, N = 20 con el protocolo de N8) | **60/60 corridas válidas.** Reproduce a N4 (N8b/N4 = 0,98–1,03 en P95 y throughput): el nivel N = 20 es estable entre sesiones. Refutó la hipótesis de «efecto de sesión de N4», pero **N11 (abajo) muestra que el contraste N8 vs N8b está confundido con un cambio de régimen del equipo**, no con el tamaño del enjambre |
| N9b (OE2, rules y bruteforce) | **160/160 corridas válidas** (159 + 1 repetida con `--resume`), 0 errores/timeouts. Réplica swarm vs `decision_table`: misma dirección (P95 ×3,9–14,7; throughput ×0,084–0,213; 8/8 significativas); swarm estable entre sesiones, `decision_table` no. Auxiliares: swarm ≈ `bruteforce` en P95; `rules` ≈ `decision_table` |
| **N11 (OE4, tres N aleatorizados) — completada 2026-10-15** | **179/180 corridas válidas** (1 inválida, `no_requests`, excluida), 0 errores/timeouts; reanudada con `--resume` sin duplicar las 17 + 1 previas. **Cambia la conclusión de OE4:** dentro de una campaña única N = 10 es el más rápido (N = 20 vs N = 10: P95 ×1,15–1,36, throughput ×0,75–0,86; N = 30 vs N = 10: ×1,22–1,38 y ×0,68–0,79). La «no monotonicidad» de N8/N8b no se reproduce y es compatible con un **cambio de régimen del equipo** (≈ ×1,6 en throughput entre ejecuciones 1–17 y 18–180, igual para los tres N; N8 se parece al régimen anterior y N8b al posterior). Causa física del régimen **no aislada**. 18 corridas de N = 10 alcanzan ≥ 20 req/s (máx. 21,99) |
| Persistencia incremental | `RunJournal` + `--resume` + 7 pruebas; utilizada y verificada en N8b, N9b y N11 |
| Estado del arte | Conciliado: 49 + 2 = 51 (D2.6) + 6 (búsqueda estructurada) = 57; niveles L1–L4 por entrada; 0 con texto completo |
| Pruebas | 1 111 pasan (+7), 18 fallos y 5 errores = los mismos 23 preexistentes de N7 |

## 1. ¿Qué se midió realmente y qué resultados se obtuvieron?
| OE | Qué se midió | Resultado principal | Estado |
|---|---|---|---|
| OE1 | 13 indicadores RF/REL/RNF sobre 9 500 ciclos en proceso (14 condiciones) + sondas | RF01, RF02, RF04–RF06, REL-C, REL-D, RNF02 cumplidos; **RF03 8 600/9 500 = 90,5 %** (el 9,5 % restante es la ablación `sequential`; 8 600/8 600 con despacho concurrente); RNF01 1 319 ms agregado (solo en proceso); RNF04 14,98 req/s y RNF03 F1 < 0,85 **no cumplidos**; RNF05 sin medir. Asociación puntaje–T_conv/P95 ρ = −0,69 (n = 14), confundida con la carga | Parcial |
| OE2 | P95 y throughput HTTP, swarm vs `decision_table`, 4 cargas × 10 corridas (N2, 80) y réplica N9b (160, con `rules` y `bruteforce`); TTFC en proceso | P95 ×3,9 a ×21,7 y throughput ×0,058 a ×0,213 según sesión (8/8 significativas tras Holm en ambas); sin ventaja de eficiencia del swarm; **swarm ≈ bruteforce en P95** (n.s.); T_conv no comparable homogéneamente | Latencia/throughput: respondido; convergencia: no homogéneo |
| OE3 | Factorial completo 48 × 5 sobre T_conv, k_stop, brecha, mensajes | Despacho concurrente −37 % T_conv (η² 0,98); difusión g_best +13 ms/+11 mensajes sin mejora de calidad; heurística −iteraciones y −brecha; réplicas sin efecto práctico; interacciones relevantes (despacho×difusión, despacho×mecanismo, heurística×mecanismo) | Respondido (experimental) |
| OE4 | P95, T_conv HTTP, throughput en 6 cargas × N ∈ {10, 20, 30}: N8 + N8b (180 corridas) y N11 (179 válidas, una sola campaña aleatorizada); 0 errores/timeouts | Latencia lineal en la carga, meseta de throughput desde 5 usuarios; **en N11 (tramo B): N = 10 < N = 20 ≲ N = 30 en latencia** (N = 20 vs 10: P95 ×1,15–1,36; N = 30 vs 10: ×1,22–1,38; N = 30 vs 20: ×0,99–1,12, 2/6 cargas significativas); el contraste N8 vs N8b (N = 10 más lento que N = 20) está **confundido con un cambio de régimen del equipo (≈ ×1,6)**; 18 corridas de N = 10 alcanzan ≥ 20 req/s (máx. 21,99), no sostenido ni con N = 20/30; N = 10 cumple P95 < 2 s hasta 25 usuarios en el régimen B (1 890 ms), N = 20/30 hasta 10 | Respondido; la **causa del cambio de régimen no está aislada**; calidad de solución por N no medida en HTTP |
| OE5 | F1_adapt v3 (provisional) y SUS | F1 v3 = 0,8156 (< 0,85), reproducido exactamente; histórico v2 = 0,6407; SUS: 0 evaluadores | Precisión provisional; usabilidad **no determinada** |

## 2. Metas alcanzadas y no alcanzadas
Alcanzadas: RF01/02/04/05/06, REL-C/D, RNF02; estabilidad sin errores hasta 100 usuarios; P95 < 2 s hasta 10 usuarios. No alcanzadas: RNF03 (F1 0,6407 v2; 0,8156 v3 < 0,85), RNF04 (N8/N8b máx. 15,9 req/s; en N11 solo corridas aisladas de N = 10 llegan a ≥ 20 req/s, hasta 21,99, y las medias de celda rozan 20,0–20,1; no sostenido), RNF01 a ≥ 25 usuarios salvo N = 10 en el régimen B (media 1 890 ms; con N = 20/30 P95 ≥ 2,3 s). Sin medir: RNF05 (SUS > 75). Desfavorable: eficiencia frente a `decision_table`.

## 3. Significación estadística
Significativas tras Holm (unidad = corrida): las 8 diferencias de OE2; efectos principales y varias interacciones de OE3 (excepto réplicas); efecto de la carga y de N en OE4 (N = 30 vs 10). No significativas/sin efecto: difusión de g_best sobre k_stop y brecha, réplicas sobre T_conv (Holm p = 0,058), asociación puntaje–brecha/throughput en OE1. En todos los casos con efectos enormes y varianza mínima se priorizan razones, IC y tamaños de efecto.

## 4. Comparación con el estado del arte
Matriz: `ESTADO_DEL_ARTE_MATRIZ.csv` (49 referencias verificadas por DOI en Crossref; 43 con resumen leído) y `state_of_art/auditoria_referencias_existentes.csv` (63 referencias de la tesis: 48 DOI coinciden con autor y año; 8 libros/URL sin DOI; 4 con año distinto entre versión en línea e impresa (no constituye error); **3 no verificables o incorrectas**: Imran y Almusharraf 2024 —el DOI corresponde a una revisión sobre IA en K-12—, Lee, Park y Kang 2025 —DOI inexistente— y Liu et al. 2024 —DOI inexistente—). Clasificación: 0 directamente comparables, 6 comparables con reservas, 28 contextuales, 15 metodológicas. **Ninguna publicación reporta latencia, throughput o convergencia de un sistema multiagente educativo comparable**, por lo que no se fijó ninguna meta numérica a partir de la literatura; las cifras publicadas útiles son de contexto (p. ej. SUS medio 76,27 en LMS, 769 estudiantes; 72,1 y 70 en un sitio de programación). Se reúnen 63 + 21 candidatas ≈ 84 referencias, de las cuales solo las verificadas (48 + 21) deberían sostenerse; no se añadió ninguna sin verificar.

## 5. Defectos técnicos corregidos
1. `http_campaign`: la ventana mínima no cabía con respuestas > 5 s (N = 30, ≥ 50 usuarios); `--start-margin` + prueba de regresión (umbrales de ventana sin cambios; comportamiento por defecto histórico).
2. Cifra errónea «8200/8200» en N1/N7 (correcta: 8 600/8 600), documentada.
3. Protocolo: tareas paralelas de CPU contaminan campañas de carga; intento descartado y repetido.

## 6. Experimentos adicionales ejecutados
N8 (OE4, N = 10 y 30; 120 corridas), N8b (N = 20; 60), N9b (OE2 con rules y bruteforce; 160) completos; N9 original abortado en 38/160 (descartado); N11 (180) completada: 179 válidas + 1 inválida. Re-análisis independientes de OE1–OE3 y F1 v3.

## 7. Condiciones que siguen impidiendo resultados
1. Hardware objetivo 8 vCPU/32 GB sin acceso (no se afirma equivalencia del equipo local ni se creó infraestructura cloud).
2. SUS y panel: 0 evaluadores; consentimiento y versión en español del SUS sin validar.
3. Regla v3 no sellada; gold sin validar por el panel.
4. Aislar la **causa del cambio de régimen** (≈ ×1,6) observado en N11 requiere un diseño que lo controle (p. ej. alternar o aleatorizar el estado del host/Docker y muestrear CPU y memoria en todo momento); no se hizo y no se atribuye a ninguna causa.
5. Comparadores convencionales externos inexistentes; decisiones del asesor abiertas.

## 8. Control de calidad
- Pruebas `tests/adaptation_swarm` (con `test.env`, `PYTHONUTF8=1`; segunda ejecución tras la persistencia incremental: **1 111 pasan, 18 fallan, 5 errores, 6 omitidas**, log `pytest_adaptation_swarm_continuacion.log`; la primera dio 1 104 pasan con los mismos fallos): **1 104 pasan, 18 fallan, 5 errores, 6 omitidas** — el mismo conjunto de 23 fallos preexistentes de N7 (`test_cpp_render`, `test_agents_library`, `test_sprint_modules_safeguards`, uno en library_full_coverage/inventory/sandbox; entre ellos una falta de privilegio de symlink en Windows y la ausencia de Chrome/podman); 4 pruebas nuevas pasan. Sin `PYTHONUTF8` fallan 13 pruebas más por codificación de la consola cp1252 (artefacto de entorno). Logs: `pytest_adaptation_swarm*.log`.
- Reproducción: F1 v3 (0/1 000 discrepancias), recuentos de OE1, contrastes de OE2 (cifras idénticas a N2) y ANOVA de OE3 recalculados con scripts independientes.
- **Cierre de N11 (2026-10-15):** `sha256` verificado en N1–N7, N8, N8b, N9b y N11 (0 discrepancias, 0 ausentes). `SHA256SUMS` de este directorio se regeneró (337 archivos) tras actualizar los informes; los de N1–N7, N8b y N9b no se tocaron; el de N11 se regeneró (374 archivos) y el del estado parcial de 19 corridas se conserva como `SHA256SUMS_estado_parcial_19runs`. Pruebas de persistencia y margen de inicio (`test_oe_campaign_journal.py`, `test_oe_start_margin.py`) ejecutadas antes de reanudar: **11 pasan**; **no se repitió la suite completa `tests/adaptation_swarm` en esta fase** (el código de `http_campaign.py` no cambió respecto de la ejecución de 1 111 pasan / 18 fallos / 5 errores). Análisis N11 ejecutado con Python 3.12.10 (scipy 1.18.1, statsmodels 0.15.0, pandas 3.0.6), entorno recreado desde `requirements_analisis.txt`.
- Integridad: `SHA256SUMS` de este directorio (`sha256sum -c SHA256SUMS`); CSV con encabezado y filas completas (180/180 corridas N8+N4, 240/240 N3, 80/80 N2).
- Git: rama `exp/oe-validation-2026-10-13` desde `65e8c97`; cambios de código mínimos y sin confirmar (`oe/http_campaign.py`, `tests/adaptation_swarm/test_oe_start_margin.py`); los experimentos N1–N9 siguen sin versionar por decisión de no alterar el estado del usuario.
- Gráficos desde datos medidos: `oe2_reanalysis/oe2_latencia_throughput.png`, `oe3_reanalysis/oe3_efectos_marginales.png`, `oe4_nvar/oe4_nvar_carga_N.png`. No hay capturas de pantalla: no se ejecutó la interfaz.
- Decisiones estadísticas: unidad = corrida, log, Welch, Holm, Mann-Whitney complementario; **son decisiones técnicas del estudio, no aprobadas por el asesor**.

## 9. Índice de entregables y cómo reproducir (directorio `backend/experiments/oe_n8_2026-10-13/`)
| Entregable | Archivo |
|---|---|
| Auditoría | `AUDITORIA_EXPERIMENTAL_OE1_OE5.md` |
| Trazabilidad | `MATRIZ_TRAZABILIDAD_OE1_OE5.csv` |
| Estado del arte | `ESTADO_DEL_ARTE_MATRIZ.csv`, `state_of_art/` |
| Informes | `INFORME_RESULTADOS_OE1.md` … `OE5.md`, este consolidado |
| Datos | N8 `campaign/`; N8b `../oe_n10_2026-10-14_n20/campaign/`; N9b `../oe_n9b_2026-10-14/campaign_final/`; N11 `../oe_n11_2026-10-14_3N/campaign/` (+ `campaign.journal`, `campaign.journal_pre_resume_19runs.jsonl`, `memguard_tramoB.log`); recursos del host `recursos.csv` en N8b, N9b y N11 |
| Análisis | `scripts/`, `oe1_verify/`, `oe2_reanalysis/`, `oe2_aux/`, `oe3_reanalysis/`, `oe4_nvar/`, `oe5_f1_repro/`, `requirements_analisis.txt` |
| Estado del arte | `ESTADO_DEL_ARTE_MATRIZ.csv` (v2, 57), `ESTADO_DEL_ARTE_CONCILIACION.md`, `state_of_art/` (búsqueda estructurada, auditorías de referencias D2.5 y D2.6) |
| Evaluación humana | `PREPARACION_EVALUACION_HUMANA.md` |
Comandos: cada informe tiene su sección «Reproducción». Entorno de ejecución: `mas-run/.venv` (Python 3.12.10); análisis: Python 3.12 con numpy/scipy/pandas/statsmodels/matplotlib; servicios: `docker start adaptation_swarm_test_redis adaptation_swarm_test_postgres` y `source tests/adaptation_swarm/integration_env/test.env`.

## 10. Comandos de reproducción de la continuación
```
cd backend && source tests/adaptation_swarm/integration_env/test.env   # tras: docker start adaptation_swarm_test_redis adaptation_swarm_test_postgres
export SWARM_REQUIRE_LIBRARY=1 PYTHONUTF8=1
../.venv/Scripts/python.exe -m adaptation_swarm.oe.http_campaign oe4 --campaign-id n10-oe4-n20 --out-dir experiments/oe_n10_2026-10-14_n20/campaign --runs 10 --users 1,5,10,25,50,100 --particles 20 --start-margin 20
../.venv/Scripts/python.exe -m adaptation_swarm.oe.http_campaign oe2 --campaign-id n9b-oe2-aux --out-dir experiments/oe_n9b_2026-10-14/campaign --runs 10 --users 1,5,10,25 --systems swarm,decision_table,rules,bruteforce --start-margin 20   # (+ --resume sobre copia del diario)
cd experiments/oe_n8_2026-10-13 && <python análisis> scripts/oe4_nvar_analysis.py && <python análisis> scripts/oe2_aux_analysis.py
python scripts/busqueda_estructurada.py && python scripts/build_conciliacion.py && python scripts/audit_referencias.py <texto_tesis.txt> <salida.csv>
../../../.venv/Scripts/python.exe -m pytest -p no:cacheprovider -q tests/adaptation_swarm        # desde backend/, con test.env y PYTHONUTF8=1
```
