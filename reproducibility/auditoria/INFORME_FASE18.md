# Fase 18 — resolución metodológica, verificación pendiente y control de V4

Fecha: 2026-10-19. Punto de partida comprobado: HEAD `b033d24`, idéntico al remoto, árbol de trabajo limpio (los directorios `backend/experiments/…` sin seguimiento ya existían y no son de esta auditoría). **La auditoría sigue abierta.**

## 1. Tabla 14: diagnóstico

Detalle y evidencia en [`DIAGNOSTICO_TABLA14.md`](DIAGNOSTICO_TABLA14.md) y [`TABLA14_REPRODUCCION.csv`](TABLA14_REPRODUCCION.csv) (script [`auditoria_tabla14.py`](../scripts/auditoria_tabla14.py)). Hay **dos análisis distintos sobre las mismas 240 corridas** (log del T_conv):

| | Tablas 13 y 16 | Tabla 14 |
|---|---|---|
| Modelo | todas las interacciones; SS tipo III; 192 g. l. residuales | efectos principales e interacciones de dos factores; tipo II; 219 g. l. |
| Inferencia | permutación (Freedman–Lane, 999; mínimo 0,001) | prueba F paramétrica |
| Corrección | ninguna | Holm sobre 15 términos |
| Código | `adaptation_swarm/oe/factorial.py` | `oe3_reanalysis.py` |

Las 9 filas de la Tabla 14 y las 5 de las Tablas 13 y 16 **se reproducen**, y «interacciones significativas (p entre 0,001 y 0,003)» también. **No hay una cifra errónea**: es un hallazgo **metodológico de rotulado** (C36). Falta decir qué prueba produce cada tabla; los residuos no son normales (Shapiro-Wilk, p = 4 × 10⁻⁴), así que los p paramétricos hasta 10⁻¹⁸⁴ indican efectos grandes y no probabilidades exactas, y el p = 0,015 de las réplicas (permutación, sin corregir) parece «significativo» junto al p de Holm de 0,058. Propuesta de rotulado y tres alternativas con sus consecuencias en el diagnóstico; **no se aplicó al DOCX** (decisión del autor).

## 2. Las dos cifras bibliográficas pendientes

Matriz en [`FUENTES_PENDIENTES_FASE18.csv`](FUENTES_PENDIENTES_FASE18.csv): se separan *existe*, *metadatos coinciden* y *respalda la afirmación*.

- **López-Goyez et al. (2026)** — texto completo del editor (MDPI), tablas leídas en su vista ampliada: el 3,74–3,92 **existe, pero es el rango de los subgrupos de género** (Tabla 14 de la fuente); las medias por dimensión son 3,77; 3,82 y 3,90 (Tabla 12) y por edad 3,72 a 3,91. «Por dimensión» era impreciso. H = 4,88 y p = 0,181 y N = 150 se mantienen. Corrección factual en V5 (R42 a R44).
- **Bennedsen y Caspersen (2019)** — el artículo está en acceso libre en ACM y lo leí en su visor (pp. 30 a 34). **El «28 % a 33 %» no es un rango de un estudio**: 33 % es el resultado de 2006/07 de los mismos autores y 28 % el de 2018 (161 cursos; 170 encuestados; tasa de respuesta del 17,8 %). Los autores concluyen que la tasa **disminuyó** (diferencia significativa) y que «no parece alarmantemente alta» frente al 42–50 % del álgebra universitaria. «Cifra que continúa estable» (§1.1) contradice esa conclusión. Atribución de cifras corregida en V5 (R45, R46); **la motivación del capítulo 1 queda a decisión del autor (C44)**: la fuente respalda que el fracaso existe, no que sea «persistente» ni alarmante.
- **Efron (1979) y Benjamini–Hochberg (1995)**: Benjamini–Hochberg **no se aplica** en ningún análisis (Holm; sin FDR en el código) → retirar del anexo. Efron: el código **sí** aplica bootstrap percentil (IC95 % del F1 histórico v1 y de las diferencias pareadas), pero el IC del F1 v3 es t de Student y el texto no describe el bootstrap → indicar el método y añadir la referencia, o retirarla. Una referencia ausente y un método no aplicado son situaciones distintas (C29).

## 3. Cobertura de la prosa

[`COBERTURA_PROSA_POR_SECCION.csv`](COBERTURA_PROSA_POR_SECCION.csv); detalle de los 105 párrafos pendientes de la fase 17 en [`REVISION_PARRAFOS_FASE18.csv`](REVISION_PARRAFOS_FASE18.csv) (línea, sección, estado, método, evidencia, limitación). **En esta fase revisé los 105 párrafos pendientes** (capítulo 4: 13; capítulo 5: 27; preliminares: 15; capítulo 2: 8; capítulo 3: 14; capítulo 6: 27; capítulo 8: 1). Estado de esos 105:

| Estado | Párrafos | Significado |
|---|---|---|
| Verificado con datos | 32 | recalculado o comprobado en datos y código |
| Coherente con el proyecto | 35 | concuerda con los informes del proyecto y con otras secciones; **no recalculado** |
| Contrastado con fuente externa | 4 | cifras comprobadas en la fuente |
| Metadatos verificados, contenido no contrastado | 7 | **siguen pendientes** |
| Interpretación examinada con observación | 6 | |
| Afirmación prospectiva o normativa | 7 | describe lo que se hará; coherente con las limitaciones |
| Texto formal | 12 | portada, dedicatoria, agradecimientos |
| Hallazgo | 2 | **siguen pendientes** (C39) |

Total por capítulo (párrafos / leídos / con datos / con fuente / interpretación / pendientes): preliminares 22/22/6/0/0/0; 1: 6/6/1/2/0/0; 2: 23/23/0/3/0/0; 3: 54/54/2/22/1/5; 4: 20/20/6/0/0/1; 5: 37/37/16/0/1/2; 6 (introducción): 4/4/1/1/0/0; 6.1: 13/13/6/2/5/0; 6.2: 13/13/6/1/5/0; 6.3: 14/14/10/2/4/0; 6.4: 22/22/18/1/4/1; 6.5: 14/14/6/1/4/0; 6.6: 3/3/1/0/3/0; 6.7: 38/38/24/2/38/0; 7: 6/6/6/0/6/0; 8: 6/6/5/1/6/0. **Total: 295 / 295 leídos / 114 con datos / 38 con fuente / 77 con interpretación examinada / 9 pendientes.**

**Cómo leer estas cifras.** «Solo 9 pendientes» no significa 286 verificados: (i) 35 son *coherentes con el proyecto*, no recalculados; (ii) 190 párrafos revisados en fases anteriores se clasificaron con un criterio menos exigente (cifra comprobada con datos o fuente, o ausencia de cifras), que no examinó sus interpretaciones; (iii) las referencias metodológicas, el contenido de varias fuentes del capítulo 3 y las afirmaciones prospectivas no se contrastaron con los textos completos.

## 4. Hallazgos nuevos de esta fase

| Id | Ubicación | Hallazgo | Estado |
|---|---|---|---|
| C37 | §3.2, Tabla 32, Anexo 7 fila 23 | el 3,74–3,92 es de subgrupos de género, no por dimensión | **corregido en V5** |
| C44 | §1.1, §2.1.2, §2.3 | atribución de 28–33 % imprecisa; la fuente concluye que la tasa disminuyó y no es alarmante | cifras en V5; **interpretación pendiente** |
| C40 | §6.7 B2.2 | la remisión «Tabla 14» cubre cifras de las Tablas 13 y 14 | **corregido en V5** |
| C39 | §5.1, §6, §6.4 | «pilotos en 8 vCPU y 7,5 GiB» parece contradecir que las campañas N1 a N4 usaron el i7-12700K de 20 vCPU (los 8 hilos son de los pilotos históricos con Locust y JMeter, sin datos en el paquete) | **pendiente** |
| C41 | carta al jurado | «evaluación de usuarios expertos» se lee como realizada | pendiente |
| C42 | §5 | «1 080 artefactos» solo si se cuentan aparte los 270 SVG | pendiente |
| C43 | §6.1 | el «0,10 al romper los empates» del Spearman de la brecha no es reproducible de forma única (depende del desempate) | observación |
| C36 | Tablas 13, 14 y 16 | rotulado de las pruebas | **pendiente** |
| C29 | Anexo 7 | Efron y Benjamini–Hochberg | **pendiente** |

Otras comprobaciones nuevas (registro, A152 a A156): Spearman del OE1 (n = 14) y razón geométrica de 7 668 reproducidos; RF03 = 8 600 de 9 500; precisión de audio 0,38 y de texto 0,61 con 323 y 277 falsos positivos; fechas de las campañas (N11 hasta el 2026-10-15). Registro: **156 afirmaciones**.

## 5. Validación integral de V4 y copia V5

- **V4**: hash `e41688cc…` intacto; sus 10 sustituciones (R32–R41) coinciden con el registro; 267 páginas; 461 campos; el índice no cambia al actualizar campos. Comparación página a página (píxeles) con el original: **44 páginas distintas**; 27 con texto cambiado (revisadas visualmente en mosaicos a 62 ppp: sin desbordamientos, páginas en blanco ni tablas rotas) y 17 sin cambio de texto ni desplazamiento de bloques (diferencias de menos de un píxel; recortes lado a lado de cuatro páginas, indistinguibles). **No** inspeccioné a la vista las 223 páginas idénticas al original (por comparación de píxeles no tienen diferencias). Defectos nuevos introducidos por V4: ninguno hallado. Preexistentes (por ejemplo, filas de tabla que continúan en la página siguiente): no se corrigieron.
- **V5** (copia separada; V3 y V4 intactas; no se publica): V4 más 6 sustituciones (R42–R47), [`REGISTRO_CAMBIOS_REVISION_FACTUAL_V5.csv`](REGISTRO_CAMBIOS_REVISION_FACTUAL_V5.csv). **267 páginas, 461 campos, texto idéntico antes y después de actualizar campos, 6 páginas con texto distinto de V4 (19, 23, 33, 149, 158, 235) y sin reflujo.** Mi primer intento (con redacciones más largas) desplazó una línea desde la página 19 hasta la 165 y dejó el encabezado «6.6 Cierre de brechas» solo al pie de la página 151; lo descarté y acorté las sustituciones hasta eliminar el reflujo. Sin revisar a la vista las páginas sin cambio. **V5 tampoco es definitiva.**

## 6. Pruebas y protecciones
Suite completa con el Python de Anaconda (`C:\ProgramData\anaconda3`): **68 pruebas, 68 superadas** tras corregir una expectativa mía equivocada en una prueba nueva (5 filas, no 6, en la matriz de fuentes). No se regeneraron salidas versionadas; no se repitió Colab (ningún archivo que consumen los notebooks cambió: `MATRIZ_CAMBIOS_POSTERIORES.csv`, 58 archivos cambiados desde `c68a746`, 0 consumidos); las ejecuciones locales no se presentan como ejecuciones históricas de Colab. No se tocó `main`, no hubo force push, el DOCX no se publicó y no se borró ningún archivo de OE3.

## 7. Decisiones que siguen siendo del autor o del asesor
C1, C2, C4, C5, C10, C11 (parte metodológica), C22 a C24, C27 a C29, C36, C38, C39, C41, C42, C44, la hipótesis del OE3 (propuesta, no preregistrada), τb de la Tabla 6, el uso de N3-R y N3-S, el tratamiento de «evidencia contraria» (C31) y los archivos residuales de OE3. **No interpreté ningún silencio como aprobación.** Para cada una hay alternativas en `PROPUESTA_CORRECCIONES_CONCLUSIONES.md`, `CLASIFICACION_CORRECCIONES.md` y `DIAGNOSTICO_TABLA14.md`.

## 8. ¿Está la tesis lista para entregar?
**No, y no por falta de pruebas pasadas.** Lo que falta, concretamente:
1. **Evidencia que no existe**: panel de expertos (0), SUS (0 respuestas), validación del gold, ejecución oficial en el hardware objetivo, F1 oficial v3 (el provisional, 0,8156, está por debajo de 0,85), RF06 y REL-D sin registros de sonda reproducibles, seis ejecuciones de Colab sin hashes verificables. Con esto, OE1, OE2, OE5 y la hipótesis general no pueden darse por cumplidos.
2. **Decisiones de redacción** (lista de la sección 7), en particular la motivación del capítulo 1 frente a la fuente de Bennedsen y Caspersen, el alcance de las conclusiones de OE3 y OE4 y la inclusión de las réplicas N3-R y N3-S.
3. **Verificación incompleta**: 7 párrafos con contenido de fuentes sin contrastar y 2 hallazgos abiertos; los 190 párrafos de fases anteriores no pasaron por el criterio más exigente de esta fase; el contenido de varias referencias del capítulo 3 se verificó solo por metadatos.
4. **Documento**: ninguna copia es definitiva; faltan aplicar (o descartar) las decisiones anteriores y repetir la validación de paginación e índice sobre la copia final.
