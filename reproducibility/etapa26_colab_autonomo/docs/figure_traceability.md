# Trazabilidad de las figuras de resultados de la tesis

Las cinco figuras de resultados de la tesis (versión CIERRE_FINAL) **no salieron de Colab**: las generó `hacer_figuras.py`, ejecutado en local sobre las salidas ya calculadas de `04_ANALISIS_ESTADISTICO`. Esta etapa demuestra la cadena completa y la hace reproducible desde Colab.

## Cadena demostrada

1. **Datos originales → resultado oficial.** Los scripts sellados (`analisis_oe*.py`, idénticos byte a byte a los de `04_ANALISIS_ESTADISTICO`) calculan los archivos de entrada de cada figura. Los notebooks los reejecutan desde los paquetes públicos.
2. **Resultado oficial → imagen de la tesis.** Con `repro.figures` (misma lógica de dibujo que `hacer_figuras.py`) y matplotlib 3.10.3 (la versión con que se dibujó la tesis, comprobada en los metadatos del PNG) sobre las salidas de `04_ANALISIS_ESTADISTICO`, los 5 PNG resultantes son **idénticos bit a bit** (mismo SHA-256) a los de `word/media` de la tesis. El script original también reproduce los 5 hashes.
3. **Notebook → figura.** Cada notebook dibuja la figura desde la salida del análisis que acaba de ejecutar y guarda la **serie dibujada** en CSV. Esa serie coincide con la dibujada desde `04_ANALISIS_ESTADISTICO`: idéntica o dentro de 1e-9 (tabla de abajo).

La imagen regenerada en otro entorno (por ejemplo Colab, sin Arial y con otra versión de matplotlib) **no** será idéntica bit a bit aunque la serie lo sea; por eso la prueba válida es la serie, no los píxeles.

## Tabla

| Figura (tesis) | Entrada | Paquete | Notebook | Archivo | Página (índice) | SHA-256 del PNG de la tesis | PNG regenerado desde 04 con matplotlib 3.10.3 | Serie del notebook frente a la de 04 (versiones oficiales / tipo Colab) |
|---|---|---|---|---|---|---|---|---|
| 1. Confiabilidad y correlación intrabloque | `resultados_oe1.json` | `oe1_http_p1` | OE1 | `fig_oe1.png` | 82 | `97e3b8376b03…` | idéntico | exacta / exacta |
| 2. Latencia P95, throughput y T_conv por carga | `resultados_oe2b.json` | `oe2b_*` | OE2-B | `fig_oe2.png` | 89 | `b4304598e9ad…` | idéntico | exacta / dentro de tolerancia (6,2e-11) |
| 3. Efectos principales sobre T_conv | `contrastes_efectos_principales.csv` | `oe3_colab_paquete_v2` | OE3 | `fig_oe3.png` | 96 | `3c8a35cf94e9…` | idéntico | dentro de tolerancia / exacta |
| 4. P95, throughput y T_conv por carga, workers y N | `celdas.csv` | `oe4_*` | OE4 | `fig_oe4.png` | 103 | `0e0ee2c48c51…` | idéntico | dentro de tolerancia / exacta |
| 5. Distribución del F1_adapt | `f1_por_perfil.csv` | `oe5_colab_paquete` | OE5 | `fig_oe5.png` | 109 | `e24f3db0fd67…` | idéntico | exacta / exacta (el CSV tiene el mismo SHA-256 que el oficial) |

Los hashes completos están en `manifests/valores_oficiales.json` (`figuras_tesis`). Las páginas son las del índice de figuras de la versión CIERRE_FINAL; no se verificaron contra el PDF.

## Diferencias deliberadas respecto de `hacer_figuras.py`

- Sin ruta absoluta de Windows: las entradas son parámetros.
- Fuente `Arial` con respaldo (`Liberation Sans`, `DejaVu Sans`).
- La etiqueta «media 0,804» se calcula de los datos; la línea de referencia 0,85, las metas 2 000 ms y 20 req/s y la banda del 5 % se leen de `manifests/valores_oficiales.json` (`metas_de_diseno`). Son metas de diseño del protocolo, no resultados.
- Cada figura guarda además SVG y el CSV de la serie.

## Figura complementaria (no está en la tesis)

`fig_oe2a_complementaria` (OE2-A): distribución del T_conv de los 5 000 ciclos y por lote. Se dibuja desde `raw_observations.csv`; la media geométrica del rótulo se lee del resultado del análisis. No sustituye ni modifica ninguna figura de la tesis.

## Qué no se hizo

No se modificó ninguna figura ni el documento de la tesis. Las figuras de la tesis siguen siendo las originales; esta etapa solo demuestra de dónde salen y permite regenerarlas.
