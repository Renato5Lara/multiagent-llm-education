# Propuesta de correcciones prudentes de las conclusiones (NO aplicadas al DOCX)

Son **propuestas** para el autor/asesor, no cambios aprobados; el documento canónico (copia corregida de D2.9.7) y el original no se han tocado. Cada una cita el texto original, el texto propuesto y la evidencia. Ninguna modifica objetivos, hipótesis, umbrales ni resultados. Los identificadores A## remiten a `REGISTRO_AFIRMACIONES_PRIORITARIAS.csv`.

## C1 — Conclusión del OE3 «demostrado» (A21, A93, A94, A95) — aparece en 4 lugares: resumen (párr. 57), abstract en inglés (párr. 65), §6.7 (párr. 2066) y §7.1 (párr. 2093)
**Original:** «El OE3 queda demostrado experimentalmente bajo las condiciones ejecutadas (diseño factorial de 48 condiciones; 1 usuario; N = 20; 5 corridas por condición).»
**Problema:** «demostrado» excede la evidencia: campaña exploratoria y no oficial, un solo equipo, sin hipótesis estadística aprobada y sin ejecución oficial.
**Propuesta:** «Los resultados de la campaña exploratoria N3 permiten caracterizar el efecto de la configuración interna sobre el tiempo de convergencia y la calidad en las condiciones ejecutadas (diseño factorial de 48 condiciones; 1 usuario; N = 20; 5 corridas por condición); el OE3 permanece pendiente de la ejecución oficial.»
**Evidencia:** N3 (Tablas 13–14) y, en el apartado complementario, N3-R y N3-S (ver C5).

## C2 — Conclusión del OE4 «demostrado»/«se cumplió» (A27, A71, A93, A94, A96) — aparece en 5 lugares: resumen (57), abstract en inglés (65), §6.5.4 (1758), §6.7 (2072) y §7.1 (2095)
**Original:** «El OE4 queda demostrado experimentalmente bajo las condiciones ejecutadas (seis cargas de 1 a 100 usuarios; N = 10, 20 y 30; 419 corridas HTTP válidas, sin errores ni timeouts).»
**Propuesta:** «Los resultados de las campañas exploratorias N4, N8, N8b y N11 caracterizan el desempeño computacional en el equipo local bajo las condiciones ejecutadas (seis cargas de 1 a 100 usuarios; N = 10, 20 y 30; 419 corridas HTTP válidas, sin errores ni timeouts); no permiten afirmar el cumplimiento de las metas en el hardware objetivo, que no se ejecutó.»

## C3 — §7.1, Conclusión del OE2 (A19)
**Original:** «frente a rules, ablación del propio sistema, el resultado fue equivalente.»
**Propuesta:** «frente a rules, ablación del propio sistema, el resultado fue similar (mismas diferencias significativas y razones de magnitud comparable; no se ejecutó una prueba de equivalencia).»

## C4 — Resumen y §6.5.4, «el despacho concurrente redujo el tiempo de convergencia en torno a 37 %» (A05)
**Alcance:** la cifra aparece en **10 lugares** (resumen, abstract en inglés, §6.5.4, §6.5.5, §6.5.6, §6.7 ×3, §7.1 y un anexo): inventario en [`EFECTO_DESPACHO_MENCIONES.csv`](EFECTO_DESPACHO_MENCIONES.csv).
**Propuesta (resumen):** «El despacho concurrente redujo el tiempo de convergencia en torno a 37 % en la campaña N3; en dos campañas posteriores con el mismo diseño la reducción fue de ≈ 32 %, de modo que su sentido es estable y su magnitud depende de la sesión de ejecución.» En los demás lugares, añadir «en N3» (o «(N3)» en tablas y anexos). No se promedian las campañas.
**Evidencia:** N3 37,4 %; N3-R 32,2 %; N3-S 32,5 % (`outputs/oe3_replicacion.json`, `oe3_sesion.json`).

## C5 — Apartado complementario «Réplica exploratoria del OE3» (si el formato lo permite)
Texto sugerido (resultados exploratorios, no oficiales, no mezclados con N3): «Se ejecutaron dos campañas adicionales con el mismo diseño: N3-R (semillas nuevas) y N3-S (las mismas semillas que N3). Los 21 efectos principales evaluados mantuvieron su sentido, y la brecha, `k_stop`, el número de mensajes y F de N3-S fueron idénticos a los de N3. El T_conv absoluto de N3-R y N3-S fue ≈ 16 % menor que el de N3 (cociente 0,84; IC95 % 0,82–0,86), de modo que la velocidad absoluta depende de la sesión de ejecución; la causa no se identificó. El despacho por lotes, la ausencia de difusión de g_best y la heurística de arranque mejoraron T_conv sin empeorar la calidad en las tres campañas; el mecanismo cognitivo fue más rápido con más del doble de brecha.»
**Aviso:** la regla de clasificación de contrastes (umbral del 5 %) se fijó conociendo los efectos agregados de N3; no es un criterio preregistrado.

## C6 — Resumen, «cumplió los requerimientos funcionales y de confiabilidad» (A02)
**Propuesta:** añadir la salvedad «según el informe del arnés para RF06 y REL-D, cuyos registros no se conservan entre los datos publicados».

## C7 — §6.5.3, párrafo «Cautela sobre el mecanismo cognitivo» (A40, A42)
**Original:** «su menor T_conv (65,7 ms frente a 78,8 ms con PSO) … el promedio marginal de la difusión de g_best (−16 %: 68,0 frente a 80,8 ms al omitirla)».
**Problemas:** (a) la media aritmética de T_conv con PSO en N3 es 78,74832635 ms (`oe3_marginales.csv`), que se redondea a **78,7**; el «78,8» ya figura en el informe del propio proyecto (`INFORME_RESULTADOS_OE3.md`), de donde la tesis lo transcribió; una causa de doble redondeo es plausible pero **no demostrable** (no existe el intermedio 78,75 en ningún archivo): discrepancia abierta; (b) «68,0 frente a 80,8 ms al omitirla» puede leerse con el orden invertido (68,0 es el valor sin difusión).
**Propuesta:** «(65,7 ms frente a 78,7 ms con PSO; medias aritméticas)» y «(−16 %: 68,0 ms sin difusión frente a 80,8 ms con difusión)».
**Evidencia:** `runs_oe3.csv` de N3 (medias aritméticas por mecanismo y por nivel de difusión).

## C8 — «PSO y social fueron equivalentes» (A47)
**Propuesta:** como C3: «similares (no se ejecutó una prueba de equivalencia)».

## C12 — «prerregistro y sellado» (§5.8; A101, A104, INVENTARIO_PRERREGISTRO.csv)
**Hallazgo:** ninguna corrida oficial se ha ejecutado; las campañas N1–N11 tienen especificación versionada (hash en `provenance.json`, fecha en Git) pero registrada como decisión interna no aprobada por el asesor, y la regla v3 no está sellada. La semilla 26092601 se fijó en Git (2026-09-27) antes de K = 10 v2 y se reutilizó después. Las frases sobre el procedimiento de las corridas oficiales son correctas (son prospectivas); la de §5.8 («la validez del estudio se resguarda mediante el prerregistro y el sellado de cada especificación antes de su ejecución») parece describir lo ejecutado.
**Propuesta (aplicada a la copia de revisión como R9):** «…mediante la especificación versionada de cada campaña (identificada por hash y fecha en el control de versiones) y, para las corridas oficiales, mediante el prerregistro y el sellado de la especificación antes de su ejecución».
**Distinción que debe mantenerse:** planificación interna previa con fecha en Git ≠ especificación documentada y versionada ≠ prerregistro independiente (ninguno existe).

## C11 — «análisis independiente» (A97, A98) — aplicada a la copia de revisión (R10, R11, R12)
**Hallazgo:** el resumen (párr. 55), §5.8 (724) y §6.6 (2031, 2043) hablan de reproducción/análisis «independiente»; fue hecho por el propio proyecto (independiente del código del artefacto, no de terceros), y §5.8 afirma «prerregistro y sellado de cada especificación» mientras las campañas registran decisiones internas no aprobadas por el asesor y la regla v3 no está sellada.
**Propuesta:** «reproducidas con un análisis independiente del código del artefacto, realizado por el propio proyecto» y precisar qué especificaciones están selladas.

## C9 — §6.5.5, «Sus medias difieren de las de la Tabla 13 en menos de 1,3 %… una diferencia cuyo origen no se identificó» (A59, D4)
**Hallazgo:** el origen sí es identificable: las medias del reanálisis (ANOVA tipo II y de rangos) son **medias aritméticas** de T_conv y la Tabla 13 informa **medias geométricas**. La diferencia relativa va del 0,6 % al 3,8 % (despacho: 1,4 % y 0,6 %; difusión, heurística, réplicas y mecanismo: 2,9–3,8 %), de modo que «menos de 1,3 %» no se cumple para 10 de los 11 niveles.
**Propuesta:** «Las medias del reanálisis son medias aritméticas de T_conv y las de la Tabla 13 son medias geométricas; difieren entre el 0,6 % y el 3,8 % según el nivel (despacho por lotes 57,5 frente a 56,8 ms; secuencial 91,2 frente a 90,6 ms), diferencia esperable porque los tiempos son positivos y asimétricos; no cambia el sentido ni el orden de ningún contraste (los efectos relativos difieren en menos de 1,3 puntos porcentuales).»
**Verificación de «no afecta a ninguna conclusión»:** con ambos estadísticos el signo y el orden de los 6 contrastes principales coinciden; la mayor diferencia en un efecto relativo es 1,26 puntos (despacho secuencial +58,4 % con medias aritméticas frente a +59,7 % con geométricas); la significación de los contrastes se conserva según la tesis (reanálisis de rangos; no se recalculó aquí salvo el caso límite de las réplicas).
**Evidencia:** `outputs/tables/oe3_medias_aritmeticas_vs_geometricas.csv`, `scripts/oe3_medias_aritmeticas_vs_geometricas.py`.

## C10 — §6.7, «a cambio de una pérdida pequeña de aptitud» (A51, D5)
**Hallazgo:** la brecha respecto del óptimo es 0,0118–0,0428 en N3 (idéntica en N3-S; 0,0117–0,0431 en N3-R), es decir ≈ 2,4 % de la aptitud óptima media en la configuración de referencia y ≈ 8,7 % en la peor condición. La tesis no define un umbral para llamar «pequeña» a una brecha, y la brecha (N3, en proceso, 1 usuario) y el throughput (N9b, HTTP) proceden de campañas distintas.
**Propuesta:** «Frente a la búsqueda exhaustiva, la propuesta alcanzó entre 1,13 y 1,51 veces su throughput en la campaña HTTP N9b; en la campaña en proceso N3 su brecha respecto del óptimo fue de 0,012 a 0,043 (≈ 2 % a 9 % de la aptitud óptima media). Estas dos magnitudes proceden de campañas distintas y no permiten afirmar una relación de compromiso ni que la pérdida sea pequeña según un criterio definido.»

## Hipótesis propuesta para el OE3 (pendiente de aprobación; no preregistrada)
«Las configuraciones con despacho por lotes, sin difusión de g_best y con heurística de arranque reducen T_conv sin empeorar la brecha frente a sus alternativas.» No se usó en ningún análisis ni aparece en la tesis.

## Fase 15 — nuevas propuestas (ver `MATRIZ_EVIDENCIA_CONCLUSIONES.csv`)
**C13 (A, aplicada en V2).** Resumen y abstract: «cumplió los requerimientos funcionales y de confiabilidad» incluye RF07 y RF08, que la Tabla 5 declara «no evaluados como requisito», y RF06 y REL-D, que solo constan en el informe del arnés. Redacción: «cumplió RF01 a RF05 y REL-C… (RF06 y REL-D según el informe del arnés…; RF07 y RF08 no se evaluaron como requisitos)». Evidencia: A02, A76, A112, A113.
**C14 (A, aplicada en V2).** «solo con N = 10 en un régimen del equipo» → añadir «(8 de 9 corridas)»: la cifra está en §7.1 y la hipótesis general (A109).
**C15 (A, aplicada en V2).** §7.1 OE1: «se cumplieron RF01, RF02, RF04 a RF06, REL-C, REL-D y RNF02» mezcla seis requisitos recalculados con dos que solo constan en el informe del arnés; además RNF02 exige una tasa de convergencia sin regla de agregación (A112).
**C16–C21 (A, aplicadas en V2).** «triviales» → «simples»; «capacidad casi fija» → «dentro de cada sesión»; «señala» → «es compatible con»; «validada previamente» → «validada técnicamente de antemano»; «unos 2 ms» → 2,6 ms de promedio (1,3–5,8 ms) en N3; «sin CPU» → «sin CPU del sistema». Ver el registro de cambios V2 para el texto exacto y la evidencia.
**C22 (C, no aplicada).** OE5: el objetivo exige evaluación de expertos y docentes (no hubo ninguna) y contraste del SUS; solo existe el F1 v3 automático y provisional. «Se cumple de forma parcial y provisional» sugiere que se cumplió la mitad; propuesta: «El OE5 no se cumple: solo se midió provisionalmente el F1 (0,8156) con un gold sin validar» (A120). Decisión del autor o asesor.
**C23 (C, no aplicada).** OE2: el objetivo literal compara con «sistemas convencionales»; la evidencia es un solo comparador operativo (`decision_table`) y dos contrastes auxiliares (A115, A123). Propuesta: «frente a un comparador convencional operativo definido por el estudio».
**C24 (C, no aplicada).** OE3: la conclusión no menciona que N3-R y N3-S son ≈ 16 % más rápidas que N3 con las mismas condiciones (N3-S/N3 = 0,8406; IC95 % 0,820–0,862; A124). Relacionada con C4 y C5.

## Fase 16 — nuevas propuestas (ver `INFORME_FASE16.md`)
**C25 (A, aplicada en V3).** §6.4.3 (N8) y Tabla 26: «p de Holm ≤ 7 × 10⁻⁹ en todas las cargas» y «≤ 5 × 10⁻¹¹» contradicen la Tabla 19 (la columna «mayor p de Holm» se reproduce exactamente: máx. 2,09 × 10⁻⁷ en el P95 y 1,54 × 10⁻¹⁰ en el throughput). Redacción: «≤ 2,1 × 10⁻⁷» y «≤ 1,5 × 10⁻¹⁰» (A125).
**C26 (A, aplicada en V3).** §4.4: «consumo de CPU y memoria … no se reportan en los resultados de las campañas» → «… no se reportan como resultados de los objetivos (salvo la memoria y la CPU del equipo en el diagnóstico del régimen de N11)» (A128).
**C27 (B, no aplicada).** §6.5.3 y B5.3: «Es una desalineación de diseño … y no un defecto de implementación, pues el F1 se reproduce exactamente». La reproducción exacta verifica el cálculo de la métrica; no verifica la función de aptitud ni el optimizador. Alternativa: «es compatible con una desalineación de diseño (la aptitud combina términos que el gold no contiene); no se descarta un defecto del optimizador, que no se evaluó» (A126). Decisión metodológica del autor.
**C28 (B/C, no aplicada).** §6.7: «las brechas parcialmente cerradas corresponden … a la selección conjunta con criterios multiobjetivo (B3.2)». B3.2 trata de protocolos asíncronos; la evidencia es el despacho concurrente, no la función de aptitud. Alternativa: eliminar la correspondencia o justificarla (A127).
**C29 (C, no aplicada).** Anexo 7: Benjamini y Hochberg (1995) y Efron (1979) figuran en la Tabla 44 sin entrada en la lista de referencias ni cita en el cuerpo; el texto no usa FDR ni bootstrap. Alternativas: añadirlas a la lista (si se usan) o quitarlas del anexo (A129).
**C30 (B, pendiente).** 45 filas del Anexo 7 («texto completo») traen cifras que no están en los resúmenes públicos, y las cifras de §1 (Watson y Li, 2014; Bennedsen y Caspersen, 2019) tampoco; solo se contrastaron con el texto completo Li et al. (2023) y, en parte, López-Goyez et al. (2026). Pendiente: contrastar las citadas en la discusión (Subiyantoro, Koca, Isal, Srinivas, Ukenova, Dinh, Liu, Tan, Mohamedhen, Watson y Li) (A131, A140, A142).
