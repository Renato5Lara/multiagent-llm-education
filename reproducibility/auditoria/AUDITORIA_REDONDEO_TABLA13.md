# Auditoría del redondeo de la Tabla 13 (OE3, campaña N3)

Versión del informe: D2.9.7 (sha256 `a6bb2934de7fd512…`). Los valores sin redondear **se recuperaron de los archivos fuente reales** (no se tomaron del informe anterior).

## 1. Fuente y fórmulas
- Fuente: `oe_n3_2026-10-06/runs_oe3.csv` (sha256 `ca97879bfcefd0df…`; 240 corridas = 48 condiciones × 5 lotes), que a su vez se **recalcula** desde las 24 000 observaciones de `run/raw_observations.csv` con `adaptation_swarm.oe.factorial.aggregate_runs` (diferencia máxima 1,4·10⁻¹⁴; ver `outputs/tables/cadena_peticiones_a_corridas.csv`, fila N3).
- T_conv: **media geométrica** por nivel, `exp(media(ln t_conv_ms))`. `k_stop`, brecha y mensajes: media aritmética por nivel (n = 120 por nivel, o 80 por nivel del mecanismo). η² parcial y p: ANOVA factorial 2×2×2×2×3 tipo III con inferencia por permutación (Freedman–Lane, 1 000 permutaciones; determinista: dos ejecuciones dan resultados idénticos), `adaptation_swarm.oe.factorial.factorial_anova(..., "t_conv_ms", log=True)`.

## 2. Cadena de redondeo observada
1. Análisis del proyecto (`anova_oe3.md`, sha256 `45b80010bcb83f31…`): escribe **con más decimales que el informe**: T_conv a 2 decimales (`pso = 76.45`), `k_stop` a 3 (`True = 1.505`), η² a 3 (`0.495`).
2. `RESULTADO_OE3.md` (sha256 `15e228062f7892cd…`, transcripción del propio proyecto): vuelve a redondear a la precisión del cuadro («1,51», «76,5», «η² = 0,50»).
3. Informe D2.9.7: copia esos valores (Tabla 13 y párrafos de §6.5.4 y §6.5.5).

Política de redondeo del resto del informe (comprobada en las otras 36 cifras de la tabla y en 1 000+ cifras más): **redondeo directo del valor sin redondear a la precisión del cuadro, mitad hacia arriba**. Las tres cifras afectadas no la siguen.

## 3. Resultado por cifra
| id | Cifra | Informe | Valor sin redondear (recalculado) | Intermedio (análisis) | Redondeo directo = valor correcto | Diagnóstico |
|---|---|---|---|---|---|---|
| C13-1 | η² parcial de la heurística de arranque (T_conv) | 0,50 | 0,4949463340601963 | 0,495 | **0,49** | doble redondeo |
| C13-2 | `k_stop` con heurística (120 corridas) | 1,51 | 1,5046666666666666 | 1,505 | **1,50** | doble redondeo |
| C13-4 | T_conv (media geométrica) con PSO | 76,5 | 76,4488485627661 | 76,45 | **76,4** | doble redondeo |

En los tres casos el valor del informe se obtiene **y solo se obtiene** redondeando primero al intermedio y luego a la precisión del cuadro (comprobado por `compare()`, que exige esa demostración: campos `explicacion`, `valor_sin_redondear` y `valor_intermedio` de `outputs/verification_report.json`). No es una discrepancia de cálculo, de datos ni metodológica; es un **error de transcripción de 1 unidad del último decimal** que no altera ninguna conclusión (ni significación, ni signo, ni orden de los niveles).

## 4. Apariciones del indicador en el documento (búsqueda en prosa **y** tablas, incluidos resumen, abstract, conclusiones y anexos)
| Cambio | Ubicación | Texto afectado |
|---|---|---|
| C13-1 | Tabla 13 (§6.5.3) | «69,4 / 74,1 (p = 0,001; η² = 0,50)» |
| C13-2 | Tabla 13 | «1,51 / 1,91» |
| C13-3 | §6.5.4, párrafo sobre roles | «la heurística de arranque redujo las iteraciones (1,51 frente a 1,91)» |
| C13-4 | Tabla 13 | «76,5 / 76,3 / 63,3 (p = 0,001)» |
| C13-5 | §6.5.5, párrafo del análisis estadístico | «mecanismo PSO 76,5, social 76,3» |
No hay apariciones en resumen, abstract, conclusiones ni anexos. Otras cadenas «1,51» del documento son **otro indicador** (razón de throughput 1,13 a 1,51 frente a bruteforce y un límite de IC) y **no** se modifican. El «0,495» de §6.5.5 (η² con 3 decimales) es correcto.

## 5. ¿Hay más cifras con el mismo problema?
El verificador compara **todas** las cifras recalculables con la regla anterior y clasifica cualquier diferencia de una unidad que no sea doble redondeo como `DIFERENCIA_SIN_EXPLICAR`. Resultado: **0 más** entre las 1 011 comprobaciones; solo estas 3. Quedan sin comprobar numéricamente las celdas «sin efecto» de la Tabla 13 y las cifras de las tablas que no están cubiertas (ver `CONCILIACION_TESIS_DATOS.csv`).

## 6. Estado de la corrección
Registrada en `REGISTRO_CAMBIOS_TESIS.csv`. Se generó una **copia** corregida del DOCX (no publicada; ver `INFORME_CORRECCIONES_TESIS.md`) en la que solo cambian esos 5 textos; el original queda intacto. Con las tablas de esa copia, el verificador da 0 diferencias explicables (1 005 coincidencias, 6 no reproducibles).
