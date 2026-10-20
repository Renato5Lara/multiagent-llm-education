# Fase 16 — auditoría sustantiva de la tesis, fuentes y validación de las copias de revisión

Fecha: 2026-10-19. Punto de partida: HEAD `773d7b7` (rama `repro/auditoria-integral-2026-10-19`). **La auditoría sigue abierta.** Los documentos de tesis no se publican; las copias de revisión viven fuera del repositorio.

## 1. Integridad y paginación de V2 (y de la nueva V3)

| Documento | sha256 (inicio) | Páginas (Word) | Estado |
|---|---|---|---|
| Original D2.9.7 (canónico) | `a6bb2934de7fd512` | 267 | **intacto** (mismo hash que el registrado) |
| Copia corregida de la Tabla 13 | `1bd0894c9586e433` | 267 | intacta |
| Copia de revisión V1 | `050a0c111ee61f9f` | 267 | intacta |
| Copia de revisión V2 | `c6716c4ca9bb599d` | **268** | **superada**: defectos que no vi en la fase 15 (abajo) |
| Copia de revisión V3 | `2949d91a79e86c12` | 267 | vigente, **no definitiva** |

Hashes completos en [`HASHES_DOCUMENTOS.csv`](HASHES_DOCUMENTOS.csv).

**Las 13 sustituciones de V2 (R13–R25)** se comprobaron contra su evidencia y contra el registro de cambios: cada texto original aparece exactamente una vez en `word/document.xml`, solo difiere ese archivo del paquete, y el ZIP se abre sin errores. Cada una remite a su evidencia: R13 y R14 a A02, A76, A112 y A113; R15 y R16 a A06 y A109; R17 a A63 y A112; R18 y R19 a A03 y A18 (redacción); R20 a A11 y A30; R21 a A90; R22 y R23 a A119; R24 a A107 y A114; R25 a A117.

**Por qué V2 tenía 268 páginas.** No fue el texto de las conclusiones sino un efecto en cadena: la sustitución R25 («sin CPU **del sistema** en el tramo B») añadió un renglón a la p. 135; a partir de ahí las páginas se desplazaron un renglón y la Tabla 28 (que Word no parte) saltó de la p. 138 a la 139; el resultado fue una **página con dos líneas de texto (p. 141)** que el original no tiene. Además, **el índice guardado en V2 no coincide con su paginación**: al actualizar los campos en Word, el índice cambia (en el original y en V3 no cambia). Esto es un defecto de V2 que la inspección visual de la fase 15 no detectó porque solo miró las páginas con texto modificado.

**V3** corrige esos dos defectos sin quitar contenido factual: acorta la sustitución R24 (R30) y quita «del equipo» de R25 (R31); añade R26–R28 (cotas de p de Holm del OE4) y R29 (CPU y memoria). Resultado: **267 páginas**, las mismas páginas casi vacías que el original (49, 53, 214, 215, 223–225), índice y campos sin cambios al actualizarlos (461 campos, 1 índice, 2 tablas de ilustraciones, 15 secciones, 46 tablas, 13 figuras en línea, 0 notas al pie, sin saltos de página manuales), y el índice del PDF idéntico al del original (139 entradas).

**Diferencias de V3.** Frente al original: texto distinto en 19 páginas y maquetación distinta en 16 (5, 6, 7, 52, 77, 80, 95, 105–107, 109, 113, 134, 166–168). Frente a V1: texto distinto en 12 páginas y maquetación en 9 (5–7, 52, 113, 134, 166–168). Detalle de los cambios: [`REGISTRO_CAMBIOS_REVISION_FACTUAL_V3.csv`](REGISTRO_CAMBIOS_REVISION_FACTUAL_V3.csv) (R26–R31, relativo a V2).

**Alcance exacto de la inspección visual.** Vi las páginas 5, 6, 7, 52, 96, 113, 118, 134, 135 y 166–168 de V3 o de V2 con el mismo texto y maquetación (5–7 y 96 son idénticas entre V2 y V3; 52, 113, 118, 134, 135 y 166–168 se vieron en V3). Las páginas 77, 80, 95, 105–107 y 109 tienen la misma maquetación que en V1, que se inspeccionó en la fase 14. **No** miré visualmente las demás páginas: se compararon de forma automática (texto y bloques) con el original y no difieren; eso no detecta defectos que el original ya tuviera.

## 2. Revisión sustantiva de la prosa: cobertura real

Unidad: párrafo de prosa (≥ 8 palabras; sin filas de tabla, rótulos ni encabezados) de los capítulos 1 a 8. Fuente: [`COBERTURA_PROSA_POR_SECCION.csv`](COBERTURA_PROSA_POR_SECCION.csv) y [`…_POR_PARRAFO.csv`](COBERTURA_PROSA_POR_PARRAFO.csv).

| Sección | Párrafos | Leídos y evaluados | Con alguna cifra o afirmación comprobada con datos |
|---|---|---|---|
| 1 Introducción | 6 | 6 | 1 |
| 2 Planteamiento | 23 | 23 | 0 |
| 3 Marco teórico | 54 | **0** (solo sus fuentes, ver §4) | 1 |
| 4 Hipótesis y variables | 20 | 20 | 2 |
| 5 Marco metodológico | 37 | 37 | 2 |
| 6.1 OE1 / 6.2 OE2 / 6.3 OE3 | 13 / 13 / 14 | 13 / 13 / 14 | 4 / 5 / 9 |
| 6.4 OE4 / 6.5 OE5 | 22 / 14 | 22 / 14 | 17 / 5 |
| 6.6 y 6.7 (brechas y discusión) | 3 / 38 | 3 / 38 | 0 / 21 |
| 7 Conclusiones / 8 Recomendaciones | 6 / 6 | 6 / 6 | 6 / 4 |
| **Total capítulos 1–8** | **295** | **227 (77 %)** | **82 (28 %)** |

«Leído» no es «verificado»: un párrafo leído puede ser procedimental, interpretativo o bibliográfico. **Lo realmente comprobado con datos** son 72 cifras o grupos de cifras de la prosa del capítulo 6 y del método ([`scripts/verificacion_prosa_cap6.py`](../scripts/verificacion_prosa_cap6.py): 71 coinciden y 1 difiere) más las 142 filas del registro (+18 en esta fase, A125–A142; 6 de ellas agrupan las 72 comprobaciones). Pendientes de revisión: 24 afirmaciones del registro; sin leer: el capítulo 3 y los anexos; sin comprobar con datos: el 72 % de los párrafos de prosa de los capítulos 1–8 (muchos son procedimentales, bibliográficos o repiten cifras de tablas que sí se verifican).

**Resultado de la comprobación numérica de la prosa: 71 de 72 coinciden.** Lo que falla es una frase, no una cifra de las tablas (H1).

## 3. Hallazgos sustantivos

| Id | Clase | Ubicación | Hallazgo | Estado |
|---|---|---|---|---|
| H1 | **factual** | §6.4.3 (N8), Tabla 26 | «p de Holm ≤ 7 × 10⁻⁹» (P95) y «≤ 5 × 10⁻¹¹» (throughput) contradicen la Tabla 19 del mismo apartado (la columna «mayor p de Holm» se reproduce exactamente: máx. 2,1 × 10⁻⁷ en el P95 y 1,5 × 10⁻¹⁰ en el throughput, a 25 usuarios). Las diferencias siguen siendo significativas. | corregida en V3 (R26–R28; A125) |
| H2 | factual | §4.4 | «consumo de CPU y memoria … no se reportan» frente a §6.4.3, que reporta memoria libre y CPU del equipo | corregida en V3 (R29; A128) |
| H3 | interpretativo | §6.5.3 y §6.7 B5.3 | «es una desalineación de diseño y no un defecto de implementación, pues el F1 se reproduce exactamente»: la premisa verifica el cálculo de la métrica, no la función de aptitud ni el optimizador | no aplicada (C27; A126) |
| H4 | interpretativo | §6.7 | correspondencia forzada B3.2 ↔ «selección conjunta con criterios multiobjetivo» | no aplicada (C28; A127) |
| H5 | documental / autor | Anexo 7 | Benjamini y Hochberg (1995) y Efron (1979) están en la Tabla 44 pero no en la lista de referencias ni se citan; el texto no usa FDR ni bootstrap | decisión del autor (C29; A129) |
| H6 | bibliográfico | §3, §6, Anexo 7 | 45 filas del Anexo 7 («texto completo») traen cifras que no están en los resúmenes públicos; solo se contrastaron con el texto completo 2 fuentes | pendiente (C30; A131, A140, A142) |
| H7 | metodológico | §5.3.4 | el gold v3 asigna el mismo conjunto {código, diagrama} a Visual-Dominant y Logical-Syntactic: la métrica no distingue esos dos arquetipos (observación; no es un error) | para la discusión (A132) |
| H8 | proyecto (no tesis) | `PANEL_PROTOCOL_ARQUETIPOS.md` | dice que la certificación de AC1 con R está «PENDIENTE», pero el registro `px8_certification_2026-09-27.json` la da por CERTIFICADA (R 4.4.1, irrCAC 1.4, 16 casos): la tesis (§5.10) es correcta y ese documento interno está desactualizado | pendiente (A133) |
| H9 | formato | V2 | página casi vacía e índice desactualizado | corregido en V3 |

Verificadas sin hallazgo: parámetros del PSO y de la aptitud, gold v3, 100 perfiles (4 × 5 × 5), 30 de 32 conceptos, biblioteca de 1 080 archivos (solo si cada SVG cuenta aparte), certificación de AC1 (registro interno), recuentos de brechas (6 + 14 = 20), recuentos y rangos de N1, N2, N3, N4, N8, N8b, N9b y N11, régimen del equipo (×0,61 / ×0,60 / ×1,62), η² parciales, Kruskal-Wallis y Spearman del OE4, FP y FN por modalidad del OE5.

## 4. Auditoría bibliográfica (evidencia externa: Crossref, DataCite y OpenAlex, 2026-10-19)

[`MATRIZ_VERIFICACION_BIBLIOGRAFICA.csv`](MATRIZ_VERIFICACION_BIBLIOGRAFICA.csv): de **120 referencias**, **111 verificadas** con su DOI (título, autores, año, publicación, volumen, número y páginas coinciden), **1 verificada solo en OpenAlex** (Holm, 1979: Crossref no sirve el DOI de JSTOR) y **8 sin DOI** que no se pueden verificar automáticamente (libros, un capítulo, una tesis y un artículo de ACL Findings). **0 discrepantes.** La frase de la tesis («las referencias se verificaron contra Crossref, OpenAlex y arXiv») es consistente con este resultado. Citas ↔ referencias ([`CITAS_Y_REFERENCIAS.csv`](CITAS_Y_REFERENCIAS.csv)): todas las citas del cuerpo tienen su entrada; Benjamini y Hochberg (1995) y Efron (1979) están en el Anexo 7 sin entrada (H5); una entrada (Pabón M. et al., 2025) solo se cita en el Anexo 7.

**Cifras atribuidas a las fuentes** ([`ANEXO7_VERIFICACION.csv`](ANEXO7_VERIFICACION.csv), [`CIFRAS_ATRIBUIDAS_A_FUENTES.csv`](CIFRAS_ATRIBUIDAS_A_FUENTES.csv)): de las 91 filas del Anexo 7, 36 no traen cifras; 3 filas de «solo resumen» tienen **todas** sus cifras en el resumen público; de las 52 filas de «texto completo» con cifras, 7 las tienen también en el resumen y **45 no**. Esas 45 solo se pueden contrastar con el texto completo. **Lectura directa del texto completo (solo 2 fuentes):** Li et al. (2023) — **coincide** (338 estudiantes; 115 frente a 200 iteraciones; 0,769, un 12,3 % mayor que el ACO); López-Goyez et al. (2026) — **parcial** (150 estudiantes; medias 3,77–3,90; sin diferencias por género; no localicé H = 4,88 ni p = 0,181). Watson y Li (2014) y Bennedsen y Caspersen (2019): las cifras de §1 no figuran en sus resúmenes; falta el texto completo. **Un metadato correcto no prueba que la fuente respalde la afirmación.**

## 5. Coherencia entre resultados, discusión, conclusiones, resumen y abstract

[`MATRIZ_COHERENCIA_ES_EN.csv`](MATRIZ_COHERENCIA_ES_EN.csv) (16 temas × 5 bloques). Resumen y abstract coinciden en cifras (34 y 34) y en cautelas. Las limitaciones que deben estar en todos los bloques sí están (campañas no oficiales, hardware distinto del objetivo, un solo comparador, F1 < 0,85, SUS sin medir, «solo con N = 10 en un régimen del equipo», «8 de 9» tras V3). Los huecos son **omisiones coherentes** de todos los bloques: **N3-R y N3-S no figuran en ninguno** (C4, C5, C24); RF07 y RF08 solo en resultados, resumen y abstract (no en las conclusiones); «sin prueba de equivalencia» solo en resultados y conclusiones; la variabilidad de T_conv solo en resultados. **Español e inglés dicen lo mismo con la misma fuerza**, incluido «demostraron/demonstrated» (C1, C2) y el nuevo «validada técnicamente».

## 6. Lo que se mantiene (sin cambios en esta fase)
OE1: RF06 y REL-D sin registros de sonda; RF07 y RF08 no evaluados; no se generaliza el cumplimiento. OE2: solo el comparador operativo. OE3: N3 separado de N3-R/N3-S como límite; efectos relativos frente a valores absolutos (≈ 16 % de diferencia entre sesiones); hipótesis no aprobada ni preregistrada. OE4: solo hardware local. OE5: F1 = 0,8156 < 0,85; sin SUS ni panel. T_conv: variabilidad separada en entre corridas (2,6 ms), entre peticiones (≈ 12 ms) y entre campañas (≈ 7 ms).

## 7. Clasificación y decisiones pendientes
Errores factuales corregibles con evidencia (aplicados a V3): H1, H2 (+ ajustes de formato R30, R31). Problemas interpretativos que requieren justificación (no aplicados): H3, H4. Decisión metodológica: H7, la parte metodológica de C11. **Decisiones académicas pendientes (sin cambios):** C1, C2, C4, C5, C10, C11 (parte metodológica), C22, C23, C24, la hipótesis del OE3, τb en la Tabla 6, y ahora C27–C30 (H3–H6) y el retiro de los archivos residuales `verificacion_oe3_20261019_071001*`. V3 **no** es definitiva.

## 8. Validación técnica
Suite local completa, comandos y notebooks: ver `INFORME_CIERRE_FINAL.md` §17. Los notebooks no consumen ninguno de los archivos nuevos (scripts de auditoría, salidas de comprobación y CSV): no se repitió Colab, y se conserva la limitación de que las seis ejecuciones históricas no se guardaron con hash verificable.

## 9. Evaluación: qué está suficientemente respaldado y qué impide considerar la tesis lista
**Suficientemente respaldado:** las cifras de las tablas y de la prosa de los capítulos 5 y 6 (1 039 comprobaciones de tablas + 72 de prosa, con 1 frase errónea ya corregida en V3), el diseño y los parámetros del artefacto, las referencias como objetos bibliográficos (111 de 120 verificadas) y la delimitación de las campañas como exploratorias.
**Impide darla por lista:** (1) los verbos y el alcance de las conclusiones de OE3, OE4 y OE5 (C1, C2, C22); (2) RF06 y REL-D no reproducibles; (3) no hay SUS, panel de expertos ni ejecución oficial; (4) el 72 % de los párrafos sin comprobación con datos y el capítulo 3 sin leer; (5) 45 filas del Anexo 7 y las cifras de §1 sin contrastar con el texto completo; (6) las decisiones académicas pendientes. Que las cifras coincidan no significa que las conclusiones estén justificadas en alcance.
