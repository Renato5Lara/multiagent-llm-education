# Conteo de cifras: qué significa «861» y cuánto vale ahora

**Definición.** Una *comprobación* (lo que antes se llamó «cifra») es **un valor numérico comparado** con su recálculo: en una celda «5,05 (4,57 a 5,58)» la razón, el límite inferior y el superior cuentan por separado (3 comprobaciones en 1 celda). Por tanto **861 no eran 861 celdas, ni 861 valores únicos**: eran 861 comprobaciones sobre 20 tablas.

**Reproducción del 861 anterior.** El informe del commit `21c7380` contiene 869 comprobaciones, de las cuales 861 `VERIFICADO_DESDE_DATOS`, 8 `NO_REPRODUCIBLE` y 0 discrepantes. El cálculo es reproducible con `git show 21c7380:reproducibility/outputs/verification_report.json`. Todas las comprobaciones antiguas siguen presentes: 864 de 869 (faltan 5: ['PEND-Tabla 25', 'PEND-Tabla 36', 'PEND-Tablas 15 y 30', 'T27-perfil', 'T6-Usuarios (carga) fre']).

## Conteo actual (esta rama)
| | |
|---|---|
| Comprobaciones totales | 1017 |
| `VERIFICADO_DESDE_DATOS` | 998 |
| `VERIFICADO_DESDE_DERIVADO` | 14 |
| `DISCREPANCIA` | 0 |
| `NO_REPRODUCIBLE` (elementos, no celdas: algunos agrupan varias tablas) | 5 |
| Celdas numéricas del informe (excluida la fila de encabezados) | 1665 |
| Celdas cubiertas por al menos una comprobación | 619 |

Las comprobaciones **no** deben dividirse por tablas sin cuidado: una celda numérica puede tener varias y algunas celdas son etiquetas de condición (carga, N) que no se calculan. El inventario por celda y por afirmación en prosa está en `CONCILIACION_TESIS_DATOS.csv`.

## Las «8 cifras no reproducibles»
No eran 8 cifras: son **8 elementos** del informe anterior, y varios agrupan tablas enteras. Estado actual de cada uno (ver `CONCILIACION_TESIS_DATOS.csv`, estado `NO_REPRODUCIBLE`/`PENDIENTE_DE_EVIDENCIA`):
- T6-usuarios-tau: la tesis publica «no calculado»; no hay cifra que comparar
- T27-sus: no existen datos: 0 evaluadores reales; no se simulan
- PEND-Tablas 5 y 37: estados MET/NOT_MET: texto categórico del informe de N1 (oe1_report.json); no hay cálculo numérico que recomputar aquí
- PEND-Tablas 32 y 44: síntesis bibliográfica: depende de consultas externas (Crossref/OpenAlex); no verificable por cómputo determinista
- PEND-Tabla 35: instrumento SUS sin aplicar: no hay datos; no se simulan

## Por tabla
|   tabla |   celdas_numericas |   celdas_cubiertas |   comprobaciones |   verificadas_desde_datos |   verificadas_desde_derivado |   discrepantes |   no_reproducibles |   valores_publicados_unicos |
|--------:|-------------------:|-------------------:|-----------------:|--------------------------:|-----------------------------:|---------------:|-------------------:|----------------------------:|
|       1 |                 21 |                  0 |                0 |                         0 |                            0 |              0 |                  0 |                           0 |
|       2 |                 17 |                  0 |                0 |                         0 |                            0 |              0 |                  0 |                           0 |
|       3 |                 32 |                  0 |                0 |                         0 |                            0 |              0 |                  0 |                           0 |
|       4 |                 22 |                  0 |                0 |                         0 |                            0 |              0 |                  0 |                           0 |
|       5 |                 47 |                  0 |                0 |                         0 |                            0 |              0 |                  0 |                           0 |
|       6 |                 10 |                  9 |               19 |                        18 |                            0 |              0 |                  1 |                          13 |
|       7 |                 13 |                  0 |                0 |                         0 |                            0 |              0 |                  0 |                           0 |
|       8 |                 40 |                 32 |               32 |                        32 |                            0 |              0 |                  0 |                          31 |
|       9 |                 28 |                 16 |               32 |                        32 |                            0 |              0 |                  0 |                          31 |
|      10 |                 36 |                 24 |               24 |                        24 |                            0 |              0 |                  0 |                          17 |
|      11 |                 60 |                 48 |               96 |                        96 |                            0 |              0 |                  0 |                          84 |
|      12 |                 13 |                  0 |                0 |                         0 |                            0 |              0 |                  0 |                           0 |
|      13 |                 15 |                 13 |               39 |                        39 |                            0 |              0 |                  0 |                          35 |
|      14 |                 36 |                 36 |               36 |                        36 |                            0 |              0 |                  0 |                          26 |
|      15 |                  6 |                  3 |                7 |                         7 |                            0 |              0 |                  0 |                           7 |
|      16 |                 13 |                  0 |                0 |                         0 |                            0 |              0 |                  0 |                           0 |
|      17 |                 42 |                 36 |               36 |                        36 |                            0 |              0 |                  0 |                          31 |
|      18 |                 42 |                 36 |               36 |                        36 |                            0 |              0 |                  0 |                          34 |
|      19 |                 30 |                 24 |               60 |                        60 |                            0 |              0 |                  0 |                          35 |
|      20 |                 24 |                 18 |               18 |                        18 |                            0 |              0 |                  0 |                          16 |
|      21 |                 24 |                 18 |               72 |                        72 |                            0 |              0 |                  0 |                          55 |
|      22 |                 90 |                 72 |              180 |                       180 |                            0 |              0 |                  0 |                          89 |
|      23 |                  7 |                  6 |               15 |                        15 |                            0 |              0 |                  0 |                           9 |
|      24 |                 41 |                 40 |               60 |                        60 |                            0 |              0 |                  0 |                          25 |
|      25 |                 12 |                  8 |               14 |                         4 |                           10 |              0 |                  0 |                          13 |
|      26 |                 16 |                  0 |                0 |                         0 |                            0 |              0 |                  0 |                           0 |
|      27 |                 10 |                  4 |               16 |                        15 |                            0 |              0 |                  1 |                          14 |
|      28 |                 16 |                 16 |               16 |                        16 |                            0 |              0 |                  0 |                          15 |
|      29 |                 11 |                 10 |               10 |                        10 |                            0 |              0 |                  0 |                          10 |
|      30 |                 15 |                  6 |               19 |                        15 |                            4 |              0 |                  0 |                          18 |
|      31 |                 29 |                  0 |                0 |                         0 |                            0 |              0 |                  0 |                           0 |
|      32 |                 19 |                  0 |                0 |                         0 |                            0 |              0 |                  0 |                           0 |
|      33 |                  5 |                  0 |                0 |                         0 |                            0 |              0 |                  0 |                           0 |
|      34 |                 23 |                  0 |                0 |                         0 |                            0 |              0 |                  0 |                           0 |
|      35 |                 10 |                  0 |                1 |                         0 |                            0 |              0 |                  1 |                           0 |
|      36 |                149 |                  0 |               33 |                        33 |                            0 |              0 |                  0 |                          29 |
|      37 |                 42 |                  0 |                0 |                         0 |                            0 |              0 |                  0 |                           0 |
|      38 |                 64 |                 56 |               56 |                        56 |                            0 |              0 |                  0 |                          34 |
|      39 |                  2 |                  0 |                0 |                         0 |                            0 |              0 |                  0 |                           0 |
|      40 |                 56 |                 49 |               49 |                        49 |                            0 |              0 |                  0 |                          29 |
|      41 |                 28 |                 28 |               28 |                        28 |                            0 |              0 |                  0 |                          24 |
|      42 |                 16 |                  0 |                0 |                         0 |                            0 |              0 |                  0 |                           0 |
|      43 |                 14 |                  0 |                0 |                         0 |                            0 |              0 |                  0 |                           0 |
|      44 |                378 |                  0 |                0 |                         0 |                            0 |              0 |                  0 |                           0 |
|      45 |                 41 |                 11 |               11 |                        11 |                            0 |              0 |                  0 |                          11 |
