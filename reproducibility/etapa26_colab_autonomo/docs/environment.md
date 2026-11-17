# Entorno y versiones

Los resultados oficiales locales se calcularon con el entorno de `freeze_venv23_2026-11-13` (numpy 2.5.3, scipy 1.18.1, pandas 3.1.1, statsmodels 0.15.0, patsy 1.0.3, Python 3.13). Las figuras de la tesis se dibujaron con matplotlib 3.10.3 y la fuente Arial (Windows).

| Entorno | Python | numpy | scipy | pandas | statsmodels | matplotlib | Estado |
|---|---|---|---|---|---|---|---|
| Oficial local (resultados de la tesis) | 3.13 | 2.5.3 | 1.18.1 | 3.1.1 | 0.15.0 | 3.10.3 (solo figuras) | Referencia |
| Colab 2026-11-14 (notebooks anteriores, registro previo en Drive privado) | 3.13 | 2.4.6 | 1.16.3 | 2.2.3 | 0.15.0 | n/d | Ejecución previa, no re-verificada |
| Ejecución local limpia de esta etapa (2026-11-16) | 3.13.5 | 2.5.5 | 1.18.1 | 3.1.1 | 0.15.0 | 3.11.2 | Ver `docs/execution_report.md` |
| Colab real con los notebooks nuevos | — | — | — | — | — | — | **Pendiente** (requiere la cuenta del autor) |

Cada notebook imprime su entorno en la celda 1 y lo guarda en `outputs/reports/<OE>/resumen_<OE>.json`.

## Diferencias entre versiones que ya se conocen

- **scipy.** El p de Wilcoxon con diferencias nulas (OE3, «social frente a PSO») cambia entre 1.16.3 y 1.18.1 (0,023801 frente a 0,024311). Es un análisis de sensibilidad; el ajuste de Holm usa la prueba t y no cambia. La biblioteca clasifica esa única diferencia como «explicada por versión» **solo** si la versión de scipy difiere de 1.18.1; con 1.18.1 el mismo p debe ser idéntico.
- **matplotlib y fuente.** Con matplotlib 3.10.3 y Arial, el código de `figures.py` produce PNG idénticos bit a bit a los de la tesis (comprobado: 5 de 5, entrada = salidas oficiales de `04_ANALISIS_ESTADISTICO`). Con otra versión o sin Arial, los píxeles difieren aunque la serie dibujada sea la misma; por eso la comprobación válida es la comparación de la serie (`figure_data/*.csv`), no la de la imagen.

## Instalación

Colab trae numpy, scipy, pandas y matplotlib. Los notebooks instalan `statsmodels` solo si falta. No se fijan versiones para no forzar reinicios del kernel en Colab; en su lugar se **registran** y se clasifica cualquier diferencia numérica. Para reproducir con exactamente las versiones oficiales: `pip install numpy==2.5.3 scipy==1.18.1 pandas==3.1.1 statsmodels==0.15.0 matplotlib==3.10.3` en un entorno nuevo y reiniciar.
