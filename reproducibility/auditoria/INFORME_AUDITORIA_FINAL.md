# Informe de auditoría final

Rama `repro/auditoria-integral-2026-10-19` del repositorio `Renato5Lara/multiagent-llm-education`. Versión de la tesis auditada: D2.9.7 (sha256 `a6bb2934de7fd512…`). Fecha: 2026-10-19.

## A. Estado general y conteos
- **Cinco objetivos** vigentes (OE1–OE5; los mismos en D2.9.7 y en el proyecto V7.1). La idea de «cuatro» viene de un borrador de 2026-09-21. Hay **cinco notebooks** por objetivo, más un índice transversal. Si se prefiere entregar cuatro, el OE5 queda con evidencia parcial (sin SUS ni panel); no lo he decidido yo.
- **1 011 comprobaciones numéricas** de tablas (un valor comparado; una celda «5,05 (4,57 a 5,58)» son 3): 1 002 coinciden a su precisión publicada, 3 difieren una unidad por doble redondeo (Tabla 13), **0 discrepancias**, 6 elementos no reproducibles. 991 se verifican desde datos originales y 14 desde un resultado derivado publicado (Tablas 25 y 30).
- **«861» y «8 no reproducibles».** 861 eran comprobaciones, no celdas ni valores únicos (el informe anterior tenía 869: 861 + 8 + 0). Los 8 eran elementos del informe, varios agrupando tablas enteras. Detalle y método de conteo: `CONTEO_CIFRAS.md`/`.csv`.
- **Cobertura.** De 1 665 celdas numéricas, 617 tienen al menos una comprobación. En `CONCILIACION_TESIS_DATOS.csv` (3 931 filas) quedan 812 afirmaciones en prosa `PENDIENTE_DE_EVIDENCIA`, 670 con `VERIFICACION_PARCIAL` y 6 celdas pendientes. **Esto no es una verificación completa de la tesis.**

## B. Por objetivo (resultado de Colab; ver C)
| Objetivo | Tablas | Cifras | Resultado |
|---|---|---|---|
| OE1 | 5, 6, 37 + prosa | 18 | 16 desde datos; 2 no reproducibles (Tabla 6 «usuarios», estados de 5/37); 8 cifras en prosa recalculadas desde los 9 500 ciclos de N1 |
| OE2 | 8–11, 38 | 240 | 240 coinciden |
| OE3 | 13, 14, 15, 40 | 131 | 128 coinciden + 3 con diferencia explicada (Tabla 13) |
| OE4 | 17–25 | 491 | 491 coinciden (481 desde datos, 10 desde derivado) |
| OE5 | 27–30, 35, 41 | 86 | 83 coinciden; 3 no reproducibles (SUS sin evaluadores, estadísticas por perfil); **meta F1_adapt ≥ 0,85 no alcanzada** (v3 provisional ≈ 0,816; v2 histórico ≈ 0,641) |

La suma (966) no llega a las 1 011: el resto no está en estos cinco notebooks. Pendientes sin evidencia: Tablas 32/44 (síntesis bibliográfica), última fila de la Tabla 6, celdas «sin efecto» de la Tabla 13, SUS y panel de expertos (0 evaluadores; no se simulan).

## C. Ejecución real en Colab
Los cinco notebooks se ejecutaron en Colab el 2026-10-19 con «Ejecutar todas», entorno limpio, commit `2fb5c046`, Python 3.13.16 y las versiones fijadas. Todos terminaron sin error y con **0 discrepancias**, prueba negativa detectada y 10 pruebas rápidas aprobadas. Detalle: `outputs/registro_ejecucion/COLAB_EJECUCION_OE1_OE5.md` y `ESTADO_NOTEBOOKS_COLAB.csv`.

**Qué es automático y qué fue transcrito.** La ejecución es real; el registro es una **transcripción manual** de lo visible en pantalla (no se exportó el `.ipynb` ejecutado). La línea `RESUMEN_COLAB` no se leyó en pantalla en ningún notebook; las cifras salen de la celda G. Los hashes `1545/1545` se leyeron en OE1–OE3; en OE4–OE5 se deducen (la celda aborta si algo no coincide). El índice `reproducibilidad_tesis` no se reejecutó en este commit (última ejecución Colab: `439eb4c`, 3 corridas que encontraron y resolvieron diferencias CRLF/LF y ruido de punto flotante; ver `COLAB_EJECUCION_REAL.md`).

## D. Discrepancias con la tesis
Una familia, tres cifras y cinco apariciones en la Tabla 13 (OE3, N3), todas por **doble redondeo** demostrado con los datos (`AUDITORIA_REDONDEO_TABLA13.md`):
| Cifra | Informe | Correcto |
|---|---|---|
| η² de la heurística | 0,50 | 0,49 |
| `k_stop` con heurística (tabla y §6.5.4) | 1,51 | 1,50 |
| T_conv de PSO (tabla y §6.5.5) | 76,5 | 76,4 |

Error de transcripción de una unidad que no cambia ninguna conclusión. Registrado en `REGISTRO_CAMBIOS_TESIS.csv` (C13-1…5). Se corrigió una **copia** del DOCX (original intacto; solo `word/document.xml` difiere, 5 párrafos); la copia no se renderizó con Word y **no está publicada**. No se halló ninguna otra cifra con el mismo problema.

## E. Integridad, seguridad y estado de `main`
- Manifiesto de 1 545 archivos con SHA-256: coinciden todos. Un hash prueba identidad frente a una referencia, no autenticidad de la medición.
- 14 archivos de texto se publican como copias sanitizadas (`data/metadata/SANITIZACION.csv`). No se publican correos, claves ni rutas locales (revisión heurística), ni el texto de la tesis; sí está el texto de sus tablas (`informe_D2.9.7_tablas.json`), que el autor puede retirar.
- Sin licencia declarada ni atribuida.
- `main` no se tocó; no hubo reescritura de historial ni `force push`. La rama de respaldo `repro/publicacion-reproducible-2026-10-19` no se publicó.
- Comparador: la tolerancia es media unidad del último decimal publicado y nunca se amplió; el control secundario de archivos regenerados usa tolerancias distintas (`AUDITORIA_COMPARADOR.md`). Riesgo residual declarado allí.

## F. Conclusión científica
1. **¿Se reproducen las cifras de la tesis?** Las que tienen cálculo determinista y datos publicados (1 005 de 1 011 comprobaciones, con 3 correcciones de una unidad), sí.
2. **¿Están todas cubiertas?** No: ver cobertura en A.
3. **¿Se alcanza la meta F1_adapt ≥ 0,85?** No con los datos disponibles.
4. **¿Se cumple H1 (F1, L_resp, SUS)?** No puede afirmarse: no hay SUS ni expertos.
5. **¿Es un benchmark contra sistemas convencionales externos?** No: `decision_table` es una definición operacional del estudio; `rules` es una ablación y `bruteforce` una referencia de optimalidad.
6. **¿Condiciones objetivo?** No: hardware local, un único equipo, campañas no oficiales; la nube 8 vCPU/32 GB no se ejecutó.
7. **¿Validación independiente?** No: la hizo el propio proyecto.
8. **¿Qué demuestra este paquete?** Que con estos archivos y estos scripts el cálculo da el valor publicado, o muestra por qué no puede. No demuestra causalidad ni que las campañas se ejecutaran como se declara.

## G. Fase de cierre de cobertura (posterior a Colab)
Detalle en `INFORME_CIERRE_COBERTURA.md`. Resumen: las 45 comprobaciones fuera de los notebooks son transversales (Tablas 36 y 45 de hashes y 32/44), 966 + 45 = 1 011; la prosa pendiente baja de 812 a 595 y la parcial sube de 670 a 887 **solo** porque 217 valores de diseño existen en registros del paquete (verificación débil, no de la oración completa); ninguna afirmación pasó a `COINCIDE`. Los commits `2fb5c04` → `2d06690` no cambian notebooks, scripts ni datos, por lo que la ejecución en Colab sigue siendo válida para ellos, pero el commit final **no** se ejecutó en Colab. La tesis **no** queda verificada por completo.
