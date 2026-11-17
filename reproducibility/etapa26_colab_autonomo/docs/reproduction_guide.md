# Guía de reproducción para un evaluador externo

No necesita ningún archivo privado ni preguntar por datos: todo está en este repositorio público.

## 1. Dónde está todo

- Repositorio: <https://github.com/Renato5Lara/multiagent-llm-education>
- Código y notebooks: `reproducibility/etapa26_colab_autonomo/` (etiqueta inmutable `repro-etapa26-v3`).
- Datos: 12 paquetes ZIP. Diez en `reproducibility/etapa23_oe1_oe5/paquetes/`, fijados al commit `3c8953a58909c48929093ef1524eb7d0ad317378`; los dos de OE2-B en `reproducibility/etapa26_colab_autonomo/paquetes_v3/`, fijados al commit `5622bf50d7a757446fd76c19fe78938831a4c7fa`. Lista con URL, tamaño, SHA-256 y registros: `manifests/data_manifest.json`.

## 2. Cómo ejecutar un notebook

1. Abra el enlace de Colab de la tabla de `README.md` (por ejemplo OE5).
2. Menú **Entorno de ejecución → Ejecutar todo**. Un Colab nuevo basta; no hay que subir ni montar nada.
3. El notebook clona el código de la etiqueta, descarga los paquetes necesarios, verifica su SHA-256 contra el manifiesto, ejecuta los scripts de análisis sellados, compara, genera tablas y figuras y ejecuta las pruebas automáticas. Al final empaqueta `resultados_<OE>.zip` (en Colab se descarga solo).
4. Duración aproximada en un portátil: 5 a 20 s por notebook más la descarga (0,1 a 27 MB).

Si falta un paquete o su hash no coincide, el notebook **se detiene** e imprime el archivo, la URL y el hash esperado y el obtenido; nunca continúa con datos incompletos.

## 3. Qué corresponde a qué

| OE | Notebook | Paquetes | Gráficos | Tablas | Resultado oficial contra el que se compara | Limitaciones que deben tenerse en cuenta |
|---|---|---|---|---|---|---|
| OE1 | `OE1_reproduccion_autonoma` | `oe1_http_p1` | `fig_oe1` (Figura 1) | `celdas`, `efectos`, `corridas_indicadores` | 120 corridas válidas; referencia S = 1,000, P95 = 571 ms, 33,9 req/s; I-13 y correlaciones intrabloque | 120 de 120 corridas con interferencia; la confiabilidad cae con la pérdida de mensajes; RNF03 no se cumple (F1_adapt 0,8044 < 0,85) |
| OE2-A | `OE2A_reproduccion_autonoma` | `oe2a_colab_paquete` | complementaria (no está en la tesis) | `medias_por_perfil` | 5 000 ciclos; 67,14 ms [65,71; 68,59]; 2 770 ciclos con interferencia fuerte (de los 2 230 restantes, 302 sin cobertura del monitor) | un solo flujo (no mide capacidad); 302 ciclos sin cobertura del monitor (`limitaciones_conocidas.md`); campaña OE2A-02 no ejecutada (cuatro fallos de la compuerta de inicio) |
| OE2-B | `OE2B_reproduccion_autonoma` | `oe2b_colab_paquete`, `oe2b_http_p1`, `p2` | `fig_oe2` (Figura 2) | `resumen_por_carga`, `estratos_por_carga` | 120 válidas; 16 no válidas; 180 intentos conservados | depende de la carga y la interferencia; no todos los niveles cumplen a la vez las metas |
| OE3 | `OE3_reproduccion_autonoma` | `oe3_colab_paquete_v2` | `fig_oe3` (Figura 3) | `contrastes_efectos_principales` | 19 200 ciclos; 48 condiciones; 40 perfiles; 10 bloques | p de Wilcoxon de «social frente a PSO» depende de la versión de scipy (5,1e-4); la v1 está descartada |
| OE4 | `OE4_reproduccion_autonoma` | `oe4_colab_paquete`, `oe4_http_p1`…`p4` | `fig_oe4` (Figura 4) | `celdas`, `contrastes`, `anova_*` | 36 celdas; 216 válidas de 220 intentos | 216 de 216 con interferencia; análisis por bloques |
| OE5 | `OE5_reproduccion_autonoma` | `oe5_colab_paquete` | `fig_oe5` (Figura 5) | `f1_por_perfil` | 100 perfiles × 10 repeticiones; F1_adapt 0,8044238095238094; IC95 % [0,7785; 0,8303] | no alcanza 0,85; repeticiones dependientes (enmienda 1) |

## 4. Dónde están los resultados

En el notebook, `outputs/` (dentro del directorio de trabajo de Colab):

- `outputs/figures/<OE>/fig_oeN.png|svg` y `figure_data/fig_oeN_serie.csv` (los valores exactos dibujados).
- `outputs/tables/<OE>/*.csv` y `tablas_<OE>.xlsx`.
- `outputs/reports/<OE>/comparacion_reproducido_vs_local.csv`, `comparacion_reproducido_vs_cifras_de_la_tesis.csv`, `resumen_<OE>.json`.

Una copia de la ejecución local limpia está en `outputs/local/`.

## 5. Cómo verificar los hashes

Automático al inicio de cada notebook. Manual: descargue un paquete de la URL de `manifests/data_manifest.json` y compare `sha256sum` (o `Get-FileHash`) con el campo `sha256`. Dentro de cada paquete, los notebooks verifican además el `SHA256SUMS.txt` de la campaña (los datos originales) y, en OE2-B, los seis archivos anonimizados contra la suma de `anonimizacion_oe2b.json`.

## 6. Cómo comparar con la tesis

La celda «Comparación con las cifras de la tesis» lista cada cifra (esperada, obtenida, diferencia, estado). La celda siguiente clasifica la comparación con el resultado local en **exacta**, **dentro de tolerancia** (1e-9), **explicada por versión**, **no explicada** o **no reproducible**. Las pruebas automáticas fallan si hay una cifra que difiere o una diferencia no explicada.

Las figuras se comparan por su **serie dibujada**, no por parecido visual: `docs/figure_traceability.md` explica la cadena datos → script → CSV → figura de la tesis y por qué la imagen solo es idéntica bit a bit con matplotlib 3.10.3 y la fuente Arial.

## 7. Qué NO demuestra esta reproducción

Reproduce el cálculo a partir de los datos registrados; no demuestra que los datos se hayan adquirido en condiciones controladas (no lo fueron: hay interferencia ambiental documentada) ni repite ninguna campaña.
