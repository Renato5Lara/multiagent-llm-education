# Evidencia reproducible de la tesis, por objetivo específico

Tesis: *Validación de una arquitectura multiagente basada en inteligencia de enjambre para la adaptación multimodal en Programación.*
**Versión auditada:** informe `D2.9.7-CIERRE-BRECHAS-CORRECCION-CUADROS.docx` (sha256 `a6bb2934de7fd512…`). La versión vigente de la tesis formula **cinco** objetivos específicos (OE1–OE5), idénticos en el proyecto V7.1 (2026-10-17); un borrador antiguo (2026-09-21) tenía cuatro. Textos literales: [`auditoria/OBJETIVOS_LITERALES.json`](auditoria/OBJETIVOS_LITERALES.json).

**Objetivo del paquete:** que un asesor elija una cifra del informe, encuentre el archivo que la respalda, ejecute el cálculo y obtenga el mismo resultado, o vea por qué no puede. **No** prueba que las hipótesis se cumplan, ni que los experimentos se hicieran en las condiciones declaradas, ni que los registros sean auténticos (un hash prueba identidad frente a una referencia, no veracidad). Todas las campañas son **experimentales y no oficiales**, en un único equipo local.

## 1. Un notebook por objetivo (Google Colab, independientes entre sí)
Rama publicada: `repro/auditoria-integral-2026-10-19` del repositorio `Renato5Lara/multiagent-llm-education`. Abra el enlace, «Ejecutar todas» y confirme el aviso estándar de Colab para cuadernos de GitHub.

| Objetivo | Notebook | Tablas que concilia | Campañas |
|---|---|---|---|
| OE1 requisitos y desempeño | [`objetivo_1_requisitos_y_desempeno`](https://colab.research.google.com/github/Renato5Lara/multiagent-llm-education/blob/repro/auditoria-integral-2026-10-19/reproducibility/notebooks/objetivo_1_requisitos_y_desempeno.ipynb) | 5, 6, 37 y cifras en prosa | N1 |
| OE2 enjambre vs convencional | [`objetivo_2_enjambre_vs_convencional`](https://colab.research.google.com/github/Renato5Lara/multiagent-llm-education/blob/repro/auditoria-integral-2026-10-19/reproducibility/notebooks/objetivo_2_enjambre_vs_convencional.ipynb) | 8–11, 38 | N2, N9b |
| OE3 configuración interna | [`objetivo_3_configuracion_interna`](https://colab.research.google.com/github/Renato5Lara/multiagent-llm-education/blob/repro/auditoria-integral-2026-10-19/reproducibility/notebooks/objetivo_3_configuracion_interna.ipynb) | 13, 14, 15, 40 | N3, K10 (v2) |
| OE4 carga y tamaño del enjambre | [`objetivo_4_carga_y_tamano_del_enjambre`](https://colab.research.google.com/github/Renato5Lara/multiagent-llm-education/blob/repro/auditoria-integral-2026-10-19/reproducibility/notebooks/objetivo_4_carga_y_tamano_del_enjambre.ipynb) | 17–25 | N4, N8, N8b, N11 |
| OE5 precisión y usabilidad | [`objetivo_5_precision_y_usabilidad`](https://colab.research.google.com/github/Renato5Lara/multiagent-llm-education/blob/repro/auditoria-integral-2026-10-19/reproducibility/notebooks/objetivo_5_precision_y_usabilidad.ipynb) | 27–30, 35, 41 | N5, K10 (v2) |
| Índice transversal (todo el informe) | [`reproducibilidad_tesis`](https://colab.research.google.com/github/Renato5Lara/multiagent-llm-education/blob/repro/auditoria-integral-2026-10-19/reproducibility/notebooks/reproducibilidad_tesis.ipynb) | todas las recalculables + hashes de las Tablas 36 y 45 | todas |

Cada notebook: (A) objetivo literal, meta y limitaciones · (B) entorno · (C) clona el repositorio y verifica el SHA-256 de cada archivo · (D) valida los datos · (E) recalcula · (F) compara con el informe, cifra por cifra · (G) prueba negativa del comparador y pruebas rápidas · (H) conclusión limitada a la evidencia · (I) exportación. Los cinco notebooks por objetivo se ejecutaron en Colab sobre el commit `2fb5c046` (sin cambios posteriores en notebooks, scripts ni datos; el commit final no se ejecutó en Colab). El estado de cada uno está en [`auditoria/ESTADO_NOTEBOOKS_COLAB.csv`](auditoria/ESTADO_NOTEBOOKS_COLAB.csv).

## 2. Cómo localizar la fuente de una cifra
1. Busque la tabla y la celda en [`auditoria/CONCILIACION_TESIS_DATOS.csv`](auditoria/CONCILIACION_TESIS_DATOS.csv): trae el valor publicado y el recalculado sin redondear, la fuente, su hash, el script, la fórmula, la política de redondeo, la tolerancia y el estado.
2. El archivo de datos está en `data/experiments/<campaña>/…` (manifiesto con SHA-256: [`EVIDENCE_MANIFEST.csv`](EVIDENCE_MANIFEST.csv)). Mapa objetivo → indicador → campaña → tabla: [`auditoria/MAPA_OBJETIVOS_EVIDENCIAS.csv`](auditoria/MAPA_OBJETIVOS_EVIDENCIAS.csv). Estado por tabla: [`RESULTS_TRACEABILITY.csv`](RESULTS_TRACEABILITY.csv).

## 3. Qué está verificado y qué no
Detalle y método de conteo: [`auditoria/CONTEO_CIFRAS.md`](auditoria/CONTEO_CIFRAS.md) e [`auditoria/INFORME_AUDITORIA_FINAL.md`](auditoria/INFORME_AUDITORIA_FINAL.md).
- **1 011 comprobaciones numéricas** de tablas (un «valor comparado»; una celda «5,05 (4,57 a 5,58)» son 3): 1 002 coinciden a su precisión publicada, **3 difieren una unidad por doble redondeo del informe** (Tabla 13: ver [`auditoria/AUDITORIA_REDONDEO_TABLA13.md`](auditoria/AUDITORIA_REDONDEO_TABLA13.md); corrección propuesta en [`auditoria/REGISTRO_CAMBIOS_TESIS.csv`](auditoria/REGISTRO_CAMBIOS_TESIS.csv)), **0 discrepancias** y 6 no reproducibles. De las que coinciden, 14 lo hacen con un resultado *derivado* publicado (Tablas 25 y 30) y el resto desde datos originales.
- La cadena **registro por petición → `runs.csv`** se recalcula en 7 campañas (N2, N3, N4, N8, N8b, N9b, N11) y los 37 archivos que generan los scripts del proyecto se regeneran idénticos (byte a byte, o salvo finales de línea/ruido de punto flotante en Linux).
- **Cifras en prosa del OE1** (8) recalculadas desde los 9 500 ciclos de N1.
- **Todavía sin verificar** (tras el cierre de cobertura, [`auditoria/INFORME_CIERRE_COBERTURA.md`](auditoria/INFORME_CIERRE_COBERTURA.md)): 595 afirmaciones numéricas en prosa y 6 celdas de tablas están `PENDIENTE_DE_EVIDENCIA`; 887 afirmaciones en prosa tienen `VERIFICACION_PARCIAL` (217 de ellas solo porque el valor de diseño figura en un registro del paquete) (el valor existe en los datos recalculados, no la oración completa); estados categóricos de las Tablas 5 y 37; síntesis bibliográfica (32, 44); última fila de la Tabla 6 y estadísticas por perfil de la 27.
- **Sin datos, por diseño:** SUS y panel de expertos (**0 evaluadores reales**; no se simulan). El OE5 está evidenciado solo parcialmente: la meta F1_adapt ≥ 0,85 **no se alcanza** con v3 provisional (≈ 0,816) ni con v2 histórico (≈ 0,641).

## 4. Limitaciones científicas que se mantienen
`decision_table` es un sistema convencional **definido operacionalmente en el estudio**, no un baseline externo validado; `rules` es una **ablación** y `bruteforce` una **referencia de optimalidad**. `T_conv` es una medición exploratoria propuesta, distinta de TTFC. En el OE3 se ejecutó un ANOVA factorial; las pruebas planeadas (p. ej. Friedman con Holm) no se ejecutaron. Los experimentos son en **hardware local**; las condiciones objetivo (8 vCPU / 32 GB en la nube) **no se ejecutaron**. N11 tiene dos tramos con régimen de rendimiento distinto. N9 fue **abortada y descartada** (38 de 160) y no se combina con N9b. La verificación D2.7 la hizo el propio proyecto, no un tercero. Los OE1–OE3 no tienen hipótesis estadística formulada en la tesis.

## 5. Contenido
```
auditoria/     inventario, mapa objetivo→evidencia, conciliación tesis↔datos, redondeo, correcciones, comparador, conteo, estado de Colab, informe final
notebooks/     objetivo_1…objetivo_5 (+ índice reproducibilidad_tesis); sin salidas guardadas
data/          evidencia (≈ 253 MB; STAGING_REPORT.csv lista lo copiado y lo excluido) y transcripción de las tablas del informe
scripts/ tests/ environment/ outputs/ publicacion/ outputs/registro_ejecucion/
```
Ejecución local: `pip install -r environment/requirements-dev.txt`; `cd scripts && python reproduce_results.py [--oe oe1..oe5]`; `python -m pytest tests -q` (el código del proyecto se toma de `../backend`; con una copia aislada defina `REPRO_BACKEND`).

## 6. Exclusiones y tratamiento de datos
14 archivos de texto con rutas locales se publican como **copias sanitizadas** que **no** son idénticas a los originales ([`data/metadata/SANITIZACION.csv`](data/metadata/SANITIZACION.csv): hash de ambos). No se publican: el texto de la tesis (solo fragmentos de ±35 caracteres alrededor de cada cifra), observaciones in-process de gran tamaño regenerables, los registros por petición de la campaña N9 abortada (solo hashes), scripts con el correo personal del autor ni metadatos de terceros con correos. **Licencia:** el repositorio no declara ninguna y no se atribuye ninguna; véase [`LICENSE-DATA.md`](LICENSE-DATA.md).
