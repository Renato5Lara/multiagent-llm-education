# Auditoría: tres diferencias de una unidad en la Tabla 13

Las tres cifras que el verificador clasifica como `DIFERENCIA_EXPLICABLE` (N3, `runs_oe3.csv`, 240 corridas). Valores sin redondear tomados directamente de los datos:

| Cifra | Informe | Sin redondear (recalculado) | Resultado del propio análisis (`anova_oe3.md` / `.json`) | Redondeo correcto a la precisión del informe |
|---|---|---|---|---|
| η² parcial de la heurística de arranque (T_conv) | 0,50 | 0,494946… | 0,495 (`partial_eta_sq` = 0,494946…) | **0,49** |
| `k_stop` con heurística de arranque | 1,51 | 1,504667… (media de 120 corridas) | 1,505 | **1,50** |
| T_conv de `pso` (media geométrica) | 76,5 | 76,448849… | 76,45 | **76,4** |

## Regla y fórmulas
- T_conv: media **geométrica** por nivel, exp(media(ln x)) sobre las 240 corridas (120 o 80 por nivel); `k_stop` y las demás respuestas: media aritmética por nivel; η² parcial y p: ANOVA factorial tipo III con permutación (Freedman–Lane), `adaptation_swarm.oe.factorial`, determinista entre ejecuciones.
- El análisis del proyecto **ya redondea a 3 decimales** al escribir `anova_oe3.md` (1,505; 76,45; 0,495). El texto `RESULTADO_OE3.md` y el cuadro del informe se transcribieron desde esas cifras ya redondeadas y se redondearon **otra vez** a la precisión del cuadro con la regla «mitad hacia arriba»: 1,505→1,51; 76,45→76,5; 0,495→0,50.

## Conclusión
No es una discrepancia de cálculo ni de datos, ni una diferencia metodológica: el cálculo del proyecto reproduce los valores. Es un **error de transcripción por doble redondeo** de 1 unidad del último decimal en tres cifras (las otras 36 de la tabla coinciden con el redondeo directo). `reproduce_results.py` ahora **demuestra** el doble redondeo en cada caso (campos `explicacion`, `valor_sin_redondear`, `valor_intermedio`) y clasifica como `DIFERENCIA_SIN_EXPLICAR` (y como discrepancia) cualquier diferencia de una unidad que no se explique así.

## Qué NO se hizo
No se modificó el informe ni el código para forzar coincidencias. Si el autor lo desea, el redondeo correcto a la precisión actual sería 0,49 · 1,50 · 76,4; ninguna conclusión de la tesis depende de esa diferencia (ni el signo, ni la significación, ni el orden de los niveles).
