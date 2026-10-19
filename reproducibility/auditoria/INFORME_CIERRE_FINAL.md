# Informe de cierre de la auditoría (estado al 2026-10-19)

**La auditoría NO está cerrada.** Este informe separa lo comprobado, lo no comprobado y lo que requiere decisión académica. Rama `repro/auditoria-integral-2026-10-19`; los commits y ejecuciones exactos están en §5.

## 1. Estado de los cinco objetivos (criterios y umbrales de la tesis; no se inventó ningún índice ni regla)
| OE | Resultado observado | Umbral/meta de la tesis | Evidencia | Limitaciones | Conclusión admisible |
|---|---|---|---|---|---|
| **OE1** | 8 cifras en prosa y los valores y **estados** de RF01–RF05, REL-C, RNF01, RNF02 y RNF03 de la Tabla 37 recalculados desde los 9 500 ciclos de N1 (y K10 para RNF03); la Tabla 6 (incluida la fila «usuarios») coincide | RF = 100 %; REL-C ≥ 99 %; RNF01 P95 < 2 000 ms; RNF02 k_stop ≤ 15 ∧ CR ≥ 98 %; RNF03 F1 ≥ 0,85 | `oe1_verify.json`, `raw_observations.csv` de N1 | RF02–RF05 se apoyan en banderas por ciclo del arnés (su contenido no se conserva); RF06, REL-D, RNF04 y RNF05 no se recalculan; el puntaje de cumplimiento carece de definición aprobada (no se asigna un MET/NOT_MET global) | Cumplimiento **parcial** y descrito requisito a requisito; no hay un veredicto global del objetivo |
| **OE2** | La propuesta tuvo P95 de 3,9 a 21,7 veces el de `decision_table` (dos campañas) y throughput de 0,058 a 0,213 veces; frente a `bruteforce` el P95 es indistinguible (IC95 % incluye 1) y el throughput 1,13–1,51 veces (significativo con Holm en 5, 10 y 25 usuarios) | L_resp < 2,0 s (aporta a H1) | N2 y N9b recalculadas; rangos recalculados (M11–M14) | `decision_table` es un sistema convencional **definido operacionalmente por el estudio**, no un baseline externo validado; `rules` es una ablación y `bruteforce` una referencia de optimalidad; no oficial | Desempeño comparado **solo con ese comparador**; no hay evidencia de superioridad frente a sistemas convencionales externos |
| **OE3** | Ver §3: efectos de despacho, difusión de g_best, heurística y mecanismo sobre T_conv y calidad; CR = 100 % y k_stop máx. ≤ 8 en N3, N3-R y N3-S | CR ≥ 98 %; k_stop ≤ 15 | N3, N3-R y N3-S recalculadas desde 24 000 observaciones cada una | exploratorio, no oficial, N = 20, 1 usuario, un equipo, sin hipótesis formulada; T_conv absoluto depende de la sesión | **ABIERTO.** Efectos determinados y replicados en condiciones exploratorias; no cumplido en sentido confirmatorio/oficial |
| **OE4** | La latencia crece con la carga y con N; throughput 8–20 req/s según N y régimen; RNF01 se cumple hasta 10 usuarios en todas las corridas y con 25 solo con N = 10 en el tramo B (8 de 9); 20 req/s en 18 de 419 corridas | T_conv ≤ 15; L_resp < 2,0 s; throughput ≥ 20 req/s | N4, N8, N8b, N11 recalculadas (491 cifras) | hardware **local**; la condición objetivo (8 vCPU/32 GB en la nube) **no se ejecutó**; N11 tiene dos tramos con régimen distinto | Metas **no** cumplidas en lo medido; sin extrapolación a la infraestructura objetivo |
| **OE5** | F1_adapt = 0,8156 (v3 provisional; IC95 % 0,8111–0,8201) y 0,6407 (v2 histórico) | F1 ≥ 0,85; SUS > 75 con n ≥ 10 | N5 y K10 recalculadas | v3 provisional; perfiles sintéticos; **0 evaluadores SUS ni panel de expertos** (no se simulan) | La meta F1 **no se alcanza**; la usabilidad **no se midió** |

## 2. Resultados y límites de N3, N3-R y N3-S
- **N3** (2026-10-06), **N3-R** (2026-10-19, semillas nuevas) y **N3-S** (2026-10-19, mismas semillas que N3): mismo diseño (48 condiciones × 5 lotes × 100 perfiles = 24 000 observaciones cada una), exploratorias y no oficiales. La cadena observaciones→corridas coincide en las tres.
- **Tiempos absolutos.** T_conv (media geométrica): N3 71,7 ms; N3-R 60,4 ms; N3-S 60,3 ms. Cociente N3-S/N3 = 0,841 (IC95 0,820–0,862, t de 4 gl con los 5 lotes como bloques); N3-S/N3-R = 0,999. Está dentro del intervalo preespecificado para «la velocidad depende de la sesión» ([0,79; 0,89]) y fuera del de «depende de las semillas» ([0,95; 1,05]).
- **Sensibilidad (`oe3_sesion.json`).** El cociente es < 1 en los 5 lotes (0,87; 0,85; 0,83; 0,83; 0,83) y en las 48 condiciones (0,79–0,89). La permutación de signos entre lotes da p = 0,0625 (bilateral), **que es el mínimo posible con 5 lotes**: la potencia inferencial es limitada. En ambas sesiones T_conv sube con el número de lote (N3 ≈ +7 %, N3-S ≈ +2 %): hay una deriva dentro de la sesión.
- **Calidad.** Brecha, k_stop, mensajes y F de N3-S son idénticos a N3 en las 240 corridas (diferencia máxima 0): el arnés es determinista con las mismas semillas.
- **Lo que NO se demuestra.** La **causa** de la diferencia. No se atribuye a la carga del equipo (la de N3 no se registró) ni se descarta un cambio de código: los fingerprints de módulos son idénticos y la ruta en proceso no cambió entre `cec0e06` y `265a4f4`, pero eso no es una prueba. N3-S no puede separar «estado del equipo» de «versión del código».
- **Pre-registro.** `PRE_REGISTRO_N3S.md` se creó 15 s antes de lanzar N3-S (marcas de archivo y de `provenance.json`), pero **no se hizo commit antes de ejecutar**: es una pre-especificación local, sin sello externo. La sección de resultados se añadió después sin modificar el texto anterior.
- **Eficiencia y los seis contrastes (`oe3_eficiencia.py`).** Se usan los indicadores que la tesis ya define (iteraciones, ms, CR) más calidad y mensajes; **no hay índice compuesto**. Veredictos: despacho por lotes, sin difusión de g_best y con heurística «dominan»; mecanismo cognitivo frente a PSO es un «compromiso» (T_conv −17 %, k_stop −52 %, brecha +123 %); social frente a PSO y réplicas, sin diferencia relevante. El mismo veredicto sale en las tres campañas (6 de 6). **El umbral del 5 % se fijó después de conocer los efectos agregados de N3: no es un criterio independiente preregistrado**; lo independiente es que coincida en N3-R y N3-S. Los veredictos son descriptivos (cambios relativos de medias); los contrastes con pruebas formales (ANOVA de N3 con permutación; pruebas por rangos con Holm en `oe3_robustez.py`) son aparte, no de N3-S.
- **Hipótesis.** El OE3 no tiene hipótesis estadística aprobada en la tesis. **Propuesta, pendiente de aprobación académica y no preregistrada:** «las configuraciones con despacho por lotes, sin difusión de g_best y con heurística de arranque reducen T_conv sin empeorar la brecha frente a sus alternativas». No se ha usado en ningún análisis ni figura en la tesis.

## 3. Comprobaciones numéricas y prosa
- **1 038 comprobaciones** de tablas: 1 014 desde datos + 16 desde resultados derivados + 8 no reproducibles; 1 027 coinciden, 3 difieren una unidad por doble redondeo (Tabla 13) y **0 discrepancias**. Un cero de discrepancias significa «sin diferencias no explicadas dentro del alcance y las reglas de comparación», no que todo el documento esté verificado.
- **Nuevo en esta fase:** el recálculo de 18 valores y estados de requisitos de la Tabla 37 (RF01–RF05, REL-C, RNF01, RNF02 desde N1; RNF03 desde el resumen K10) con los umbrales de la propia tabla; y 4 afirmaciones de rangos del OE2 (M11–M14). Un control negativo (alterar `w_valid` en N1) hace fallar el verificador (código 5).
- **Los «cinco» no reproducibles son ahora ocho elementos más finos** porque la Tabla 37 se desglosó. Cada uno, con su motivo y lo que falta:
  | Elemento | Por qué no se reproduce | Qué falta |
  |---|---|---|
  | T6 Kendall τb «usuarios» | la tesis publica «no calculado»; no hay cifra que comparar (no es un fallo de reproducción) | nada, salvo calcularlo si se quisiera publicar |
  | T27 SUS y Tabla 35 | 0 evaluadores; no se simulan | aplicar el SUS a ≥ 10 evaluadores reales |
  | T37 RF06 | sonda de persistencia de 20 ciclos no conservada | el registro de la sonda |
  | T37 REL-D | sonda de determinismo (20 pares) solo consta en el informe del propio arnés | el registro de los pares |
  | T37 RNF04 | no está la mediana del throughput por lote en proceso de N1 | `batches.json` de N1 |
  | T37 RNF05 | sin SUS | idem SUS |
  | Tablas 32/44 | síntesis bibliográfica: depende de fuentes externas | acceso a cada fuente original |
- **Prosa:** 574 afirmaciones `PENDIENTE_DE_EVIDENCIA`, 865 `VERIFICACION_PARCIAL`, 77 coinciden (36 exactas + 41 con redondeo), 347 no aplica; celdas: 6 pendientes, 56 parciales, 2 no reproducibles. **El grueso de la prosa sigue sin revisarse oración por oración.** 217 de las parciales lo son solo porque el valor de diseño existe en un registro (verificación débil). Las verificaciones manuales M1–M14 recalculan **valores** y dejan escrita en cada fila la limitación de la oración (p. ej. «sin mejorar la calidad», «régimen del equipo»); ninguna oración completa se ha dado por verificada por esos medios.

## 4. DOCX
Original D2.9.7 `a6bb2934de7fd512…` intacto; copia corregida `1bd0894c9586e433…`. Cambian 5 párrafos y solo las cifras autorizadas (Tabla 13). Comparación automática de las 267 páginas exportadas con Word: el texto difiere solo en las páginas 105, 109 y 111 y la maquetación (posición de los bloques) es idéntica en todas. **Inspección visual: solo las páginas 105, 109 y 111;** el resto del documento no se leyó página a página. «Nuevo» es D2.9.3 (byte a byte) y no sustituye a D2.9.7.

## 5. Commits y ejecuciones
Ver `ESTADO_NOTEBOOKS_COLAB.csv` y `outputs/registro_ejecucion/COLAB_EJECUCION_OE1_OE5.md`. Los cambios de esta fase (T37, M11–M14, sensibilidad de N3-S) cambian `reproduce_results.py` y `oe3_sesion.py`, por lo que **los notebooks deben volver a ejecutarse en Colab sobre el commit que los contenga**; hasta que conste esa ejecución en el registro, no se afirma que lo estén.

## 6. Pendientes priorizados
**Bloqueos técnicos:** `batches.json` y sondas de N1 (RF06, REL-D, RNF04); revisión oración por oración de ≈ 1 440 afirmaciones en prosa (trabajo manual extenso); acceso a las fuentes de las Tablas 32/44.
**Requisitos metodológicos:** ejecución oficial del OE3/OE4 (hardware objetivo, ≥ 10 réplicas); datos reales de SUS y de expertos; regla aprobada del puntaje de cumplimiento (OE1).
**Decisiones de aprobación académica:** hipótesis estadística del OE3 (propuesta en §2); si N3-R y N3-S se incorporan a la tesis como cuadro de réplica; si se aprueba un índice compuesto de eficiencia; redacción de «el OE3 queda demostrado experimentalmente» (§7.1), más fuerte que la evidencia; privacidad: el repositorio es público y contiene el texto de las tablas (decisión ya tomada: se mantiene).

## 7. Cambios de esta fase y su validación
| Cambio | Archivos | Validación |
|---|---|---|
| Control N3-S, datos y análisis | `data/experiments/oe_n3s_2026-10-19/`, `scripts/oe3_sesion.py`, `PRE_REGISTRO_N3S.md` | cadena 240/240; prueba `test_oe3_sesion_…` y control negativo |
| Sensibilidad de N3-S y límites | `scripts/oe3_sesion.py`, `outputs/oe3_sesion.json` | ejecución local |
| Eficiencia con indicadores de la tesis | `scripts/oe3_eficiencia.py` | prueba `test_oe3_eficiencia_…` |
| Tabla 6 «usuarios», Tabla 27 por perfil | `scripts/reproduce_results.py` | `test_tabla6_usuarios_y_tabla27_…` |
| Tabla 37: valores y estados desde N1 | `scripts/reproduce_results.py` | `test_estados_de_requisitos_de_la_tabla_37_…` (incluye alteración de N1) |
| Rangos del OE2 (M11–M14) | `scripts/verificacion_manual_conclusiones.py` | `VERIFICACION_MANUAL.csv` |
| Regeneración de conciliación, conteo, trazabilidad y mapa | `auditoria/*`, `RESULTS_TRACEABILITY.csv` | scripts de generación y pruebas |
