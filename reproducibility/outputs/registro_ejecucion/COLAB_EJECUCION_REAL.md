# Ejecución real del notebook en Google Colab

Fecha: 2026-10-19. Notebook abierto desde `https://colab.research.google.com/github/Renato5Lara/multiagent-llm-education/blob/repro/publicable-2026-10-19/reproducibility/notebooks/reproducibilidad_tesis.ipynb`, «Ejecutar todas», entorno sin conexión previa (partida limpia), cuenta Google del autor, sin montar Drive ni usar credenciales. **Transcripción manual de las salidas visibles en pantalla** (no es una exportación automática del notebook; no se guardó el `.ipynb` ejecutado de Colab).

Entorno de Colab: Python 3.13.16; las celdas instalaron `numpy 2.5.4, pandas 3.0.6, scipy 1.18.1, statsmodels 0.15.0, matplotlib 3.11.2` (versiones fijadas). Los scripts corren en procesos nuevos y usan esas versiones; el kernel traía numpy 2.1.3 y matplotlib 3.10.0 preinstalados (por eso la celda B ahora imprime las versiones de un proceso nuevo). `pip` avisa de conflictos con `google-colab` y `numba`; no afectan al análisis.

## Tres ejecuciones y lo que cada una encontró
| # | Commit de la rama | Resultado | Hallazgo |
|---|---|---|---|
| 1 | `13d5a09` | Todas las celdas se ejecutan, 1540/1540 hashes, 858 `COINCIDE`, 3 `DIFERENCIA_EXPLICABLE`, 8 `NO_REPRODUCIBLE`, cadena petición→corrida verificada en 7 campañas. **Pero los 37 derivados `DIFIERE`.** | Los derivados publicados se generaron en Windows con finales de línea CRLF; Linux escribe LF. |
| 2 | `3967a7c` | 17 `COINCIDE_SALVO_FINALES_DE_LINEA`, 18 `COINCIDE_NUMERICO`, **2 `DIFIERE`** (`oe2_reanalysis.json`, `oe3_anova.csv`). | `oe2_reanalysis.json` contiene una ruta con barras de Windows; `oe3_anova.csv` tiene valores teóricamente cero (`sum_sq` ≈ 1e-30) cuyo ruido de punto flotante da diferencia relativa enorme entre plataformas. Las 861 cifras del informe seguían coincidiendo. |
| 3 | `439eb4c` | **0 `DIFIERE`**: 17 `COINCIDE_SALVO_FINALES_DE_LINEA` + 20 `COINCIDE_NUMERICO`. | Comparación con tolerancia relativa 1e-6 y absoluta 1e-12, y barras de ruta normalizadas (`repro_lib.comparar_archivos`, con pruebas). |

## Salidas de la ejecución 3 (commit `439eb4c`)
- Origen: clonado de `https://github.com/Renato5Lara/multiagent-llm-education.git` @ `repro/publicable-2026-10-19`; raíz `/content/tesis_repo/reproducibility`.
- Integridad: `manifiesto: 1540/1540 coinciden; difieren=0; faltan=0`.
- Validación: N2 80/80, N4 60/60, N8 120/120, N8b 60/60, N9b 160/160, N11 180/180 con 179 `ok` y `n11-oe4-3n-swarm|u100|N10-r01 (status = no_requests)` excluida.
- Eslabón 1 (peticiones → corrida): N2, N4, N8, N8b, N9b, N11 y N3 `VERIFICADO_DESDE_DATOS`, `no_coinciden = 0`.
- Eslabón 2 (derivados): `{'COINCIDE_NUMERICO': 20, 'COINCIDE_SALVO_FINALES_DE_LINEA': 17}`.
- Eslabón 3 (cifras): `{'COINCIDE': 858, 'NO_REPRODUCIBLE': 8, 'DIFERENCIA_EXPLICABLE': 3}`; la matriz de trazabilidad se muestra al final (18 tablas `VERIFICADO_DESDE_DATOS`, 6 `PARCIAL`, 1 `NO_REPRODUCIBLE`, 2 `NO_APLICA`).
- Tabla 8 mostrada en pantalla desde las 80 corridas de N2 (p. ej. decision_table 1 usuario: 13,3 · 14,7 · 23,9 · 67,4; swarm 25 usuarios: 1401,4 · 1523,5 · 2316,4 · 16,5).
- Duración total de las celdas: ≈ 1 min 38 s.

## Límites de esta comprobación
Se ejecutó una sola vez cada versión, con un solo tipo de entorno de Colab (CPU estándar). No se guardó el notebook ejecutado de Colab; la evidencia es esta transcripción y el registro del clon limpio local (`notebook_ejecutado_en_clon_limpio.sanitizado.ipynb`, versión anterior del paquete).
