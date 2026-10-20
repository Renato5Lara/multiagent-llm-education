# Fase 17 — discrepancias estadísticas, fuentes y cobertura pendiente

Fecha: 2026-10-19. Antecedente: HEAD `2bf217d` (fase 16), confirmado antes de empezar (árbol limpio, remoto idéntico). **La auditoría sigue abierta.** Los documentos de tesis no se publican.

## 1. La discrepancia numérica restante (P4-06)

De las 72 comprobaciones numéricas de prosa de la fase 16, 71 coincidían y **una no**. Identidad completa:

| Campo | Contenido |
|---|---|
| Ubicación | §6.4.3 (OE4, campaña N8), párrafo «Con un enjambre de 30 partículas…», y la celda «Decisión e interpretación» de la Tabla 26 |
| Cifra publicada | «p de Holm ≤ 7 × 10⁻⁹ en todas las cargas» (P95) y «≤ 5 × 10⁻¹¹» (throughput) |
| Cifra recalculada | máximo del P95: **2,09 × 10⁻⁷** (25 usuarios); máximo del throughput: **1,54 × 10⁻¹⁰** (25 usuarios) |
| Datos y método | `runs.csv` de N8 (120 corridas válidas; 10 por celda), N = 30 frente a N = 10 en cada una de las 6 cargas; Welch sobre el logaritmo por corrida; Holm con m = 6 por métrica |
| Contraste interno | la columna «mayor p de Holm» de la **Tabla 19** del mismo apartado (6,9 × 10⁻⁹ … 2,1 × 10⁻⁷) se reproduce exactamente; el archivo del proyecto `oe4_nvar_contrastes.csv` da los mismos valores que mi recálculo |
| Causa | **no** es redondeo, ni población distinta, ni fórmula, ni datos: el análisis del proyecto y la Tabla 19 son correctos; **la cota de la prosa estaba mal**. La cota del P95 coincide con el p de Holm de la celda de 1 usuario (6,9 × 10⁻⁹), que es también el máximo si se omite la de 25 usuarios; la del throughput no coincide con ninguna combinación de celdas |
| Resolución | corregida en V3 (R26–R28: «≤ 2,1 × 10⁻⁷» y «≤ 1,5 × 10⁻¹⁰»); V4 la hereda. Las diferencias siguen siendo significativas |

## 2. Auditoría independiente de los valores p de Holm

[`HOLM_AUDITORIA.csv`](HOLM_AUDITORIA.csv), generada por [`scripts/auditoria_holm.py`](../scripts/auditoria_holm.py): **84 comprobaciones** con **dos implementaciones independientes** (método A: scipy y `statsmodels.multipletests`; método B: Welch con la fórmula de Satterthwaite y Holm escritos a mano), que **coinciden entre sí en las 84**. De las 83 comparables con el texto, **81 coinciden y 2 difieren** (las dos cotas originales de N8, ya corregidas); 1 fila es informativa (diagnóstico del origen de la cota).

| Tabla o pasaje | Filas | Familia y método |
|---|---|---|
| Tabla 9 (OE2, N2) | 8 | Welch sobre log, Holm m = 8 |
| Tabla 10 (OE2, N2) | 8 | Mann-Whitney asintótico, Holm m = 8 |
| Tabla 11 (OE2, N9b) | 24 | Welch sobre log, Holm m = 8 por comparador |
| Tabla 14 (OE3, N3) | 10 | ANOVA tipo II paramétrico, Holm m = 15 |
| §6.3.3 (réplicas) | 2 | p de Holm 0,058 (paramétrico) y 0,049 (ANOVA sobre rangos) |
| Tabla 19 y §6.4.3 (OE4, N8) | 6 + 4 + 1 | Welch sobre log, Holm m = 6 por métrica; cotas original y corregida |
| §6.4.3 (N8b frente a N4) | 1 | Holm m = 12 (menor p = 0,15) |
| Tabla 26 (N4, pasos consecutivos) | 2 | Holm m = 5 (4 × 10⁻²⁰ y 0,073) |
| Tabla 22 (OE4, N11 tramo B) | 18 | Holm m = 18 por métrica |

**Resultado numérico** (separado de su interpretación): los valores corregidos se reproducen; las comparaciones, la unidad (la corrida), el número de contrastes y la corrección coinciden con lo declarado en §5.8. **Hallazgo de rotulado (C36):** la Tabla 14 informa p de Holm **paramétricos** de la prueba F (hasta 10⁻¹⁸⁴), mientras que §6.3.5 y §6.3.6 hablan de p **por permutación** con piso en 0,001; los p por permutación no figuran en ninguna tabla. Referencias cruzadas: la cota incorrecta aparecía en tres lugares (prosa del OE4, Tabla 26 y —ya corregida— V3); no queda ninguna en V3 ni en V4.

## 3. Fuentes con cifras no contrastadas

Procedimiento ([`scripts/fuentes_texto_completo.py`](../scripts/fuentes_texto_completo.py) y lectura en el navegador; EVIDENCIA EXTERNA, 2026-10-19): para cada fuente se localizó la versión abierta que indica OpenAlex, se obtuvo el texto completo (PDF o HTML del editor; Heliyon por Europe PMC) y se buscó cada cifra; las salvedades se leyeron con su contexto. Los textos descargados no se publican. **Se separan tres niveles:** *la fuente existe* y *los metadatos coinciden* (fase 16: 111 de 120 con DOI) frente a *la fuente respalda la afirmación* (esta fase). Resultado en [`FUENTES_TEXTO_COMPLETO.csv`](FUENTES_TEXTO_COMPLETO.csv):

- **Corrección de mi conteo de la fase 16.** Allí conté 45 filas de «texto completo» sin cifras en el resumen; la clasificación correcta del nivel declarado da **91 filas: 36 sin cifras, 6 de «solo resumen» con todas sus cifras en el resumen (coherente con su nivel), y 49 de «texto completo» con cifras (5 también en el resumen y 44 no)**. Ninguna fila de «solo resumen» trae cifras que falten en el resumen.
- **De las 44 filas**, se contrastaron las cifras con el texto completo: **105 halladas, 4 con salvedad, 1 no hallada, 1 no contrastable, 1 inaccesible** (y 4 filas cualitativas sin cifras reales).

| Fuente | Resultado |
|---|---|
| Clinton-Lisell y Litzinger (2024) | **corrección:** el 26 % es de *medidas de resultado*, no de estudios; recomiendan, si se incorporan los estilos de aprendizaje, hacerlo en un contexto multimodal (no «una instrucción multimodal para todos»); hallaron además un beneficio global pequeño y significativo (g = 0,31; p = 0,02) → R32, R33 |
| Al Faia y Alomar (2025) | el 3,61 % de más usabilidad **no fue significativo** (Wilcoxon, efecto pequeño) → R34, R35 |
| Cioca y Cioca (2025) | el SUS informado es un intervalo de **80 a 100**, no una media de 80 → R36, R37 |
| Al-Ahmad et al. (2022) | 91,89 % se redondea a 91,9 (la tesis lo truncaba) → R38, R39 |
| Chen y Hsu (2022) | el texto de la fuente da p < 0,05 (su Tabla 2, p = 0,000); no «p < 0,001» → R40, R41 |
| López-Goyez et al. (2026) | **H = 4,88 y p = 0,181 hallados** (Kruskal-Wallis, usabilidad); 150 estudiantes; medias globales 3,77, 3,82 y 3,90; **3,74 y 3,92 no hallados** en el texto extraído; sin mención de grupo de control (una ausencia no es una afirmación) |
| Li et al. (2023) | coincide (338 estudiantes; 115 frente a 200 iteraciones; 0,769, un 12,3 % mayor) |
| Watson y Li (2014) | el repositorio da 161 cursos, 15 países, 51 instituciones y 67,7 % de aprobación; el 32,3 % de fracaso es 100 − 67,7 |
| Bennedsen y Caspersen (2019) | «28 % a 33 %» **no verificado**: PDF de acceso libre en ACM pero no extraíble |
| Resto (≈ 35 fuentes) | cifras halladas con significado coincidente comprobado a mano en una muestra (Tan, S. Zhang, Pabón, Tebourbi, Troussas, Hao, Ma, Sulaiman, Ren, Cheng, Dinh, Amin, Feng, Isal, Koca, Liu, Smaili, Srinivas, Ukenova, Žerovnik, Nand, Ledmi, Arshad, Mohamedhen, Naseer…) |

Hallar una cifra en un texto **no prueba** que respalde la interpretación de la tesis: el contexto se leyó a mano en la muestra citada, no en las 105. Una repositorio protegido por verificación anti-bot (Durham) se abrió solo cuando la verificación se resolvió por sí sola; no se eludió ninguna.

**Benjamini y Hochberg (1995) y Efron (1979)** (Tabla 44, sin entrada en la lista): Benjamini–Hochberg **no se usa** (el texto controla con Holm; no hay FDR en el texto ni en el código) → retirarlo del anexo. Efron: el código incluye un IC95 % por bootstrap percentil del F1 (`gold/f1.py`), probablemente el del F1 v1 histórico (0,8031; IC95 % 0,711–0,877), cuyo método el texto no indica → indicar el método y añadir la referencia, o retirarla. Decisión del autor (C29).

## 4. Cobertura de la prosa, por capítulo y sección

[`COBERTURA_PROSA_POR_SECCION.csv`](COBERTURA_PROSA_POR_SECCION.csv) y [`…_POR_PARRAFO.csv`](COBERTURA_PROSA_POR_PARRAFO.csv). Unidad: párrafo de prosa (≥ 8 palabras; sin tablas ni encabezados). **«Leído» no es «verificado».**

| Sección | Párrafos | Leídos y evaluados | Comprobados con datos | Contrastados con fuente externa | Interpretación examinada | Pendientes |
|---|---|---|---|---|---|---|
| Preliminares | 22 | 8 | 5 | 0 | 0 | 15 |
| 1 Introducción | 6 | 6 | 1 | 2 | 0 | 0 |
| 2 Planteamiento | 23 | 23 | 0 | 3 | 0 | 8 |
| **3 Marco teórico (leído por primera vez)** | 54 | **54** | 1 | 18 | 0 | 14 |
| 4 Hipótesis y variables | 20 | 20 | 2 | 0 | 0 | 13 |
| 5 Marco metodológico | 37 | 37 | 2 | 0 | 0 | 27 |
| 6 (introducción) | 4 | 4 | 0 | 1 | 0 | 3 |
| 6.1 OE1 / 6.2 OE2 / 6.3 OE3 | 13 / 13 / 14 | 13 / 13 / 14 | 4 / 5 / 9 | 2 / 1 / 2 | 5 / 5 / 4 | 4 / 1 / 1 |
| 6.4 OE4 / 6.5 OE5 | 22 / 14 | 22 / 14 | 17 / 5 | 1 / 1 | 4 / 4 | 2 / 7 |
| 6.6 y 6.7 | 3 / 38 | 3 / 38 | 0 / 21 | 0 / 2 | 3 / 38 | 2 / 7 |
| 7 Conclusiones / 8 Recomendaciones | 6 / 6 | 6 / 6 | 6 / 4 | 0 / 1 | 6 / 6 | 0 / 1 |
| **Total** | **295** | **281 (95 %)** | **82 (28 %)** | **34** | **75** | **105 (36 %)** |

Pendientes = párrafos no leídos (14 de los preliminares) o con cifras o afirmaciones sin comprobar con datos ni con fuente externa; muchos son procedimentales o repiten cifras de tablas ya verificadas, pero no se afirma que estén verificados. **Registro de afirmaciones: 151** (+9 en esta fase: A143–A151; A129, A131, A140 y A142 actualizadas); 27 pendientes, 13 con discrepancia.

## 5. Errores sustantivos encontrados en esta fase

| Clase | Hallazgo | Estado |
|---|---|---|
| Factual (cifra atribuida a una fuente) | Clinton-Lisell (26 % de medidas, no de estudios; recomendación condicional), Al Faia (no significativo), Cioca (80–100), Al-Ahmad (91,9), Chen y Hsu (p < 0,05) | corregidos en **V4** (R32–R41) |
| Interpretativo | «evidencia contraria al emparejamiento con estilos» (§1.2, §6.5.6) para una fuente que halló un beneficio global pequeño y significativo | abierto (C31, parte de formulación) |
| Metodológico | Tabla 14: p paramétricos frente a p por permutación | abierto (C36) |
| Metodológico | «c1 = c2 = 1,494 corresponden a la formulación con coeficiente de constricción» (la fórmula da 1,496) | abierto (C38) |
| Bibliográfico | rango 3,74–3,92 (López-Goyez) y «28 % a 33 %» (Bennedsen y Caspersen) sin contrastar | abierto (C37) |
| Documental | Benjamini–Hochberg y Efron en el Anexo 7 sin referencia | abierto (C29) |

## 6. Copia V4 y protecciones

[`REGISTRO_CAMBIOS_REVISION_FACTUAL_V4.csv`](REGISTRO_CAMBIOS_REVISION_FACTUAL_V4.csv): 10 sustituciones exactas (R32–R41), cada una con su evidencia. **267 páginas** con Word; índice y 461 campos sin cambios al actualizarlos; texto distinto frente a V3 en 8 páginas (35–38, 234, 251–253) y maquetación en 7; inspeccioné las 8 páginas con texto cambiado y los dos casos de maquetación de las páginas de anexo; **no** revisé visualmente el resto. Original, copias anteriores (V1, V2, V3) y `main` intactos; hashes en [`HASHES_DOCUMENTOS.csv`](HASHES_DOCUMENTOS.csv). **V4 no es definitiva.** Las correcciones no tocan resumen, abstract ni conclusiones: las limitaciones de OE1–OE5 (RF06/REL-D, RF07/RF08, comparador único, N3 frente a N3-R/N3-S, hardware local, F1 < 0,85, sin SUS ni panel) se conservan sin cambios.

## 7. Pruebas
No se tocó código ni datos que ejecuten los notebooks (los scripts nuevos son de auditoría): no se repitió Colab; las seis ejecuciones históricas siguen sin hash verificable. Suite local completa (Python de Anaconda, 2026-10-19): **65 pruebas superadas** en 7 min 56 s; las pruebas nuevas cubren Holm, fuentes, V4, hashes y cobertura.

## 8. Qué falta para considerar la tesis lista para entregar
(1) Decisiones del autor y del asesor: C1, C2, C4, C5, C10, C11 (parte metodológica), C22–C24, C27–C29, C31 (formulación), C36–C38, la hipótesis del OE3 y τb. (2) RF06 y REL-D no reproducibles; SUS, panel de expertos y ejecución oficial inexistentes. (3) 105 párrafos pendientes (36 %), con el capítulo 5 y el 4 los más pendientes (procedimentales, pero sin comprobar). (4) Cifras de fuentes: 44 filas contrastadas por coincidencia numérica, con el contexto leído solo en una muestra; 2 afirmaciones sin contrastar (López-Goyez, Bennedsen y Caspersen). (5) Una revisión visual completa de V4. Que las cifras coincidan y las pruebas pasen no equivale a que las conclusiones estén justificadas en su alcance.
