# Informe de ejecución y reproducción

Fecha: 2026-11-16. **Estas ejecuciones fueron locales (Windows, Python 3.13.5), no en Google Colab.** La ejecución en Colab real de los notebooks nuevos queda **pendiente**; la hace el autor con su cuenta.

## Qué se ejecutó

Cada uno de los seis notebooks se ejecutó de principio a fin con `tools/ejecutar_local.py` (nbclient) en un **directorio vacío**, sin ningún archivo previo: descarga HTTP pública desde `raw.githubusercontent.com` al commit `3c8953a…`, verificación SHA-256 contra el manifiesto, verificación interna (`SHA256SUMS` de cada campaña), recálculo desde las peticiones HTTP (OE1, OE2-B, OE4), análisis, comparaciones, tablas, figuras, pruebas automáticas y resumen. El código se tomó del árbol local (`REPRO_LOCAL_REPO`); los datos, de GitHub. Las 6 ejecuciones terminaron **sin errores**, en dos entornos:

| Entorno | numpy | scipy | pandas | statsmodels | Propósito |
|---|---|---|---|---|---|
| Versiones oficiales | 2.5.5 | 1.18.1 | 3.1.1 | 0.15.0 | Mismas versiones de scipy/pandas/statsmodels que los resultados de la tesis |
| Versiones tipo Colab | 2.3.5 | 1.16.3 | 2.2.3 | 0.15.0 | Las versiones de scipy y pandas del Colab del 2026-11-14 |

## Resultados

| OE | Versiones oficiales: comparación con el resultado local | Versiones tipo Colab: comparación con el resultado local | Cifras de la tesis (31 en total) |
|---|---|---|---|
| OE1 | 5 exactas | 3 exactas, 2 dentro de tolerancia (7,8e-11) | 6 de 6 (2 exactas, 4 dentro del redondeo) |
| OE2-A | 1 exacta | 1 dentro de tolerancia (6,0e-11) | 6 de 6 (3 y 3) |
| OE2-B | 5 exactas | 1 exacta, 4 dentro de tolerancia (6,2e-11) | 4 de 4 exactas |
| OE3 | 2 exactas | 1 exacta, **1 explicada por versión**: p de Wilcoxon `contrastes/27` 0,023801 frente a 0,024311 (5,1e-4) | 4 de 4 exactas |
| OE4 | 8 exactas | 1 exacta, 7 dentro de tolerancia (6,7e-11) | 5 de 5 exactas |
| OE5 | 2 exactas | 2 dentro de tolerancia (1,0e-12) | 6 de 6 (4 y 2) |

Recálculo desde las peticiones HTTP: OE1 120 de 120 corridas con los 12 campos idénticos; OE2-B 120 de 120 (133 intentos recalculados con registro de peticiones); OE4 216 de 216 (217 intentos recalculados); diferencia máxima 0,0 en los tres.

La diferencia de la tabla (OE3, Wilcoxon) coincide exactamente con la que registró el Colab del 2026-11-14 (0,023801 con scipy 1.16.3): es un resultado **independiente** que corrobora aquel registro, pero no lo sustituye. Con scipy 1.18.1 el mismo p es idéntico al oficial.

Las comparaciones de «exacta» y «dentro de tolerancia» se hacen contra el resultado local sellado que viaja en cada paquete, que es idéntico al de `04_ANALISIS_ESTADISTICO` (verificado por hash). Las 31 cifras de la tesis se comprueban además aparte, en cada notebook.

## Figuras

Ver `docs/figure_traceability.md`: PNG regenerados desde las salidas oficiales con matplotlib 3.10.3 idénticos bit a bit a los de la tesis (5 de 5); series de los notebooks idénticas o dentro de 1e-9 en las dos ejecuciones.

## Pruebas unitarias

`python -m unittest discover -s tests`: 12 pruebas, todas superadas (clasificación de diferencias, detención ante hash incorrecto o ruta insegura, manifiestos con URL fijada a un commit, ausencia de datos personales en los manifiestos).

## Lo que NO se comprobó

- Ejecución en Google Colab real de los notebooks nuevos (ni su clonado de la etiqueta inmutable `repro-etapa26-v1` desde un Colab).
- Que el PDF de la tesis tenga las figuras en las páginas del índice (se usó el índice del DOCX).
- Que los ids de Drive de las ejecuciones previas sigan accesibles con su contenido (solo se consultaron metadatos en la etapa anterior).

## Salidas

`outputs/local/oficial/` (figuras PNG/SVG, series CSV, tablas CSV/XLSX, informes) y `colablike/reports/`.
