# AUDITORÍA EXPERIMENTAL OE1–OE5 (2026-10-13)

Auditoría inicial de solo lectura (Fase A) + control de calidad (Fase G). Todo lo afirmado está contrastado con archivos del repositorio; lo no verificado se marca como tal.

## 1. Repositorio de trabajo y estado Git
| Copia | Rama / HEAD | Contenido |
|---|---|---|
| `Aplicacion_Proyecto/mas-run` | `feat/adaptation-swarm-poc` @ `65e8c97` (2026-10-06) | **Repositorio de trabajo**: contiene las campañas N1–N7 (sin versionar), los guards oficiales y `oe/http_campaign.py` |
| `Aplicacion_Proyecto/multiagent-llm-education` | `feat/adaptation-swarm-poc` @ `fa858c2` (2026-10-01) | Anterior: sin N1–N7 ni la capa de campañas HTTP; 55 archivos modificados/sin seguimiento del usuario |
| `Aplicacion_Proyecto/mas-clean` | `env/windows-validation` @ `fa858c2` | Copia de validación de entorno |

Trabajo de esta sesión: rama **`exp/oe-validation-2026-10-13`** creada desde `65e8c97` en `mas-run` (los archivos sin seguimiento del usuario —N1–N7 y pilotos— se conservan intactos). No se borró ni sobrescribió ningún experimento histórico. No se modificó ningún documento de tesis.

Otras ubicaciones consultadas: `Docuemento de tesis/` (versiones de la tesis hasta D2.5 del 2026-10-13, `Asesoria.docx`, decisiones del asesor, `AUDITORIA-ETIQUETAS-PENDIENTE-D2.5`), `Auditoria Tesis/`, `Biblioteca sellada 2026-09-24/` (10 versiones con `SHA256SUMS`).

## 2. Arquitectura, algoritmo y definiciones
- **Agentes:** AG0 orquestador (LangGraph) + PSO; AG1 vector W (perfil); AG2 código; AG3 diagrama; AG4 texto + audio (TTS); bus Redis Streams; persistencia PostgreSQL (`adaptation_swarm/agents`, `bus`, `graph`, `persistence`).
- **PSO discreto** (`pso/`): espacio S ∈ {0,1,2}^8 = 6 561 configuraciones (énfasis e_m y variante v_m por modalidad code/diagram/text/audio); N = 20, w = 0,729, c1 = c2 = 1,494, ε = 0,001, k_max = 15; parada literal (Δ𝓕 < ε).
- **Aptitud 𝓕** (`fitness/`): α/β/γ/δ = 0,40/0,30/0,15/0,15 sobre Simil, Coher, Redund, CostT.
- **Inclusión (P1):** `e_m ≥ 1 ∧ 5·e_m ≥ Σe`. **Gold (P2):** matriz por arquetipo (`gold/rubric_v3.py`). F1 por caso (Dice) y media por caso.
- **Comparador operacional del estudio:** `baselines/decision_table.py` (tabla de decisión estática). **No es una referencia establecida por terceros**; `rules` (ablación del enjambre) y `bruteforce` (óptimo de referencia) son contrastes auxiliares, no comparadores convencionales (`oe/campaign_spec.py`).

## 3. Inventario de evidencia (ejecutado / calculado / reproducible / faltante)
| Evidencia | Estado | Ubicación |
|---|---|---|
| Corridas PoC congeladas `corrida-poc-1/2` (F1 de la PoC = 0,8031, definición previa) | Histórico, conservado | `backend/experiments/evidence_package_*` |
| F1 K = 10 **v2** = 0,6407048 | Histórico, conservado | `backend/official_runs/k10_*_2026-09-27` |
| N1 OE1 (9 500 ciclos en proceso) | Ejecutado; **reproducible** (recuentos reverificados) | `oe_n1_2026-10-05/` |
| N2 OE2 (80 corridas HTTP + 20 000 ciclos en proceso) | Ejecutado; **reproducido** (re-análisis independiente) | `oe_n2_2026-10-05/` |
| N3 OE3 (240 corridas) | Ejecutado; **reproducido** | `oe_n3_2026-10-06/` |
| N4 OE4 (60 corridas HTTP, N = 20) | Ejecutado | `oe_n4_2026-10-06/` |
| N5 OE5 F1 v3 provisional | Ejecutado; **reproducido exactamente** | `oe_n5_2026-10-06/` |
| N6/N7 consolidaciones | Calculado (con una cifra errónea de OE1, ver §5) | `oe_n6_*`, `oe_n7_*` |
| N8 (esta sesión): OE4 con N = 10 y N = 30 | **Ejecutado, completo** (120/120 corridas, 0 errores/timeouts) | `oe_n8_2026-10-13/campaign/` |
| N9 original: OE2 con `rules` y `bruteforce` | **Abortado en la corrida 38/160**; descartado (estado «incompleto») | `oe_n9_2026-10-13/campaign.tmp-raw/` |
| N8b (continuación): OE4 con N = 20 | **Ejecutado, completo** (60/60) | `oe_n10_2026-10-14_n20/` |
| N9b (continuación): OE2 con `rules` y `bruteforce` | **Ejecutado, completo** (160/160; 1 corrida repetida con `--resume`) | `oe_n9b_2026-10-14/campaign_final/` |
| N11 (continuación): OE4, tres N aleatorizados | **Completo** (179/180 válidas; 1 inválida `no_requests` excluida; 0 errores/timeouts; dos tramos de ejecución: 1–17 y 18–180 con `--resume`) | `oe_n11_2026-10-14_3N/`; análisis `oe4_n11/` |
| SUS / panel del gold | **No existe** (0 respuestas) | `oe_n5_2026-10-06/instrumento/` |
| Hardware objetivo 8 vCPU / 32 GB | **No disponible** | — |

## 4. Hardware
Equipo local: Intel i7-12700K (20 hilos lógicos), 31,7 GiB, Windows 11 Pro; Redis 7 y PostgreSQL 16 en contenedores Docker aislados (puertos 56379/55432); Python 3.12.10. **No es el hardware objetivo (8 vCPU / 32 GB)**, el generador de carga (Locust) comparte host con el servidor y no se tuvo acceso a ninguna infraestructura cloud: toda ejecución es *técnicamente compatible, P6 pendiente* y **no oficial**.

## 5. Hallazgos y correcciones
| # | Hallazgo | Evidencia | Acción |
|---|---|---|---|
| H1 | N1 `RESULTADO_OE1.md` y N7 `RESUMEN_FINAL_ESTUDIO.md` dicen «8200/8200 ciclos con despacho concurrente». El recuento correcto es **8 600/8 600** (5 400 + 3 200); 8 600/9 500 son los ciclos con solape en total | `scripts/oe1_verify.py` → `oe1_verify/oe1_verify.json`; `oe1_report.json` | Corregido en `INFORME_RESULTADOS_OE1.md`; los archivos históricos no se editaron |
| H2 | **Defecto de medición (código):** en `http_campaign`, la duración total de Locust = calentamiento + ventana + margen fijo de 5 s, y la ventana se mide desde la primera respuesta. Si la primera respuesta tarda más que el margen (N = 30 con 50–100 usuarios) la ventana de 60 s no cabe y la corrida sale `invalid_window_shorter_than_min`, sin importar el desempeño | Intento 1 de N8 (`_n8_failed_attempt1_margin5/`): 1ª corrida N = 30/50 usuarios con ventana 57,9 s | Nuevo parámetro `--start-margin` (por defecto 5,0 = comportamiento histórico) que amplía solo el tiempo total; umbrales de ventana (≥ 10 s de calentamiento, ≥ 60 s de ventana) **sin cambios**; prueba de regresión `tests/adaptation_swarm/test_oe_start_margin.py` |
| H3 | **Protocolo:** ejecutar tareas de CPU en paralelo (instalación de paquetes, ANOVA) mientras corre una campaña de carga distorsiona la latencia: el monitor de saturación solo mira la CPU de Locust, no la contención del servidor. En el intento 2 de N8, N = 10 salió más lento que N = 20 | `_n8_discarded_attempt2_cpu_contention/` | Resultados descartados (conservados, no usados); la campaña se repitió sin carga concurrente |
| H4 | Inconsistencia documental sobre la regla v3: el docstring de `gold/rubric_v3.py` indica P1/P2 aprobadas el 28/09/2026 pero `APPROVED_RULE_VERSIONS` está vacío y N5/N7 las tratan como no aprobadas | `gold/rubric_v3.py` vs `RESULTADO_OE5.md` | No se afirma aprobación; el F1 v3 sigue **provisional** |
| H5 | Desalineación aptitud–métrica: ρ(𝓕, F1 por caso) = 0,08 global, negativo en 3 de 4 arquetipos | `oe5_f1_repro/alineacion_aptitud_f1.json` | Solo diagnóstico; no se cambió 𝓕 ni el gold (sería post-hoc) |
| H6 | Referencias de la tesis (63): 3 no verificables/incorrectas (Imran y Almusharraf 2024: el DOI corresponde a otro artículo; Lee, Park y Kang 2025: DOI inexistente en Crossref y sin coincidencia por título; Liu et al. 2024: DOI inexistente en Crossref; el artículo similar encontrado es de otros autores, 2025) | `state_of_art/auditoria_referencias_existentes.csv` | Informado; **no se modificó la tesis**. Requieren comprobación manual |
| H7 | Cifra menor de N3: batch/sequential 56,8/90,6 ms (informe) vs 57,5/91,2 ms (recalculado, ≤ 1,3 %) | `oe3_reanalysis/` | Anotado en el informe de OE3 |
| H9 | **Anomalía parcialmente resuelta:** N = 10 (N8) es más lento que N = 20 (N8b) (×1,4 P95) entre campañas, pero en N11 (una campaña) N = 10 es **más rápido** que N = 20 (P95 ×1,15–1,36 a favor de N = 10, 5/6 cargas significativas). N11 contiene un cambio de régimen (≈ ×1,6 throughput entre ejecuciones 1–17 y 18–180, igual para los tres N); N8 se parece al régimen anterior y N8b al posterior. Compatible con confusión entre campañas; **la causa física del régimen no está aislada** (memoria libre 9,2 → 11,9 GiB medios y reinicio de Docker son candidatos, no probados) y la clasificación es post hoc | `oe4_n11/*.csv`, `oe4_nvar/*.csv` | Aislarla exige un diseño que controle el régimen; no ejecutado |
| H10 | La campaña HTTP escribía sus resultados solo al terminar; un fallo a mitad (N9, corrida 38) perdió los 37 registros medidos | `oe_n9_2026-10-13/campaign.log` | **Corregido** en la continuación: `RunJournal` (diario atómico con fsync, estados completed/invalid/failed/interrupted), una corrida fallida ya no aborta la campaña, `--resume` sin duplicados; 7 pruebas (`test_oe_campaign_journal.py`) |
| H11 | D2.6 (Anexo 7) declara 51 publicaciones y el registro posterior 49 | `ESTADO_DEL_ARTE_CONCILIACION.md` | 49 + 2 (Zheng 2025, Yu 2024) = 51; la matriz v2 agrega 6 de la búsqueda estructurada = 57; niveles de verificación por entrada |
| H12 | El `decision_table` varía entre sesiones (N9b vs N2: P95 ×1,15–1,55; throughput ×0,66–0,76) mientras el swarm es estable (0,95–1,06) | `oe2_aux/oe2_consistencia_N9b_vs_N2.csv` | Las razones swarm/convencional se informan por sesión |
| H8 | Las pruebas históricas fallan sin las variables de entorno del entorno aislado (`test.env`); con ellas pasan | 3 pruebas de `test_oe2_phase_c.py` | Se ejecutan siempre con `test.env` |

## 6. Decisiones metodológicas adoptadas en esta sesión (criterio técnico; **no** son aprobaciones del asesor)
1. Unidad estadística = **corrida** (sin pseudorreplicación por petición), igual que N2–N4; escala log para latencia/throughput.
2. N8 repite el protocolo de N4 (10 corridas por carga, calentamiento 10 s + ventana 60 s, persistencia OFF, política `reuse`) con N ∈ {10, 30} y `--start-margin 20`, que solo alarga el tiempo total a 90 s.
3. Los resultados de N8 se analizan junto con los de N4 (N = 20) como diseño factorial carga × N con 10 corridas por celda; las diferencias de duración total (75 s vs 90 s) se documentan como diferencia de protocolo y no afectan la ventana de medición.
4. Para el comparador de OE2 solo se usa `decision_table` como comparador convencional operacional; `rules` y `bruteforce` (N9) se reportan como contrastes auxiliares descriptivos, con sus propias familias de pruebas.
5. No se creó ningún comparador adicional ni se simularon participantes.

## 7. Limitaciones que impiden resultados oficiales
Hardware objetivo (P6) no disponible; sin evaluadores (SUS, panel); regla v3 no sellada; comparador convencional único y simple; decisiones del asesor abiertas (estadístico de latencia, B1, B5, B13, hipótesis formal); `T_conv` y el tiempo operacional hasta la configuración final no son equivalentes.

## 8. Control de calidad
Ver `INFORME_RESULTADOS_CONSOLIDADO.md` §«Control de calidad» (pruebas, integridad CSV/JSON, SHA-256).
