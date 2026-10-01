# R31 — Análisis estadístico de Corrida 2 (dataset real, PostgreSQL)

- Fuente: `experiment_cmg_results` WHERE `run_label = 'corrida_2'` (N=64, 32 Concepts × 2 condiciones).
- Piloto 1 (`run_label='pilot_1'`, N=64) **no** entra en la inferencia — sección independiente al final.
- Artefactos: `corrida2_analysis_v1.csv`, `corrida2_statistics_v1.json`, `corrida2_paired_bootstrap_v1.json`.
- Reproducibilidad: análisis ejecutado dos veces de forma independiente contra el mismo export SQL; salida JSON byte-idéntica (`diff` exit 0). Semilla de bootstrap fija: `20260922`.

## A. Integridad del dataset

Auditoría SQL directa sobre `run_label='corrida_2'`:

| Verificación | Resultado |
|---|---|
| N total | 64 |
| Concepts distintos | 32 |
| Experimental | 32 |
| Control | 32 |
| Duplicados Concept×condition | 0 |
| Pares incompletos (≠1 exp + 1 ctl) | 0 |
| Pares con `learning_objective_id` distinto entre exp/ctl | 0 |
| NULL en cmg/d1/d2/d3/configuration/execution_valid | 0 |

## B. Estadística descriptiva (Tabla 1 — distribución de D1 por condición)

| Condición | n | Nivel 0 | Nivel 1 | Nivel 2 | Mediana | Rango | Media (aux.) | DE (aux.) |
|---|---|---|---|---|---|---|---|---|
| Experimental | 32 | 0 (0%) | 2 (6.25%) | 30 (93.75%) | 2.0 | [1, 2] | 1.9375 | 0.246 |
| Control | 32 | 0 (0%) | 1 (3.125%) | 31 (96.875%) | 2.0 | [1, 2] | 1.96875 | 0.177 |

D1 es ordinal discreto {0,1,2}; media/DE se reportan solo como descriptivos auxiliares, no como base de una inferencia paramétrica.

## C. Pares Concept × D1 experimental/control (Tabla 2)

32 pares completos. Tabla completa en `corrida2_analysis_v1.csv` (columnas: `concept_id`, `learning_objective_id`, `profile`, `condition_experimental` [configuración obtenida en el brazo experimental], `configuration_control`, `d1_experimental`, `d1_control`, `difference_d1`).

Resumen: 31/32 pares con `d1_experimental == d1_control` (ambos en nivel 2, salvo 1 par en nivel 1/1). 1/32 par con `d1_experimental=1, d1_control=2` (concepto `4ec2e7de-2133-48b2-9c9c-567f9f82d3f9`, perfil E2).

## D. Distribución de diferencias (Tabla 3)

| Diferencia (exp − ctl) | Frecuencia | Proporción |
|---|---|---|
| −2 | 0 | 0% |
| −1 | 1 | 3.125% |
| 0 | 31 | 96.875% |
| +1 | 0 | 0% |
| +2 | 0 | 0% |

Mediana de las diferencias: **0.0**.

## E. Prueba principal — Wilcoxon signed-rank pareado (Tabla 4)

Justificación: D1 es ordinal, diseño pareado por Concept, n=32 pares.

| Elemento | Valor |
|---|---|
| n pares totales | 32 |
| n diferencias = 0 | 31 |
| n diferencias ≠ 0 | 1 |
| Manejo de ceros | `scipy.stats.wilcoxon(zero_method='wilcox')` — descarta los pares con diferencia 0 antes de rankear (comportamiento por defecto de scipy) |
| Estadístico | 0.0 |
| Método | `auto` (scipy elige exacto/asintótico según n y empates de rango tras remover ceros) |
| p-value | **0.3173** |

**No se oculta la limitación exigida por R31 §6:** con solo 1 de 32 pares presentando una diferencia distinta de cero, el test de Wilcoxon queda con una sola observación efectiva. En estas condiciones el resultado es estadísticamente casi vacío de información — el p-value no debe leerse como evidencia sustantiva en ningún sentido (ni a favor ni en contra de una diferencia), sino como reflejo directo de que 31/32 pares fueron idénticos en D1.

## F. Análisis de sensibilidad — Sign test pareado (Tabla 5)

| Elemento | Valor |
|---|---|
| n positivos (exp > ctl) | 0 |
| n negativos (exp < ctl) | 1 |
| n empates (diferencia 0) | 31 |
| n efectivo (usado en el test) | 1 |
| Método | `scipy.stats.binomtest(k=max(n_pos,n_neg), n=n_efectivo, p=0.5, alternative='two-sided')` |
| p-value | **1.0** |

**Comparación de robustez:** Wilcoxon (p=0.3173) y sign test (p=1.0) llegan a la misma conclusión cualitativa — ninguno detecta una diferencia estadísticamente significativa — pero difieren en el p-value exacto porque Wilcoxon pondera la magnitud del único cambio observado (rango) mientras el sign test solo cuenta signos. Con n_efectivo=1 en ambos casos, esta discrepancia numérica es esperable y no representa una contradicción sustantiva: ambas pruebas coinciden en que la Corrida 2, tal como fue ejecutada, no aporta evidencia estadística suficiente para detectar una diferencia bajo ninguna de las dos pruebas.

## G. Tamaño del efecto (Tabla 6)

| Elemento | Valor |
|---|---|
| Definición | r = Z / √N (Rosenthal), Z de la aproximación normal de Wilcoxon, N = pares con diferencia ≠ 0 |
| N usado | 1 |
| Z aproximado | −1.0 |
| r | **−1.0** |

Con N=1 este "tamaño de efecto" es un artefacto aritmético de tener una sola observación no-nula, no una estimación interpretable de magnitud poblacional. Se reporta por transparencia metodológica (R31 §7 exige reportar el valor y su método de cálculo), no como evidencia de un efecto grande.

## H. Intervalos / incertidumbre — bootstrap pareado (Tabla 6, continuación)

Bootstrap pareado por Concept, resampleo con reemplazo de las 32 diferencias, semilla fija `20260922`, 10 000 replicaciones (`corrida2_paired_bootstrap_v1.json`):

| Estadístico | Valor observado | IC 95% (bootstrap) |
|---|---|---|
| Mediana de la diferencia | 0.0 | [0.0, 0.0] |
| Media de la diferencia | −0.03125 | [−0.09375, 0.0] |

El bootstrap no reemplaza la prueba principal (Wilcoxon); se reporta como complemento de incertidumbre, según R31 §8.

## I. D2/D3 como filtros de validez (Tabla 7)

| Dimensión | Experimental | Control |
|---|---|---|
| D2 (`execution_valid`) | 32/32 válidos | 32/32 válidos |
| D3 (`passed`, coherencia intermodal) | 32/32 válidos | 32/32 válidos |

Ambos son constantes en esta corrida (100% válidos en ambas condiciones): funcionan como criterios de filtro/validez técnica, no aportan variación inferencial. No se combinan entre sí ni con D1 en un índice de calidad.

## J. E1/E2 — descriptivo

Perfiles de evidencia sintética dentro de la condición experimental (no tratados como segunda variable independiente de la tesis):

| Perfil | n | Nivel 0 | Nivel 1 | Nivel 2 | Mediana |
|---|---|---|---|---|---|
| E1 (errors=2, p=0.2, config esperada mixta/fundamentos) | 16 | 0 | 0 | 16 | 2.0 |
| E2 (errors=10, p=1.0, config esperada visual/fundamentos) | 16 | 0 | 2 | 14 | 2.0 |

Las 2 observaciones de D1=1 en la condición experimental corresponden ambas al perfil E2. No se realiza inferencia causal E1 vs. E2 (no estaba pre-registrada).

## K. Comprobación de paridad

Verificado por trazabilidad real disponible en BD (no inferido):

- Mismo `concept_id` y mismo `learning_objective_id` dentro de cada par: 32/32.
- Configuración experimental observada: `{mixta/fundamentos, visual/fundamentos}` (varía según perfil E1/E2, tal como exige el diseño — la VI sí varió).
- Configuración control observada: `{mixta/aplicacion}` — constante, como exige el diseño (`configuration_source=fixed_control` en las 32 filas).
- Mismo `CMGGenerationService`/evaluador/`SandboxRunner`: ambas condiciones se generaron y evaluaron en la misma corrida del mismo runner (`experimento_cmg_runner.py`), sin bifurcación de código entre brazos salvo la determinación de `configuration`.
- Única diferencia experimental prevista: `configuration_source` (`multiagent_runtime` vs `fixed_control`) — confirmado, sin otras diferencias detectables en los campos persistidos.

## L. Reproducibilidad

Análisis re-ejecutado desde cero (mismo export SQL, script independiente invocado dos veces) con semilla de bootstrap fija (`20260922`, 10 000 replicaciones). Comparación byte a byte de la salida JSON completa (`diff` sobre las dos corridas): **idéntica** — mismos N, mismas tablas, mismo estadístico y p-value de Wilcoxon, mismo p-value del sign test, mismo tamaño de efecto, mismo intervalo bootstrap. Reproducibilidad verificada.

## M. Limitaciones

1. **Escala extremadamente discreta y con techo (ceiling effect).** D1 quedó en nivel 2 en 61/64 observaciones de Corrida 2 (95.3%). Con tan poca variabilidad, cualquier prueba estadística —paramétrica u ordinal— tiene poca capacidad para detectar diferencias reales si las hubiera; el resultado aquí reportado (p=0.3173 Wilcoxon, p=1.0 sign test) refleja principalmente la falta de variación observada, no necesariamente ausencia de efecto poblacional.
2. Con solo 1 par de 32 mostrando una diferencia no nula, el tamaño de efecto (r=−1.0) y el estadístico de Wilcoxon dependen enteramente de esa única observación — no son estimaciones estables.
3. D1 mide adherencia curricular léxica (cobertura de términos del Concept/LearningObjective), no calidad pedagógica ni aprendizaje — la interpretación de cualquier diferencia debe limitarse a ese constructo (limitación ya aceptada en R25).
4. D2/D3 no aportaron variación en esta corrida (100% válidos en ambas condiciones) — no permiten, por sí solos, distinguir las condiciones.
5. N=32 pares es el diseño cerrado de esta corrida; no se ejecutó una corrida adicional para "compensar" el resultado (prohibido explícitamente por R31 §13).

## N. Relación con la hipótesis

Hipótesis cerrada: *"La calidad del contenido multimodal generado difiere entre la condición en que la configuración de generación es determinada por el mecanismo multiagente y la condición de comparación con configuración fija."*

- **Dirección:** en el único par con diferencia no nula, D1 fue menor en la condición experimental que en control (−1). En el resto (31/32 pares) no hubo diferencia detectada en D1.
- **Magnitud:** mínima y basada en una sola observación no nula sobre 32 pares.
- **Incertidumbre:** IC 95% bootstrap de la diferencia mediana = [0.0, 0.0]; de la diferencia media = [−0.094, 0.0] — ambos incluyen 0.
- **Resultado de las pruebas:** ni Wilcoxon (p=0.3173) ni el sign test (p=1.0) detectan una diferencia estadísticamente significativa bajo la prueba utilizada.

No corresponde declarar la hipótesis aceptada ni rechazada a partir de este resultado exclusivamente: **la Corrida 2, con la operacionalización actual de D1 (0/1/2, con techo pronunciado en nivel 2), no proporciona evidencia estadística suficiente para detectar una diferencia entre condiciones bajo las pruebas utilizadas.** No se extrapola este resultado a aprendizaje, rendimiento académico o experiencia del estudiante — D1/D2/D3 no miden ninguna de esas variables.

## O. Piloto 1 (contexto, no usado en inferencia)

- 64 observaciones (`run_label='pilot_1'`), 32 experimental + 32 control.
- Función: validación técnica del pipeline (generación → evaluación → persistencia), previa a la implementación de `run_label` (R28/R29).
- Separación garantizada por `run_label` a nivel de columna con `CheckConstraint`, verificada en R29 y re-confirmada en la auditoría §A de este documento (Corrida 2 se extrajo exclusivamente con `WHERE run_label='corrida_2'`).
- No se recalcula la hipótesis combinando Piloto 1 con Corrida 2.

## Estado final: **GREEN**

El dataset de Corrida 2 es íntegro (32 pares completos, sin duplicados, sin NULL, sin contaminación con Piloto 1) y el análisis es reproducible byte a byte. Se clasifica GREEN pese al resultado no significativo y pese al efecto techo en D1, porque ambos son propiedades reales de los datos, correctamente medidas y reportadas — no defectos del análisis. No se modificó ningún dato para forzar este estado.
