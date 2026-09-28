# Nota de pre-análisis — corrida oficial K = 10

**Proyecto:** UPAO-MAS-EDU · **Fecha de redacción:** 2026-09-27 · **Naturaleza:** documento nuevo e independiente. No modifica el pre-registro, sus addenda, el código, el dataset, la biblioteca, los resultados ni ningún documento de decisión.

## 0. Momento y alcance de esta nota (declaración de transparencia)

- **El procedimiento estadístico ya estaba pre-registrado antes de la corrida.** Está en el bloque `inference` de `preregistration_k10.json` (sha256 `9e8cd236…`), sellado en `5d7d12c`. Esta nota **no crea** el procedimiento: lo **consolida por escrito** y fija cómo se leerá el resultado.
- **La nota se redacta después** de que los resultados K = 10 se archivaran en `3088e69` (27/09/2026, 23:22 −05:00), **pero antes de que esta sesión observe cualquier valor numérico**.
  - Al redactarla no se abrió ningún `replica_*.json`, `plan.json` ni `manifest.json` de `official_runs/`.
  - No se calculó F1 ni ningún estadístico.
  - Solo se leyeron los metadatos de los commits y los archivos del pre-registro.
- **Límite:** esta nota no puede certificar que nadie haya observado los valores fuera de esta sesión. El commit `3088e69` declara que solo archiva la integridad técnica, sin F1, estadísticos ni conclusiones.

## 1. Identificación del experimento

| Elemento | Valor |
|---|---|
| Commit de sellado de la especificación | `5d7d12c9776a62d1234afb71acb505cd84cb5872` |
| Commit de registro técnico de la regla (HEAD de la corrida) | `5a1fe3b2fcfa34d5a3a920a01a6b1a30fc7d79a5` |
| Commit de resultados | `3088e6912885376baba2de30a8940fa0c3453e20` (`backend/official_runs/k10_official_2026-09-27/`) |
| Ejecución | 2026-09-27, 22:59:44–22:59:58 (−05:00), según el mensaje del commit |
| K | 10 réplicas (`replica_00` … `replica_09`) |
| Perfiles por réplica | 100 |
| `master_seed` | 26092601 (10 semillas de lote derivadas; la semilla histórica 20260923 está excluida) |
| Regla oficial | `gold-v2-cand-A+incl-ge1+samples+panel-arq-ac1-maj-tie0-v2` |
| Huellas | gold `1f917a7a…`; protocolo del panel `a83f8556…` |
| Dataset | `profiles-v1.jsonl`, sha256 `005b5a82ae85b4e83e1b9a931578fd60e9c6789a6e407928fdba6674fc1ccd15` |
| Biblioteca | `lib-v10-5dd83cd4`, manifiesto sha256 `89716455a14c2674a3a6a93bf1609be2c0cf83ed62ae654b2832b7038543a0ab` |
| Entorno | Python 3.12.14, numpy 2.5.3, scipy 1.18.1 (según el mensaje del commit de resultados) |

Ninguno de estos elementos se modifica.

## 2. F1_adapt

| Paso | Definición | Fuente |
|---|---|---|
| Gold | `gold-v2-cand-A`: Visual {diagram}, Logical {code}, Explanatory {text}, Balanced {code, diagram, text, audio}; cuatro modalidades; solo depende del arquetipo | P2 (26/09) |
| Predicción | `incl-ge1`: $P_i = \{m : e_m \ge 1\}$ sobre el `g_best` decodificado | P1 (26/09) |
| F1 por caso | Dice: $F1_i = 2\lvert G_i \cap P_i\rvert / (\lvert G_i\rvert + \lvert P_i\rvert)$; si $P_i = \varnothing$, $F1_i = 0$ | P1-bis, P3 |
| F1 por réplica | $F1_{adapt}(r)$ = media de los 100 $F1_i$ de la réplica *r* (`samples`) | P3 |
| Resumen entre réplicas | Media, DE e IC95 de los 10 valores $F1_{adapt}(r)$ | K |
| IC95 | t de Student de una muestra, gl = 9 | R1 |
| Criterio del IC | **Límite inferior del IC95 ≥ 0.85** | K, R3 |

## 3. Inferencia por perfil

| Paso | Definición | Fuente |
|---|---|---|
| Unidad | El **perfil** | R2 |
| Agregación | Cada perfil tiene un $F1$ por réplica; sus 10 valores se promedian: $m_j$, con j = 1…100 | R2 |
| Independencia | Los 1 000 valores caso × réplica **no** se tratan como independientes | R2 |
| Normalidad | Shapiro-Wilk sobre los 100 $m_j$, α = 0.05 | R2 |
| Prueba | Si hay normalidad (p de Shapiro > 0.05): t de una muestra contra 0.85. Si no: Wilcoxon de rangos con signo contra 0.85 | R2 |
| Dirección | **Unilateral**: H0: μ ≤ 0.85; H1: μ > 0.85 (`alternative = "greater"`) | Consulta 4 |
| Prueba superada | **p < 0.05 y media muestral de los $m_j$ > 0.85** | Consulta 4 (`DEC-F1-TEST`) |
| Muestra constante | Si los 100 $m_j$ son iguales, la prueba no se calcula: **INDETERMINADO** | Implementación sellada |

**Sobre la dirección del contraste.**
- `greater` **no** es solo una decisión del tesista. El asesor la fijó en su respuesta a la Consulta 4 del 26/09: «Unilateral. H0: μ <= 0.85 / H1: μ > 0.85 / Criterio: p < 0.05 Y media muestral > 0.85» (`TRANSCRIPCION-RESPUESTAS-ASESOR-2026-09-26.md` §4).
- Sigue la reserva de siempre: la respuesta se conoce por el texto del tesista y el original está por anexar.
- En cualquier caso, la dirección **no se cambia**: es la del pre-registro vigente.

## 4. Diferencia entre el IC y la prueba inferencial

| Nivel | Observaciones | n | Qué produce |
|---|---|---|---|
| A. IC95 | $F1_{adapt}(r)$, uno por réplica | 10 | Límite inferior del IC95 para el criterio del IC |
| B. Prueba estadística | $m_j$, uno por perfil (media de 10 réplicas) | 100 | Shapiro-Wilk y después t o Wilcoxon unilateral |

No es una contradicción: son dos procedimientos con **unidades distintas** (R1 y R2), y se reportan por separado.

**Criterio de RNF-03** (R3, Consulta 5, `DEC-RNF03`): **límite inferior del IC95 ≥ 0.85 Y prueba superada** (§3). Cualquier otra combinación implica que no se cumple. Si la prueba es INDETERMINADO, RNF-03 queda INDETERMINADO.

### 4.1 Discrepancia conocida entre la regla aprobada y el código sellado

- **La regla aprobada** (Consulta 4) define «prueba superada» como **p < 0.05 Y media muestral > 0.85**.
- **El código sellado no calcula la segunda condición.** `inference.profile_level_test` calcula `statistical_pass = (p < alpha)` sin comparar la media, y `combined_criterion` combina ese valor con el criterio del IC. La media muestral sí se reporta, en el campo `mean` del resultado.
- **Cuándo puede importar:**
  - En la rama t, un p < 0.05 unilateral implica t > 0, es decir, media > 0.85, así que las dos condiciones coinciden.
  - En la rama Wilcoxon, el contraste se refiere a la localización de las diferencias. Es posible, aunque infrecuente, que p < 0.05 y la media ≤ 0.85.
- **Procedimiento fijado antes de ver los resultados** (sin modificar el código sellado):
  1. Se reporta la salida del código tal cual (`statistical_pass`, `verdict`).
  2. Se verifica y reporta por separado la condición «media de los $m_j$ > 0.85», tomada del campo `mean` de la misma salida.
  3. Para declarar RNF-03 se aplica la regla aprobada: la prueba se considera superada solo si **p < 0.05 Y media > 0.85**. Si el código y la regla discrepan, se reportan **los dos valores** y se declara según la regla aprobada, dejando constancia de la discrepancia.

*Este paso aplica la decisión del asesor ya registrada; no es una regla nueva. Aun así, conviene que el tesista lo confirme antes de ejecutar el análisis.*

## 5. RNF-02 / convergencia

- La salida del análisis incluye, por caso y por réplica, `k_stop`, `stop_reason`, la proporción de convergencia (CR, definida en DEC-10 como la proporción de ciclos con `stop_reason = epsilon`) y estadísticas descriptivas de su variabilidad entre réplicas (`convergence_variability`).
- **El procedimiento vigente no codifica un veredicto completo para RNF-02.** No hay ninguna regla que diga:
  - si `T_conv ≤ 15` se evalúa sobre la media, el máximo o cada réplica;
  - cómo se agrega `CR ≥ 98 %` sobre K = 10.
- **Observación documental:** con la regla de parada (`k_max = 15`), `k_stop ≤ 15` se cumple por construcción (la «tautología» señalada en DEC-10).
- **Por tanto:** la convergencia se reporta **solo de forma descriptiva**. **No** se declarará RNF-02 cumplido ni incumplido hasta que exista una regla metodológica formal, y esa regla no se fijará mirando estos resultados.

## 6. RNF-01, RNF-04 y RNF-05

K = 10 (`core_replay`) **no** mide la latencia (RNF-01), el throughput (RNF-04) ni el SUS (RNF-05). Esas métricas requieren, respectivamente, la pila completa en el entorno cloud de 8 vCPU / 32 GB (R4) y la evaluación humana. No se infieren de K = 10.

## 7. Hipótesis general

La hipótesis general es **conjuntiva** (D6, Consulta 5):

$$\text{RNF-03} \;\wedge\; L_{resp} < 2.0\,\text{s} \;\wedge\; SUS > 75$$

- K = 10 permite evaluar **solo el componente F1** (RNF-03).
- **No** permite confirmar la hipótesis general, que depende también de la latencia y del SUS, todavía pendientes.
- Esta nota no emite ningún veredicto.

## 8. Panel humano

- El gold oficial está sujeto a validación por el panel, según PX1–PX7: AC1 de Gwet > 0.70, acuerdo crudo ≥ 85 %, más del 50 % de aprobación en cada arquetipo, empate = no aprobado. La implementación de AC1 está certificada con R 4.4.1 e irrCAC 1.4 (PX8; `addendum_presealing_2026-09-27.json`).
- **El panel no se ha ejecutado.**
- Si el panel invalida la regla, corresponde una **nueva `rule_version`** y la repetición de lo que corresponda (PX11).
- En ese caso, los resultados de K = 10 **no se reinterpretan retrospectivamente** para adaptarlos a la regla posterior: quedan como resultados de la regla con la que se ejecutaron.
- Esta nota no prepara ni convoca participantes.

## 9. Control contra HARKing y *p-hacking*

Durante el análisis:
- no se cambian la regla gold, la regla de inclusión, la agregación, la dirección del contraste, el método del IC, la unidad inferencial ni los umbrales (0.85, α = 0.05);
- no se eliminan perfiles, casos ni réplicas;
- no se cambian semillas;
- no se elige la prueba mirando los resultados: la elección entre t y Wilcoxon la determina **solo** Shapiro-Wilk, como está pre-registrado;
- no se añaden métricas ni subgrupos como criterio. El F1 por modalidad, por arquetipo y las matrices One-vs-Rest son **solo descriptivos** (P3).

## 10. Fuente computacional del análisis

- El análisis oficial usa exclusivamente `adaptation_swarm.analysis.replica_evaluation.evaluate(<official_runs/k10_official_2026-09-27>, official=True)`, que exige el manifiesto oficial y la regla aprobada, y las funciones de `adaptation_swarm.analysis.inference` que ya contiene: `student_t_ci`, `aggregate_by_profile`, `profile_level_test`, `combined_criterion` y `convergence_variability`.
- **No** se crea ninguna fórmula paralela. La única comprobación adicional es la lectura del campo `mean` descrita en el §4.1, que no recalcula nada.
- El análisis se ejecuta en el entorno declarado (Python 3.12.14) sobre los resultados congelados, **sin modificarlos**. Su salida se archiva aparte, con hash.

## 11. Archivos excluidos del análisis oficial

`corrida-poc-1`, `corrida-poc-2`, la sensibilidad histórica, `gold-v1`, los análisis exploratorios de las reglas candidatas gold-v2, los pilotos, los paquetes de evidencia históricos (`evidence_package_2026-09-23/24/24-final`), los benchmarks previos y las pruebas de carga previas.

## 12. Fuentes

| Fuente | Estado |
|---|---|
| `MASTER-SPEC-2026-09-23.md` | Encontrada |
| `DECISION-CLOSURE-2026-09-23.md` (incluida la §15) | Encontrada |
| `ADDENDUM-DECISIONES-ASESOR-2026-09-25.md` | Encontrada |
| `ADDENDUM-DECISIONES-ASESOR-RULE-VERSION-2026-09-26.md` | Encontrada |
| `TRANSCRIPCION-RESPUESTAS-ASESOR-RULE-VERSION-2026-09-26.md` | Encontrada |
| `TRANSCRIPCION-RESPUESTAS-ASESOR-2026-09-26.md` (R1–R6 y Consultas 1–5) | Encontrada; es la fuente de la dirección y del criterio de la prueba |
| `preregistration_k10.json` y addenda (`python312`, `presealing`, `rule_registration`) | Encontrados (metadatos) |
| Commits `5d7d12c`, `5a1fe3b` y `3088e69` | Encontrados (metadatos; no se abrieron los resultados) |
| **Respuesta del asesor sobre el orden sellado/registro (27/09, «lectura 1 / opción A»)** | **No encontrada en los documentos de tesis.** Solo aparece en `addendum_rule_registration_2026-09-27.json`, marcada como «informado por el tesista… NO verificable desde el repositorio». Falta transcribirla |
| Originales de todas las respuestas del asesor | No disponibles (reserva vigente) |

---

**El procedimiento estadístico queda fijado antes de observar los resultados numéricos de K=10. La ejecución posterior se limitará a aplicar las reglas aquí documentadas sobre los resultados oficiales congelados, sin modificar retrospectivamente las decisiones metodológicas.**
