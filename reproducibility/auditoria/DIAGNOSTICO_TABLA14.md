# Diagnóstico de la Tabla 14 y de los p del OE3 (fase 18)

Evidencia: [`TABLA14_REPRODUCCION.csv`](TABLA14_REPRODUCCION.csv), generado por [`scripts/auditoria_tabla14.py`](../scripts/auditoria_tabla14.py) (requiere `pandas`, `statsmodels` y `scipy`; ejecutado con el Python de Anaconda). Datos: las 240 corridas de N3 (`data/experiments/oe_n3_2026-10-06/runs_oe3.csv`), con el logaritmo del T_conv.

## 1. Qué prueba produce cada cifra

| Cifras | Tablas o pasajes | Análisis | Modelo y g. l. residuales | Inferencia | Corrección |
|---|---|---|---|---|---|
| η² parcial y p de los cinco efectos principales (0,980; 0,879; 0,876; 0,495; 0,033; p = 0,001 o 0,015) y «interacciones significativas (p entre 0,001 y 0,003)» | Tabla 13, Tabla 16 (filas «p-valor» y «Tamaño del efecto»), §6.3.4 | **A** — `adaptation_swarm/oe/factorial.py` | todas las interacciones; sumas de cuadrados tipo III con codificación de suma cero; 48 parámetros; **192 g. l.** | **por permutación** (Freedman–Lane, 999; mínimo posible 0,001) | **ninguna** (cada p está sin corregir) |
| η² parcial y «p de Holm» de la Tabla 14 (0,979; 0,874; 0,871; 0,483; 0,031; …) y «p de Holm = 0,058» | Tabla 14, §6.3.5 («ANOVA tipo II… con corrección de Holm sobre 15 términos»), B3.1 (§6.7) | **B** — `oe_n8_2026-10-13/scripts/oe3_reanalysis.py` | efectos principales e interacciones de **dos** factores; tipo II; **219 g. l.** | **prueba F paramétrica** | **Holm sobre 15 términos** por respuesta |
| «p de Holm = 0,049 en el análisis de rangos» | §6.3.5 | **B′** — el mismo modelo B sobre los rangos | ídem | prueba F sobre rangos | Holm sobre 15 términos |

Las nueve filas de la Tabla 14 y las cinco de las Tablas 13 y 16 **se reproducen** con las cifras publicadas (η² a tres decimales; p de Holm con el orden de magnitud correcto), y las cuatro interacciones de dos factores con p por permutación < 0,05 tienen p entre 0,001 y 0,003, como dice la Tabla 16. La diferencia entre los η² de las Tablas 13 y 16 y los de la Tabla 14 (por ejemplo, 0,980 frente a 0,979 y 0,495 frente a 0,483) no es un error: son modelos distintos.

**Clasificación del hallazgo: metodológico (de rotulado), no factual.** No hay una cifra errónea. Lo que falta es que la tesis diga con claridad cuál de los dos análisis produce cada tabla.

## 2. Lo que la redacción actual no deja claro

1. La **Tabla 14** se titula «p de Holm por término» sin decir que son p de la prueba F paramétrica. Con residuos que **no son normales** (Shapiro-Wilk del modelo completo: p = 4 × 10⁻⁴, dato que la propia Tabla 16 invoca para elegir la permutación), los p paramétricos extremos (hasta 10⁻¹⁸⁴) no son probabilidades fiables: indican efectos enormes, no una probabilidad real de 10⁻¹⁸⁴. El §6.3.5 ya advierte que «se interpretan los tamaños del efecto».
2. La **Tabla 13** y la fila «p-valor» de la **Tabla 16** presentan p por permutación **sin corregir**, junto a los de Holm de la Tabla 14. Para las réplicas de consumidores, p = 0,015 (permutación, sin corregir) se ve «significativo» al lado de p de Holm = 0,058 (paramétrico) y 0,049 (rangos). Si se corrigiera el p por permutación con Holm sobre los 31 términos del modelo completo daría 0,345 (cifra informativa: la familia de la corrección depende de una decisión que el texto no toma).
3. El §6.3.6 y la Tabla 16 hablan de «valores p por permutación con piso en 0,001» y los lectores pueden creer que la Tabla 14 también lo es.

## 3. Propuesta de rotulado (no aplicada al DOCX; decisión del autor, C36)

| Dónde | Redacción propuesta |
|---|---|
| Título de la Tabla 14 | «ANOVA tipo II del T_conv (en escala logarítmica) y de la brecha respecto del óptimo: η² parcial y p de la prueba F con corrección de Holm (15 términos) por término (campaña N3; no oficial)» |
| Nota al pie de la Tabla 14 | «Modelo con efectos principales e interacciones de dos factores (219 g. l. residuales). Los p son paramétricos (F) y los residuos no son normales; los valores extremos indican efectos grandes y no deben leerse como probabilidades exactas. Los η² difieren ligeramente de los de la Tabla 13, que proceden del modelo con todas las interacciones.» |
| Encabezado de la Tabla 13 | «(p por permutación sin corregir; η² parcial del modelo completo)» |
| Fila «p-valor» de la Tabla 16 | añadir «sin corregir por contrastes múltiples» |

## 4. Alternativas

| Alternativa | Ventajas | Límites y consecuencias |
|---|---|---|
| **1. Solo rotular** (recomendada) | no cambia ninguna cifra ni conclusión; elimina la ambigüedad | los p paramétricos extremos siguen en la tabla |
| 2. Añadir a la Tabla 14 una columna con el p por permutación corregido por Holm | una sola inferencia robusta y corregida | exige decidir la familia de la corrección (31 términos del modelo completo o 15 del reducido) y recalcular; añade una cifra nueva (no verificada por un tercero) |
| 3. Dejar en la Tabla 14 solo los η² y quitar los p paramétricos | coherente con «se interpretan los tamaños del efecto» | pierde la referencia que cita B3.1 (p de Holm = 0,058) |

## 5. Limitación
No se probó ninguna prueba distinta de las dos que el proyecto ya ejecutó, y no se sustituyó una por otra. El orden de magnitud de cada p paramétrico depende de la normalidad de los residuos, que no se cumple.
