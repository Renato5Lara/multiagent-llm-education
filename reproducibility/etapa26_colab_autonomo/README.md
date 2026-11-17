# Reproducción autónoma de los resultados OE1–OE5 (Google Colab + GitHub)

Seis notebooks que, desde un Colab limpio y con «Ejecutar todo», descargan los datos públicos de este repositorio (commit fijado), verifican su SHA-256, ejecutan el análisis estadístico sellado, comparan con las cifras de la tesis, generan tablas y las figuras de resultados y terminan con pruebas automáticas. **No hay que subir ni buscar ningún archivo.**

> **Use la etiqueta `repro-etapa26-v3`.** La `repro-etapa26-v2` es histórica (se conserva, pero sus paquetes de OE2-B contienen rutas locales que la v3 anonimiza) y la `repro-etapa26-v1` está descartada (falla en Windows); ver `docs/ETIQUETAS.md`.

Se reproduce el **análisis**; no se repiten las campañas, no se modifican datos originales, scripts ni umbrales, y ninguna campaña pasa a ser controlada. Los tiempos medidos son los del equipo local con la interferencia registrada.

| Objetivo | Notebook (abrir en Colab) | Paquetes que descarga | Figura de la tesis que genera | Tablas |
|---|---|---|---|---|
| OE1 | [OE1_reproduccion_autonoma](https://colab.research.google.com/github/Renato5Lara/multiagent-llm-education/blob/repro-etapa26-v3/reproducibility/etapa26_colab_autonomo/notebooks/OE1_reproduccion_autonoma.ipynb) | `oe1_http_p1` | Figura 1 | celdas, efectos, corridas_indicadores |
| OE2-A | [OE2A_reproduccion_autonoma](https://colab.research.google.com/github/Renato5Lara/multiagent-llm-education/blob/repro-etapa26-v3/reproducibility/etapa26_colab_autonomo/notebooks/OE2A_reproduccion_autonoma.ipynb) | `oe2a_colab_paquete` | ninguna en la tesis; una figura complementaria marcada como tal | medias_por_perfil |
| OE2-B | [OE2B_reproduccion_autonoma](https://colab.research.google.com/github/Renato5Lara/multiagent-llm-education/blob/repro-etapa26-v3/reproducibility/etapa26_colab_autonomo/notebooks/OE2B_reproduccion_autonoma.ipynb) | `oe2b_colab_paquete`, `oe2b_http_p1`, `p2` | Figura 2 | resumen_por_carga, estratos_por_carga |
| OE3 | [OE3_reproduccion_autonoma](https://colab.research.google.com/github/Renato5Lara/multiagent-llm-education/blob/repro-etapa26-v3/reproducibility/etapa26_colab_autonomo/notebooks/OE3_reproduccion_autonoma.ipynb) | `oe3_colab_paquete_v2` | Figura 3 | contrastes_efectos_principales |
| OE4 | [OE4_reproduccion_autonoma](https://colab.research.google.com/github/Renato5Lara/multiagent-llm-education/blob/repro-etapa26-v3/reproducibility/etapa26_colab_autonomo/notebooks/OE4_reproduccion_autonoma.ipynb) | `oe4_colab_paquete`, `oe4_http_p1`…`p4` | Figura 4 | celdas, contrastes, anova_* |
| OE5 | [OE5_reproduccion_autonoma](https://colab.research.google.com/github/Renato5Lara/multiagent-llm-education/blob/repro-etapa26-v3/reproducibility/etapa26_colab_autonomo/notebooks/OE5_reproduccion_autonoma.ipynb) | `oe5_colab_paquete` | Figura 5 | f1_por_perfil |

Estos notebooks sustituyen, sin borrarlos, a los 11 de `../etapa23_oe1_oe5/` y `OE*/` del trabajo anterior (que pedían `files.upload()`): cada uno reúne en un solo notebook lo que antes eran el individual y el integral. La versión 1 de OE3 sigue descartada.

## Estructura

```
manifests/data_manifest.json     paquete -> URL fijada al commit, tamaño, SHA-256, registros, anonimización
manifests/valores_oficiales.json 31 cifras de la tesis con su ruta en el resultado oficial; metas de diseño; hash de las 5 figuras de la tesis
paquetes_v3/                     los dos paquetes de OE2-B con la segunda anonimización
analisis_sellado/                copia legible (hash verificado) de los scripts de análisis que viajan dentro de los paquetes
src/repro/                       data_loading, runner, validation, official, figures, tables (código legible)
notebooks/                       los seis notebooks (generados por tools/generar_notebooks.py)
tools/                           generar_notebooks.py, ejecutar_local.py (ejecución local limpia)
tests/test_repro.py              pruebas unitarias sin red
docs/                            reproduction_guide, data_dictionary, environment, figure_traceability, execution_report
outputs/local/    salidas de la ejecución local limpia (figuras, tablas, informes); NO son de Colab
```

Los datos **no se duplican**, salvo dos paquetes: diez están en `../etapa23_oe1_oe5/paquetes/` en el commit `3c8953a58909c48929093ef1524eb7d0ad317378` (inmutable) y los dos de OE2-B (`oe2b_colab_paquete`, `oe2b_http_p1`) están en `paquetes_v3/` (commit `5622bf50d7a757446fd76c19fe78938831a4c7fa`), con una segunda anonimización: solo cambia el campo `error` de cinco líneas de `intentos.jsonl`. Las versiones anteriores de esos dos se conservan sin modificar.

## Estado de verificación

- Descarga pública sin credenciales, verificación de SHA-256 y análisis completo: **ejecutados** en un directorio vacío en Windows (2026-11-16), con las versiones oficiales y con versiones equivalentes a las de Colab (scipy 1.16.3, pandas 2.2.3). Ver `docs/execution_report.md`.
- **Ejecución en Google Colab real de estos notebooks: pendiente** (requiere la cuenta del autor). Los notebooks anteriores sí se ejecutaron en Colab el 2026-11-14 (registro en `../etapa23_oe1_oe5/README.md`).
- Pruebas unitarias: `python -m unittest discover -s tests -v`.

Guía paso a paso para un evaluador: `docs/reproduction_guide.md`.
