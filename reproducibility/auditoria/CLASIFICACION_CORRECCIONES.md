# Clasificación de las correcciones propuestas (C1–C24)

Criterio: **A. Factual o de redacción sustentada por evidencia** (se pueden aplicar a una copia de revisión sin decidir nada metodológico); **B. Requiere decisión metodológica**; **C. Requiere aprobación del autor o asesor** (alcance de las conclusiones, estructura de la tesis, hipótesis).

| # | Corrección | Clase | Motivo | Estado |
|---|---|---|---|---|
| C3 | «equivalente» → «similar» frente a `rules` (§6.5.3 y §7.1) | **A** | no existe prueba ni criterio de equivalencia; es un hecho verificable | **aplicada a la copia de revisión** (R4, R5) |
| C6 | salvedad: RF06 y REL-D según el informe del arnés (resumen y abstract) | **A** | las sondas no existen; es un hecho verificable | **aplicada** (R7, R8) |
| C7 | 78,8 → 78,7 ms con PSO y aclarar 68,0/80,8 | **A** | valor recalculado de los datos; el orden lo confirma la fuente | **aplicada** (R1, R2) |
| C8 | «equivalentes» → «similares» (PSO y social, §6.5.4) | **A** | como C3 | **aplicada** (R6) |
| C9 | medias aritméticas frente a geométricas en lugar de «menos de 1,3 %» | **A** | recalculado: la afirmación original es incorrecta; «no afecta a ninguna conclusión» se verificó (signo y orden de los 6 contrastes iguales; efectos relativos difieren ≤ 1,3 puntos) | **aplicada** (R3) |
| C11 | «análisis independiente» → «independiente del código del artefacto, realizado por el propio proyecto» (resumen, abstract, §5.8) | **A** | hecho verificable: lo realizó el propio proyecto | **aplicada** (R10, R11, R12) |
| C12 | «prerregistro y sellado» (§5.8) → especificación versionada con hash y fecha; prerregistro y sellado solo para corridas oficiales | **A** | estado registrado en provenance.json y Git; ninguna corrida oficial | **aplicada** (R9) |
| C13 | «cumplió los requerimientos funcionales…» → RF01 a RF05 y REL-C; RF06 y REL-D según el informe del arnés; RF07 y RF08 no evaluados (resumen y abstract) | **A** | Tabla 5 y recálculo de la Tabla 37 | **aplicada a la copia V2** (R13, R14) |
| C14 | añadir «8 de 9 corridas» a «con 25 usuarios, solo con N = 10» (resumen y abstract) | **A** | N11 `runs.csv` | **aplicada a la copia V2** (R15, R16) |
| C15 | §7.1 OE1: separar lo verificado desde los datos de lo que consta solo en el informe del arnés | **A** | Tabla 37 recalculada | **aplicada a la copia V2** (R17) |
| C16 | «comparadores triviales» → «simples» (2 lugares) | **A** (redacción) | adjetivo valorativo | **aplicada a la copia V2** (R18, R19) |
| C17 | «capacidad casi fija» → «…dentro de cada sesión» | **A** | N8/N8b y N11: ≈ ×1,62 entre regímenes | **aplicada a la copia V2** (R20) |
| C18 | OE5: «señala una desalineación» → «es compatible con» | **A** | no hay contraste de la causa | **aplicada a la copia V2** (R21) |
| C19 | «validada previamente» → «validada técnicamente de antemano» (resumen y abstract) | **A** | §3: validación técnica automática | **aplicada a la copia V2** (R22, R23) |
| C20 | «desviación estándar de unos 2 ms» → cifras medidas (N3: 2,6 ms de promedio; 1,3–5,8 ms) | **A** | `oe3_variabilidad_tconv.json` | **aplicada a la copia V2** (R24) |
| C21 | «sin CPU en el tramo B» → «sin CPU del sistema» | **A** | `recursos.csv`; `.cpu.csv` es del generador | **aplicada a la copia V2** (R25) |
| C22 | OE5 «se cumple de forma parcial y provisional» → «no se cumple; solo una medición provisional del F1» | **C** | alcance del objetivo (evaluación de expertos y docentes) | **no aplicada** |
| C23 | OE2: restringir la conclusión a «un comparador convencional operativo definido por el estudio» | **C** | alcance frente al OE2 literal (plural) | **no aplicada** |
| C24 | OE3: mencionar en la conclusión el efecto de sesión (N3-S/N3 = 0,84) | **C** | decisión sobre N3-R y N3-S (C4, C5) | **no aplicada** |
| C4 | cualificar el «≈ 37 %» con N3 y N3-R/N3-S (10 lugares) | **B/C** | exige decidir si las campañas exploratorias posteriores se mencionan en el resumen | **no aplicada** |
| C10 | «pérdida pequeña de aptitud» → dato + salvedad | **B** | exige elegir entre mantener la valoración con un criterio o suprimirla | **no aplicada** |
| C1 | OE3 «demostrado» (4 lugares) | **C** | alcance de la conclusión principal | **no aplicada** |
| C2 | OE4 «demostrado»/«se cumplió» (5 lugares) | **C** | ídem | **no aplicada** |
| C5 | apartado complementario «Réplica exploratoria del OE3» | **C** | estructura y contenido de la tesis | **no aplicada** |
| — | hipótesis del OE3 | **C** | no preregistrada; solo propuesta | **no incorporada** |

**Copia de revisión:** `…2026-10-19 - D2.9.7-REVISION-FACTUAL.docx` (misma carpeta que el original; **no publicada**, contiene el texto completo de la tesis). Base: la copia corregida de la Tabla 13 (`1bd0894c9586e433…`); original D2.9.7 (`a6bb2934de7fd512…`) intacto. Solo difiere `word/document.xml` y cambian 11 párrafos (12 sustituciones exactas, cada una en un único nodo de texto): [`REGISTRO_CAMBIOS_REVISION_FACTUAL.csv`](REGISTRO_CAMBIOS_REVISION_FACTUAL.csv). sha256 de la copia: `050a0c111ee61f9fdf57b886934a0631531913a838bcd16393f898ee69c6a6ae`.
**Revisión con Word (PDF, 267 páginas cada una):** el número de páginas no cambia; el texto difiere en 11 páginas (5, 6, 7, 77, 95, 105, 106, 107, 109, 167, 168) y la maquetación en 13 (las anteriores, 80 y 113) por el desplazamiento de línea de los textos más largos. Se inspeccionaron visualmente las 13 páginas afectadas (5, 6, 7, 77, 80, 95, 105, 106, 107, 109, 113, 167, 168) sin hallar defectos de maquetación ni de texto.

**Segunda copia de revisión (fase 15):** `…2026-10-19 - D2.9.7-REVISION-FACTUAL-V2.docx` (misma carpeta; **no publicada**). Parte de `…REVISION-FACTUAL.docx` (`050a0c11…a6ae`, que no se modifica) y añade 13 sustituciones exactas (R13–R25, [`REGISTRO_CAMBIOS_REVISION_FACTUAL_V2.csv`](REGISTRO_CAMBIOS_REVISION_FACTUAL_V2.csv)), cada una en un único nodo de texto; solo difiere `word/document.xml`. sha256: `c6716c4ca9bb599da1bd339c1afedfbb3b196d3cc9fae386b7982e038b979bad`. **Con Word: 268 páginas** (la anterior, 267): un renglón más en la p. 113 desplaza el resto desde la p. 135; el índice y las referencias de páginas se actualizan solos. Comparando el texto de todas las páginas desde la 15, los únicos cambios de contenido son los de R17–R21, R24 y R25 (R13–R16, R22 y R23 están en las páginas 5–7, que no entran en esa comparación y se comprobaron a ojo). Inspección visual de las páginas con texto cambiado (5, 6, 7, 96, 113, 135, 167, 169) sin defectos; el resumen sigue ocupando una página y cuatro líneas, como en la copia anterior. **Esta copia no es la versión definitiva:** incluye solo correcciones factuales de clase A.
