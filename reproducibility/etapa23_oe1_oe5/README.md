# Comprobación reproducible de los resultados de los objetivos específicos OE1 a OE5

Esta carpeta contiene los cinco cuadernos de Google Colab y los paquetes de datos con los que se vuelve a ejecutar, desde los datos de entrada de cada campaña, el análisis estadístico de los cinco objetivos específicos y se compara con el resultado calculado en el equipo local. Cada cuaderno incluye la descripción del objetivo, los datos de entrada, la verificación de archivos contra sus hashes, las dependencias, la ejecución del análisis, la reconstrucción de los indicadores, la comparación con el resultado oficial, las diferencias numéricas y una celda final que calcula la conclusión de reproducibilidad.

## Alcance

Los cuadernos vuelven a ejecutar el análisis; no repiten las campañas, no regeneran ciclos ni corridas, no modifican datos originales, scripts, umbrales ni protocolos, y no convierten ninguna campaña en controlada. Los tiempos medidos son los del equipo local, con la interferencia de procesos ajenos registrada en cada campaña. Para OE1, OE2-B y OE4, además, el cuaderno recalcula los indicadores de cada corrida desde el registro de cada petición HTTP y comprueba que coinciden con los indicadores guardados. Reproducir el cálculo no equivale a reproducir la adquisición de los datos.

## Resultado de la ejecución en Google Colab (2026-11-14)

Cada cuaderno se ejecutó completo en un entorno nuevo de Colab (Python 3.13, numpy 2.4.6, scipy 1.16.3, pandas 2.2.3, statsmodels 0.15.0). La tolerancia de comparación es 1e-9 en valor absoluto o relativo; es un umbral de informe, no un umbral del protocolo.

| Cuaderno | Hojas comparadas | Diferencia absoluta máxima | Resultado |
|---|---|---|---|
| OE1 | 947; 120 corridas desde las peticiones | 2,8e-16 | Coincide |
| OE2 (A y B) | 245, 1 327 y 125; 120 corridas desde las peticiones | 6,2e-11 | Coincide |
| OE3 | 1 573 | 5,1e-04 en una hoja, el resto ≤ 2e-15 | Coincide salvo un p de Wilcoxon |
| OE4 | 1 802 y 35; 216 corridas desde las peticiones | 1,4e-10 | Coincide |
| OE5 | 86 y 30 | 1,0e-12 | Coincide |

La única diferencia que supera la tolerancia es el p de Wilcoxon del contraste «social frente a PSO» sobre la brecha de optimalidad en OE3 (0,024311 localmente con scipy 1.18.1 y 0,023801 en Colab con scipy 1.16.3). Se comprobó que depende de la versión de scipy: ambos entornos reciben los mismos datos, y el p de Wilcoxon con diferencias nulas cambia entre versiones. Es un análisis de sensibilidad; el ajuste de Holm se calcula con la prueba t y coincide.

## Cómo ejecutar un cuaderno

1. Abra el cuaderno en Colab, por ejemplo con `https://colab.research.google.com/github/Renato5Lara/multiagent-llm-education/blob/<rama>/reproducibility/etapa23_oe1_oe5/notebooks/OE3_comprobacion_colab.ipynb`.
2. Ejecute las celdas en orden. La celda de carga indica qué archivos de `paquetes/` subir (los paquetes por parte, de menos de 8 MB, se suben juntos o uno a uno desde el panel de archivos de Colab; si los archivos ya están, la celda no pide nada).
3. La última celda imprime la conclusión de reproducibilidad calculada, con la lista de hojas que difieren.

## Contenido y hashes

`SHA256SUMS.txt` contiene el hash SHA-256 de cada archivo. Cada paquete lleva dentro su propia lista de hashes de los datos originales, que el cuaderno verifica antes de analizar. Ningún paquete contiene credenciales, claves ni contraseñas.

## Privacidad: seis archivos anonimizados

Por privacidad, seis archivos de la campaña del componente por HTTP del segundo objetivo (cinco registros de Locust y el registro de intentos) se publican en copias anonimizadas: se sustituyó, con la misma longitud, el nombre del equipo y el usuario de Windows de las rutas temporales por valores neutros (`HOST001` y `USER`), sin alterar marcas de tiempo, métricas, códigos HTTP ni identificadores experimentales. Los análisis no leen esos archivos. El cuaderno de OE2 compara esos seis archivos con la suma anonimizada que figura en `anonimizacion_oe2b.json` (dentro de los paquetes) y todos los demás con la suma original de la campaña. El cuaderno de OE2 se ejecutó de nuevo en Colab con los paquetes anonimizados y el resultado fue idéntico.

| Archivo | Objetivo | Tamaño (bytes) | SHA-256 | Contenido |
|---|---|---|---|---|
| `notebooks/OE1_comprobacion_colab.ipynb` | OE1 | 15090 | `18e8e49fce3d3cc07a2390e056f214fb58f1a149d1a4fcc6cf131afe958529e2` | Cuaderno de comprobación reproducible en Google Colab |
| `notebooks/OE2_comprobacion_colab.ipynb` | OE2 | 27442 | `a31526e8bcd0fb7f25efd8042e1767821a0fe13c14d8a596774e8331487ac5e2` | Cuaderno de comprobación reproducible en Google Colab |
| `notebooks/OE3_comprobacion_colab.ipynb` | OE3 | 9698 | `4dfc6124650c681061bceedc9faa53358bc16eda172dc468d0a28df2d2b7ad2f` | Cuaderno de comprobación reproducible en Google Colab |
| `notebooks/OE4_comprobacion_colab.ipynb` | OE4 | 22240 | `8b21b61b5bd4b9659588929caea37bc3ab5cff0820f3b4b56415dddc36e93321` | Cuaderno de comprobación reproducible en Google Colab |
| `notebooks/OE5_comprobacion_colab.ipynb` | OE5 | 9022 | `08dbea317be60c3101bd87abc2250b6ad4fbbc9c47da2e73145af5e701f5695e` | Cuaderno de comprobación reproducible en Google Colab |
| `paquetes/oe1_http_p1.zip` | OE1 | 7231736 | `27e84f86c40430878f2238a22b4fe22b08cfbb2d6eb3b9044f6e4012dd0f8eeb` | Registro por petición HTTP de las 120 corridas válidas de OE1 (indicadores por corrida) |
| `paquetes/oe2a_colab_paquete.zip` | OE2 | 408415 | `2ae5a013b7b617b4e5073e854fdc6cefbc6d039254f105da76ce3957d40bb223` | Observaciones por ciclo, monitor, planes y script de análisis de OE2-A, con el resultado local |
| `paquetes/oe2b_colab_paquete.zip` | OE2 | 596239 | `af7ce8508a484e859c402c8c3b8e3fcb6e0d05c2da8ae8862fb36f9a582c2447` | Indicadores por corrida, planes, monitor, registros y script de análisis de OE2-B, con el resultado local |
| `paquetes/oe2b_http_p1.zip` | OE2 | 7604816 | `b3f67b47efe321e7bec3ab50dae660fa1f6b9d31d273a3b061fc2c1f3f488e3c` | Registro por petición HTTP de OE2-B, parte 1 de 2 |
| `paquetes/oe2b_http_p2.zip` | OE2 | 4159947 | `7642676a1f9bf77ed19e93df3b33f53fe4f21c4f9841a1b624e59c8d2caab9fd` | Registro por petición HTTP de OE2-B, parte 2 de 2 |
| `paquetes/oe3_colab_paquete_v2.zip` | OE3 | 1455878 | `8044d6635bd3681f437112842b8abc2cf9a4004e035642dc79ecb311e101f029` | Observaciones por ciclo (19 200), lotes, entorno, monitor y script de análisis de OE3, con el resultado local |
| `paquetes/oe4_colab_paquete.zip` | OE4 | 633365 | `952af04cad980bdbdf7064b0b03c57c359b7c1abb5a629d67de8c4441c8ad9e6` | Indicadores por corrida, planes, monitor y scripts de análisis de OE4, con el resultado local |
| `paquetes/oe4_http_p1.zip` | OE4 | 7541357 | `0a9c1b19a16aeaad7297808055809480746ef050ad106da628bade57864f9fda` | Registro por petición HTTP de OE4, parte 1 de 4 |
| `paquetes/oe4_http_p2.zip` | OE4 | 7652602 | `81daba0090e1ea2df0a4abb263b70078dc69fadf007f4c6a2101b2caaec56c1b` | Registro por petición HTTP de OE4, parte 2 de 4 |
| `paquetes/oe4_http_p3.zip` | OE4 | 7620652 | `eaac9cc762dd2ed7f6e3bbef39fbeccb9cccaef66a93bcbbf722c16bb91ebc57` | Registro por petición HTTP de OE4, parte 3 de 4 |
| `paquetes/oe4_http_p4.zip` | OE4 | 2007919 | `1fcfafb6a7109b60749d3179bf2e8ecc8407f3caaa4fb8414c5e6ec72060d7cb` | Registro por petición HTTP de OE4, parte 4 de 4 |
| `paquetes/oe5_colab_paquete.zip` | OE5 | 86891 | `5825a80a59b03a5ea5669f7c2521c5147ef48f60b4d90fd009931bccd41e5163` | Ciclos con el vector de selección, perfiles, referencia gold sellada y scripts de análisis de OE5, con el resultado local |
