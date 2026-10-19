# Propuesta de correcciones prudentes de las conclusiones (NO aplicadas al DOCX)

Son **propuestas** para el autor/asesor, no cambios aprobados; el documento canónico (copia corregida de D2.9.7) y el original no se han tocado. Cada una cita el texto original, el texto propuesto y la evidencia. Ninguna modifica objetivos, hipótesis, umbrales ni resultados. Los identificadores A## remiten a `REGISTRO_AFIRMACIONES_PRIORITARIAS.csv`.

## C1 — §7.1, Conclusión del OE3 (A21)
**Original:** «El OE3 queda demostrado experimentalmente bajo las condiciones ejecutadas (diseño factorial de 48 condiciones; 1 usuario; N = 20; 5 corridas por condición).»
**Problema:** «demostrado» excede la evidencia: campaña exploratoria y no oficial, un solo equipo, sin hipótesis estadística aprobada y sin ejecución oficial.
**Propuesta:** «Los resultados de la campaña exploratoria N3 permiten caracterizar el efecto de la configuración interna sobre el tiempo de convergencia y la calidad en las condiciones ejecutadas (diseño factorial de 48 condiciones; 1 usuario; N = 20; 5 corridas por condición); el OE3 permanece pendiente de la ejecución oficial.»
**Evidencia:** N3 (Tablas 13–14) y, en el apartado complementario, N3-R y N3-S (ver C5).

## C2 — §7.1, Conclusión del OE4 (A27)
**Original:** «El OE4 queda demostrado experimentalmente bajo las condiciones ejecutadas (seis cargas de 1 a 100 usuarios; N = 10, 20 y 30; 419 corridas HTTP válidas, sin errores ni timeouts).»
**Propuesta:** «Los resultados de las campañas exploratorias N4, N8, N8b y N11 caracterizan el desempeño computacional en el equipo local bajo las condiciones ejecutadas (seis cargas de 1 a 100 usuarios; N = 10, 20 y 30; 419 corridas HTTP válidas, sin errores ni timeouts); no permiten afirmar el cumplimiento de las metas en el hardware objetivo, que no se ejecutó.»

## C3 — §7.1, Conclusión del OE2 (A19)
**Original:** «frente a rules, ablación del propio sistema, el resultado fue equivalente.»
**Propuesta:** «frente a rules, ablación del propio sistema, el resultado fue similar (mismas diferencias significativas y razones de magnitud comparable; no se ejecutó una prueba de equivalencia).»

## C4 — Resumen y §6.5.4, «el despacho concurrente redujo el tiempo de convergencia en torno a 37 %» (A05)
**Propuesta:** añadir «en N3» y una nota: «en réplicas posteriores (N3-R y N3-S) la reducción fue de ≈ 32 %».
**Evidencia:** N3 37,4 %; N3-R 32,2 %; N3-S 32,5 % (`outputs/oe3_replicacion.json`, `oe3_sesion.json`).

## C5 — Apartado complementario «Réplica exploratoria del OE3» (si el formato lo permite)
Texto sugerido (resultados exploratorios, no oficiales, no mezclados con N3): «Se ejecutaron dos campañas adicionales con el mismo diseño: N3-R (semillas nuevas) y N3-S (las mismas semillas que N3). Los 21 efectos principales evaluados mantuvieron su sentido, y la brecha, `k_stop`, el número de mensajes y F de N3-S fueron idénticos a los de N3. El T_conv absoluto de N3-R y N3-S fue ≈ 16 % menor que el de N3 (cociente 0,84; IC95 % 0,82–0,86), de modo que la velocidad absoluta depende de la sesión de ejecución; la causa no se identificó. El despacho por lotes, la ausencia de difusión de g_best y la heurística de arranque mejoraron T_conv sin empeorar la calidad en las tres campañas; el mecanismo cognitivo fue más rápido con más del doble de brecha.»
**Aviso:** la regla de clasificación de contrastes (umbral del 5 %) se fijó conociendo los efectos agregados de N3; no es un criterio preregistrado.

## C6 — Resumen, «cumplió los requerimientos funcionales y de confiabilidad» (A02)
**Propuesta:** añadir la salvedad «según el informe del arnés para RF06 y REL-D, cuyos registros no se conservan entre los datos publicados».

## Hipótesis propuesta para el OE3 (pendiente de aprobación; no preregistrada)
«Las configuraciones con despacho por lotes, sin difusión de g_best y con heurística de arranque reducen T_conv sin empeorar la brecha frente a sus alternativas.» No se usó en ningún análisis ni aparece en la tesis.
