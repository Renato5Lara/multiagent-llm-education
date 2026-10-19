# Informe de correcciones propuestas a la tesis (D2.9.7)

**Qué se corrige y qué no.** Solo cambios de **transcripción** respaldados por los datos fuente. No se modifican objetivos, hipótesis, umbrales, metodología aprobada ni datos originales, y **no se borra ninguna limitación**.

## 1. Correcciones aplicadas a una copia del DOCX
Registro completo en `REGISTRO_CAMBIOS_TESIS.csv` (valor anterior, valor corregido, ubicación, evidencia, causa y dependientes revisados). Las cinco sustituciones corrigen **tres cifras** y sus dos repeticiones en prosa:

| id | Valor | Ubicación |
|---|---|---|
| C13-1 | η² de la heurística 0,50 → **0,49** | Tabla 13 |
| C13-2 / C13-3 | `k_stop` con heurística 1,51 → **1,50** | Tabla 13 y §6.5.4 |
| C13-4 / C13-5 | T_conv de PSO 76,5 → **76,4** | Tabla 13 y §6.5.5 |

**Cómo se aplicó.** `scripts/corregir_docx.py` hace sustituciones de cadenas exactas que aparecen **una sola vez** y dentro de un único nodo de texto del XML (no toca el formato), y verifica el resultado:
- Original: `…D2.9.7-CIERRE-BRECHAS-CORRECCION-CUADROS.docx`, sha256 `a6bb2934de7fd512…` — **sin cambios** (comprobado antes y después).
- Copia corregida: `…2026-10-19 - D2.9.7-CORREGIDO-REDONDEO-TABLA13.docx`, sha256 `1bd0894c9586e433…`, en la misma carpeta que el original.
- Comparación de ambos: **una sola entrada del ZIP difiere** (`word/document.xml`) y **exactamente 5 párrafos** cambian (índices 1198, 1199, 1210, 1293, 1332 del recorrido del documento).
- Con las tablas de la copia, `reproduce_results.py` da **1 005 coincidencias, 0 diferencias explicables, 6 no reproducibles**.

**Limitación.** No se pudo renderizar la copia con Word ni exportarla a PDF en este entorno: la comprobación de formato es por comparación estructural del ZIP/XML (idéntico salvo los 5 textos), no visual. Antes de entregar, ábrala y revise las celdas citadas. La copia **no está publicada** en el repositorio (contiene el texto completo de la tesis).

## 2. Cambios que **no** se hacen y por qué
- Cifras con estado `PENDIENTE_DE_EVIDENCIA` o `NO_REPRODUCIBLE` (ver `CONCILIACION_TESIS_DATOS.csv`): no se sustituyen por estimaciones.
- Nada de lo que depende de evaluadores humanos (SUS, panel de expertos): no existen datos.
- Cifras citadas de la literatura: no son resultados del proyecto.

## 3. Observaciones verificadas durante la auditoría (no numéricas)
- 2 de los 33 hashes citados en la Tabla 36 correspondían a archivos que no estaban publicados (`oe3_run/environment.json` de N1 y el `README.txt` del intento fallido de N4); ya se incorporaron al paquete y sus prefijos SHA-256 **coinciden** con los del informe.
- Numeración vigente comprobada en D2.9.7: Tabla 35 = ítems del cuestionario SUS (instrumento sin aplicar) y Tabla 36 = trazabilidad de evidencias del Anexo 2. Una versión anterior de la matriz de trazabilidad de este paquete los había confundido; está corregido aquí, no en la tesis.
- El informe vigente formula cinco objetivos específicos; no se detectó en D2.9.7 ninguna mención a «cuatro objetivos» como número de objetivos (búsqueda no exhaustiva en la prosa; el borrador de 21-sep sí tiene cuatro).
