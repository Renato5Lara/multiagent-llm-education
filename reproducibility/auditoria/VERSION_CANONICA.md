# Versión canónica del documento de tesis

Matriz completa de 33 candidatos (sha256, fecha interna del DOCX, párrafos, tablas): [`MATRIZ_VERSIONES_DOCUMENTO.csv`](MATRIZ_VERSIONES_DOCUMENTO.csv), generada por `scripts/matriz_versiones.py`.

## El documento «1. Formato del informe de tesis - Ingeniería - Nuevo.docx»
- Ruta: `Documents\Cursos 2026-20\Tesis II\1. Formato del informe de tesis - Ingeniería - Nuevo.docx` (DOCX, 1 188 602 bytes).
- sha256 `2d0b486a118f6518a0a0db7f5f580ebe4896c95d3e747c957549bfb6d6394af8`.
- Fecha interna de modificación (core.xml): 2026-10-15 15:29 UTC; fecha del archivo: 2026-10-15 10:29 (hora local).
- **Es byte a byte idéntico a `…2026-10-15 - D2.9.3-CIERRE-EDITORIAL.docx`** (mismo sha256, mismo tamaño y misma fecha). Tiene 3 810 párrafos, 90 títulos de tabla (45 tablas, con las Tablas 1–45 del informe de resultados N1–N11) y menciona N11 53 veces.
- El archivo más antiguo con nombre sin «Nuevo» (`1. Formato del informe de tesis - Ingeniería.docx`, 2026-06-22) es otro documento anterior (715 párrafos, 7 tablas, sin resultados).

## Relación con D2.9.7
Entre D2.9.3 (= «Nuevo») y D2.9.7 hay cuatro versiones posteriores, todas del 2026-10-16 (D2.9.4 a D2.9.7, 05:53–12:03 UTC), y D2.9.7 es la más reciente de la serie. Comparación párrafo a párrafo («Nuevo» frente a la copia corregida de D2.9.7), excluyendo los números de página de los índices:
- **Resultados y tablas idénticos**, salvo las 5 cifras de la Tabla 13 corregidas (η², `k_stop`, T_conv de PSO), que en «Nuevo» conservan el doble redondeo.
- Contenido **añadido** en D2.9.7: la sección de discusión y cierre de brechas (20 brechas, 4 por objetivo), y tres notas de «documento no incorporado» en los anexos administrativos.
- No hay párrafos eliminados y ninguna cifra de resultados, objetivo, hipótesis ni umbral cambia entre ambas versiones.

## Decisión
**La referencia canónica sigue siendo la copia de trabajo `D2.9.7-CORREGIDO-REDONDEO-TABLA13.docx`** (sha256 `1bd0894c9586e4330b2f5d61851cf33eb8c6a5242187906f4564752ac4ae13c3`; original D2.9.7 `a6bb2934de7fd512…` intacto). «Nuevo» **no** la sustituye: es una versión anterior que D2.9.7 contiene y amplía. Como las tablas y los resultados son los mismos, toda la conciliación ya hecha vale también para «Nuevo» (salvo la Tabla 13 corregida). Si el autor prefiere usar «Nuevo» como base de entrega, las 5 correcciones de la Tabla 13 deberían aplicarse también a ese archivo y se perdería la sección de cierre de brechas; esa decisión es suya y no se ha tomado.

Los objetivos OE1–OE5 son idénticos en ambos documentos y en el proyecto V7.1; `OBJETIVOS_LITERALES.json` no cambia.
