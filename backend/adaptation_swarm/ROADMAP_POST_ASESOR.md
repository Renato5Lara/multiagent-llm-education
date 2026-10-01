# Roadmap post-asesor — fases F0–F8 (2026-09-25)

> **Qué pregunta responde (y por qué es un documento nuevo):** *«¿qué hay que hacer, en qué orden, con qué archivos, dependencias y criterios de cierre, para pasar de la PoC técnica cerrada con limitaciones a la validación metodológica que exige la respuesta del asesor del 25/09/2026?»*
> `CIERRE_POC.md` dice **qué se cumple hoy**; este documento dice **qué falta**. Fuente de las decisiones: `Docuemento de tesis/ADDENDUM-DECISIONES-ASESOR-2026-09-25.md` (resumen comunicado por el tesista; **texto literal del asesor por anexar**).
>
> **Regla de lectura:** este roadmap **no declara resultados**. `F1_adapt = 0.8031` queda como **resultado histórico** de la definición anterior (`gold-v1`, etiqueta única, audio fuera de la métrica) y **no se reutiliza como resultado final**. **La hipótesis H1 (conjuntiva) sigue sin confirmarse.**

## 0. Decisiones que este roadmap ejecuta

| ID | Decisión del asesor | Fase |
|---|---|---|
| D1 | `F1_adapt` = inclusión/exclusión multimodal 4×4 con audio obligatorio; nueva `rule_version` y nueva corrida | F1 |
| D2 | Se rechaza el desempate de Balanced hacia `code`; gold que represente las cuatro modalidades; nueva corrida sobre los 100 perfiles | F1 |
| D3 / D4 | Se ratifica excluir Recursividad (30 conceptos) / N = 20 incluye la partícula heurística | F0 |
| D5 | K = 10 réplicas con semillas independientes | F3 |
| D6 | Hipótesis oficial conjuntiva: `F1_adapt ≥ 0.85` ∧ `L_resp < 2.0 s` ∧ `SUS > 75` | F8 |
| D7 | Mismo panel (n ≥ 10) valida gold y SUS; κ ≥ 0.70; desacuerdo mayoritario ⇒ reportar, redefinir `rule_version` y repetir | F7 |
| D8 | SUS en versión española publicada y validada; el asesor valida el consentimiento; sin trámite institucional adicional | F7 |
| D9 | Git LFS para publicar el audio (contingencia: repositorio institucional), pendiente de verificar cuota, instalación y viabilidad | F6 |
| D10 | Respondida con la opción hardware cloud de 8 vCPU / 32 GB: no son definitivas las mediciones con 7.5 GiB; repetir en ese hardware | F5 |
| D11 | Shapiro-Wilk + prueba correspondiente sobre latencias por petición; unidad por caso para el F1; línea base fuerza bruta frente a PSO | F2, F4, F5 |

## 1. Datos que NO se modifican en ninguna fase

Corridas `corrida-poc-1/2` y sus auditorías (`experiments/results/adaptation_swarm_corrida-poc-*`), la sensibilidad, `gold-v1` (`gold/rubric.py`, `gold/f1.py`, `gold/dataset.py`, `datasets/synthetic_profiles/gold-v1.jsonl`), `profiles-v1` (salvo una decisión nueva y explícita sobre el dataset), el paquete `evidence_package_2026-09-24-final/`, la biblioteca sellada (`lib-v1…lib-v10`, sus manifiestos y sha256), `loadtest/results/` históricos y las plantillas `human_eval` (no se fabrican respuestas). **Todo resultado nuevo va a directorios nuevos**, con `run_label`/carpeta y hashes propios; los guardias de `isolated_env` lo imponen. Las pruebas `test_gold_v2::test_historical_modules_and_data_are_untouched` y `test_frozen_runs_preserved` fallan si algo de lo anterior cambia.

## 2. Estado del sprint acelerado (2026-09-25): qué ya está preparado y qué no

| Pieza | Estado | Archivos |
|---|---|---|
| Registro de decisiones (F0) | **hecho** (falta anexar el texto literal) | `ADDENDUM-DECISIONES-ASESOR-2026-09-25.md`, Anexo B de la consulta, avisos en `DECISION-CLOSURE`/`DECISION-REGISTER`, `CIERRE_POC.md` §8 |
| Métrica multietiqueta 4×4 con audio, reglas gold-v2 **candidatas PROVISIONALES**, guardia de aprobación | **implementado y probado**; **ninguna regla aprobada** | `gold/labels_v2.py`, `gold/rubric_v2.py`, `gold/f1_multilabel.py` |
| Informe comparativo de alternativas de Balanced e inclusión (exploratorio) | **implementado y probado**; resultados **PROVISIONALES** | `analysis/balanced_alternatives.py` |
| Ejecutor puro de K réplicas con semillas independientes | **implementado y probado**; **no se ejecutó ninguna corrida oficial** | `analysis/core_replay.py`, `analysis/replicas.py` |
| Línea base fuerza bruta frente a PSO | **implementada y probada**; solo hay mediciones locales **NO CONCLUYENTES** | `analysis/baseline_bruteforce.py` |
| Pruebas puras | 82 nuevas; suite «sin servicios» = **regresión pura sin Redis** (`pytest tests/adaptation_swarm -m "not integration"` con `--deselect` de `test_messages_bus.py` y `test_agents_library.py`, que **requieren un Redis en ejecución** y por eso **no se ejecutaron**; 40 pruebas): **325 pasan** | `tests/adaptation_swarm/test_gold_v2.py`, `test_replicas_executor.py`, `test_baseline_and_alternatives.py`, `test_sprint_modules_safeguards.py` |
| `gold-v2` como dataset, aprobación de la regla, inferencia, benchmark en hardware objetivo, Git LFS, panel humano | **no iniciados** | ver F1–F7 |

## 3. Ruta crítica y paralelismo

```
F0 ─▶ F1 (aprobar regla + gold-v2) ─┬─▶ F3 réplicas ─▶ F2 inferencia ─┐
                                    ├─▶ F4 línea base ────────────────┤
                                    └─▶ F7 panel (SOLO tras congelar F1)┼─▶ F8 resultados y conclusiones
F5 hardware 8 vCPU/32 GB  ──────────────────────────────────────────────┤
F6 Git LFS / audio        ──────────────────────────────────────────────┘
```
Orden crítico indicado por el tesista: **nuevo gold y métrica → réplicas → benchmark → panel humano.** F5 y F6 son independientes de F1 y pueden avanzar en paralelo. **El panel humano (F7) no se ejecuta antes de congelar la definición del gold**: un desacuerdo mayoritario obliga a repetir la corrida.

## 4. Decisiones humanas pendientes (bloquean fases concretas)

**Primer punto exacto que requiere confirmación humana: la aprobación de UNA `rule_version`** = (a) regla de **inclusión** (cuándo una modalidad cuenta como «incluida» dado `e_m ∈ {0,1,2}`; addendum **P1**), (b) **conjunto esperado** por arquetipo (**P2**) y (c) **agregación** que se denomina `F1_adapt` (**P3**). Sin ella no existe corrida oficial (el código lo impide: `APPROVED_RULE_VERSIONS` está vacío).

> **Riesgo de selección post-hoc (medido, exploratorio, PROVISIONAL).** Sobre las corridas históricas, el F1 varía entre **≈ 0.64 y ≈ 0.87 solo según cómo se defina «incluida» y el gold**; **una sola** de las 12 combinaciones v2 supera 0.85 (`gold-v2-cand-A+incl-top-tol0`, agregación por caso: 0.870), y ninguna lo hace con macro o micro. Como esos resultados ya se conocen, elegir la regla por su F1 sería post-hoc. Mitigación: la regla se aprueba **por criterio conceptual** (qué significa «incluida» cuando RF-05 exige las 4 modalidades siempre presentes), con su justificación escrita y fecha, **antes** de ejecutar las réplicas oficiales, y se evalúa sobre réplicas **nuevas** con semilla maestra pre-registrada.

| # | Pendiente | Bloquea |
|---|---|---|
| P1–P3 | Regla de inclusión, conjunto esperado por arquetipo y agregación de `F1_adapt` | F1, F2, F3, F7 |
| P4 | Qué es «desacuerdo mayoritario» y si κ ≥ 0.70 es global, por celda o ambos | F7 |
| P5 | Semilla maestra pre-registrada y versión de biblioteca de las réplicas | F3 |
| P6 | Hardware objetivo: el asesor respondió con la opción «hardware cloud de 8 vCPU y 32 GB» (comunicaciones previas: «cercano a»). Umbral operativo aquí (≥ 8 vCPU y ≥ 90 % de la RAM) y dónde se obtiene, por confirmar | F4, F5 |
| P7 | Referencia de la versión española publicada del SUS | F7 |
| P8 | Cuota, instalación y viabilidad de Git LFS (D9c); términos de OpenAI (D9d) y retención de versiones antiguas (D9e) si la opción Git LFS no los cubre | F6 |
| — | D9a–D9f (opción Git LFS) y D10a–D10c (opción cloud 8 vCPU / 32 GB) **respondidas**; sin especificar: pronunciamiento propio sobre D9a/D9d/D9e y aceptación definitiva de M1 y 4 workers (condicionada a la medición) | F5, F6 |

---

## F0 — Cierre documental de decisiones
- **Objetivo:** registrar D1–D11, marcar lo superado sin reescribir el historial y dejar el roadmap.
- **Archivos que cambian:** `ADDENDUM-DECISIONES-ASESOR-2026-09-25.md` (nuevo, fuera del repo); Anexo B de `CONSULTA-ASESOR-CIERRE-POC-2026-09-25.md`; **avisos** al inicio de `DECISION-CLOSURE` y `DECISION-REGISTER`; `CIERRE_POC.md` §8; este roadmap. Pendiente: anexar el texto literal del asesor.
- **Dependencias:** respuesta del asesor (recibida, resumida). **Riesgos:** el registro es un resumen, no una transcripción; «desacuerdo mayoritario» ambiguo (P4).
- **Datos que no se modifican:** todo lo de la §1. **Pruebas:** validación de tablas y citas de los documentos; `git diff` solo con avisos añadidos (0 líneas eliminadas en los documentos de autoridad).
- **Criterio de cierre:** texto literal anexado y contrastado con el registro; P1–P8 asignados a un responsable.
- **Fuera de alcance:** enmiendas sección por sección (B1–B10) de `MASTER-SPEC`/`DECISION-CLOSURE`: cambio documental separado cuando P1–P4 estén definidos.
- **Estimación:** hecho en este sprint (≈ 0.5 día); anexar el texto literal ≈ 1 hora.

## F1 — Nueva definición 4×4 y gold multimodal
- **Objetivo:** aprobar una `rule_version` y congelar `gold-v2`.
- **Archivos que cambian:** `gold/rubric_v2.py` (añadir la `rule_version` aprobada a `APPROVED_RULE_VERSIONS`, en una revisión con la decisión del asesor); **nuevo** `datasets/synthetic_profiles/gold-v2.jsonl` y su manifiesto con sha256 (generado por una herramienta nueva a partir de la regla, sin tocar `gold-v1`); ADR-0019: addendum de la nueva métrica; `CIERRE_POC.md`. Ya existen `gold/labels_v2.py`, `gold/f1_multilabel.py` y el informe de alternativas.
- **Dependencias:** P1–P3 (decisión humana). **Riesgos:** selección post-hoc (ver §4); el audio casi no aparece como énfasis principal (con `incl-top-tol0` su recall es 0.40 y el F1 por caso de Balanced 0.654), lo que el asesor debe conocer al definir «incluida»; los centroides (`centroids-v1`) dan al audio peso 0.10–0.25.
- **Datos que no se modifican:** `gold-v1` y sus módulos; corridas históricas. **Pruebas:** `test_gold_v2` (16, ya pasan) + pruebas nuevas del dataset `gold-v2` (sha256, 100 casos, Balanced = las 4 modalidades, independencia de `W`) y de la aprobación.
- **Criterio de cierre:** regla aprobada con justificación y fecha; `gold-v2.jsonl` con hash en el manifiesto; `require_approved` pasa solo para esa regla; tests verdes; ADR actualizado.
- **Fuera de alcance:** ejecutar corridas; recalcular el F1 histórico.
- **Estimación:** 0.5–1 día de implementación **después** de la aprobación; la aprobación depende del asesor (no estimable).

## F2 — Métrica F1 por caso e inferencia
- **Objetivo:** unidad por caso para el F1 (D11a) y contrastes Shapiro-Wilk + t/Wilcoxon (D11a, D11b).
- **Archivos que cambian:** **nuevo** `analysis/inference.py` (Shapiro-Wilk, t de una muestra o Wilcoxon según normalidad, IC95; sobre F1 por caso, y sobre latencias por petición); pruebas nuevas; `REPRODUCIBILITY.md`. Ya existe el F1 por caso (`MultilabelReport.per_case`, agregación `samples`).
- **Dependencias:** F1 (regla) para el F1; F3 (réplicas) para la inferencia oficial; JMeter `.jtl` históricos (12 archivos) solo para ensayar sobre latencias. **Riesgos:** los 100 casos comparten perfiles entre réplicas (pseudo-replicación); el F1 por caso es discreto y no normal (Wilcoxon); con miles de latencias Shapiro-Wilk siempre rechaza; las latencias de bucle cerrado están autocorrelacionadas y el criterio es un **P95** mientras el contraste de la asesoría compara una **media** (pedir al asesor qué estadístico se contrasta); **Locust no conserva latencias por petición**.
- **Datos que no se modifican:** `loadtest/results/` históricos (solo lectura). **Pruebas:** distribuciones sintéticas conocidas (normal ⇒ t, sesgada ⇒ Wilcoxon), n mínimo, casos degenerados.
- **Criterio de cierre:** protocolo inferencial pre-registrado (qué unidad, qué test, qué hipótesis nula) y probado; la aplicación oficial queda para F3/F5.
- **Fuera de alcance:** conclusiones sobre H1. **Estimación:** ≈ 1 día.

## F3 — Diez réplicas con semillas independientes
- **Objetivo:** K = 10 réplicas (D5) con la regla aprobada, sobre los 100 perfiles.
- **Archivos que cambian:** **nuevo directorio de resultados** (p. ej. `backend/experiments/replicas_<fecha>/`) con `plan.json`, `replica_00…09.json` y `manifest.json`; `CIERRE_POC.md`; paquete de evidencia nuevo (F8). Ya existen `analysis/core_replay.py` y `analysis/replicas.py`.
- **Dependencias:** F1 (regla aprobada) y P5 (semilla maestra y biblioteca pre-registradas). **Riesgos:** las réplicas del **núcleo** reproducen las etiquetas (el replay coincide con los 100 casos históricos) pero **no ejercen la pila completa** ni miden latencia; si el asesor exige la pila completa, se usaría `run_experiment` con Redis, PostgreSQL y audio (≈ 17 s por corrida según `elapsed_s`); las 10 réplicas comparten los mismos 100 perfiles (solo varía la semilla del PSO).
- **Datos que no se modifican:** `corrida-poc-1/2`, `profiles-v1`, biblioteca sellada. **Pruebas:** `test_replicas_executor` (12, ya pasan): semillas independientes, sin sobrescritura, determinismo, integridad, puerta de aprobación.
- **Criterio de cierre:** `manifest.json` con estado OFICIAL, semillas y sha256 de cada réplica; `verify` sin problemas; F1 por réplica con la agregación aprobada y su resumen.
- **Fuera de alcance:** latencia; SUS. **Estimación:** cómputo ≈ 2 s por 10 réplicas × 100 perfiles (medido, exploratorio); ≈ 3 min con la pila completa; con análisis ≈ 0.5 día.

## F4 — Línea base fuerza bruta frente a PSO
- **Objetivo:** comparar PSO y fuerza bruta con el mismo perfil, biblioteca y 𝓕: tiempo de búsqueda, solución y brecha (D11c).
- **Archivos que cambian:** resultados en directorio nuevo; `CIERRE_POC.md` (R08, R27). Ya existe `analysis/baseline_bruteforce.py`.
- **Dependencias:** ninguna para el código; la **afirmación** exige el hardware de F5. **Riesgos:** el ruido de tiempos; «cold» frente a «warm» (declarados); se mide **búsqueda en proceso, no `L_resp`**; en la máquina local (8 vCPU / 7.5 GiB) el resultado es **NO CONCLUYENTE** por diseño.
- **Datos que no se modifican:** biblioteca, corridas. **Pruebas:** `test_baseline_and_alternatives` (ya pasan): la fuerza bruta coincide con el óptimo histórico; el PSO nunca supera el óptimo; sin afirmación sin hardware/dataset/repeticiones válidos.
- **Criterio de cierre:** informe en el hardware objetivo con los 100 perfiles y ≥ 5 repeticiones, con `claim_allowed = true`.
- **Fuera de alcance:** afirmar reducción de latencia de extremo a extremo. **Estimación:** medición local exploratoria ≈ 3 s (5 perfiles × 3 repeticiones); en hardware objetivo ≈ minutos; el cuello es obtener el hardware (F5).

## F5 — Validación en hardware de 8 vCPU / 32 GB
- **Objetivo:** repetir latencia y throughput (RNF-01/04) en hardware cloud de 8 vCPU / 32 GB (D10a–D10c) y registrar latencias por petición (D11b).
- **Archivos que cambian:** `loadtest/locustfile.py` (registrar cada petición), `loadtest/README.md`, scripts de ejecución; **nuevos** `loadtest/results/<fecha>_<hw>/` (nunca sobre los históricos); `test_loadtest_structure.py` (extendido); `REPRODUCIBILITY.md`; `CIERRE_POC.md` (R20, R21, R25).
- **Dependencias:** P6 (umbral operativo del hardware objetivo); acceso al hardware (presupuesto de la asesoría: nodo cloud 8 vCPU / 32 GB); Redis, PostgreSQL y la biblioteca con audio en ese equipo; la aceptación definitiva de M1 y de 4 workers (D10a/D10b) queda condicionada a esta medición. **Riesgos:** costo y tiempo de provisión; **generador de carga en un host distinto** del servidor (en las pruebas históricas compartían host); versión de Python (3.14.7 local frente a 3.12 de la asesoría, T1); restaurar 1.2 GB de biblioteca con audio.
- **Datos que no se modifican:** `loadtest/results/` históricos. **Pruebas:** estructura de scripts; que cada petición quede registrada; hardware declarado en el resultado.
- **Criterio de cierre:** 5 escenarios × herramienta con perfil de hardware que cumple P6, latencias por petición guardadas, P95@25 y throughput reportados con y sin la configuración de 4 workers.
- **Fuera de alcance:** conclusiones sobre el enjambre. **Estimación:** ejecución ≈ 3–6 min por configuración y herramienta (las 4 corridas históricas ocurrieron entre las 23:01 y las ≈ 23:13 del 2026-09-23); **1–3 días** con provisión y preparación (depende del acceso).

## F6 — Git LFS y publicación del audio
- **Objetivo:** publicar el audio con Git LFS (D9f) o, si es inviable, en el repositorio institucional.
- **Archivos que cambian:** `.gitattributes` (nuevo), `.gitignore` (hoy ignora `*.mp3`), `REPRODUCIBILITY.md` §9, `CIERRE_POC.md` (R16), `DECISION-CLOSURE` §14 (por addendum).
- **Dependencias:** P8 (**verificar** `git-lfs` instalado, cuota y ancho de banda del remoto, viabilidad); D9d (términos de OpenAI). **Riesgos:** el remoto es **público** y lo subido con LFS es difícil de retirar; cuota/ancho de banda limitados; **evitar `git lfs migrate`** (reescribe la historia); ≈ 269.5 MB únicos de `lib-v5`, `lib-v9` y `lib-v10` (≈ 368.5 MB de audio en total).
- **Datos que no se modifican:** los mp3 originales, los manifiestos (sha256), la copia sellada. **Pruebas:** un clon nuevo con `git lfs pull` supera `library_inventory --check --require-complete`; el oid de LFS de cada mp3 coincide con el sha256 del manifiesto.
- **Criterio de cierre:** audio recuperable desde un clon limpio, con verificación de hashes; contingencia documentada.
- **Fuera de alcance:** instalar o configurar LFS en este sprint (no se hizo). **Estimación:** 0.5–1 día si la cuota alcanza.

## F7 — Panel humano, gold y SUS
- **Objetivo:** ≥ 10 evaluadores validan el gold (κ ≥ 0.70) y responden el SUS (D7, D8).
- **Archivos que cambian:** `human_eval/CONSENT_TEMPLATE.md` (validada por el asesor), `SUS_INSTRUMENT_ES.md` (versión publicada citada), `TASK_SCRIPT_v1.md` (adaptar o construir el visor); `metrics/sus.py` (κ ≥ 0.70 y regla de desacuerdo, tras definir P4); datos reales fuera de la base efímera; `CIERRE_POC.md` §4.
- **Dependencias:** **F1 cerrada y gold congelado**, P4, P7, reclutamiento. **Riesgos:** reclutar n ≥ 10; que el gold no alcance κ ≥ 0.70 (⇒ redefinir la regla y **repetir la corrida**); el guion pide una gráfica de convergencia y una traza que **no existen**; κ inestable con marginales sesgados (reportar % de acuerdo).
- **Datos que no se modifican:** el gold congelado durante la validación; **no se fabrican respuestas** (`CIERRE_POC.md` §4.7). **Pruebas:** cálculo del SUS y κ (ya probados con datos ficticios); nueva prueba del umbral κ ≥ 0.70 y del gatillo de desacuerdo.
- **Criterio de cierre:** n ≥ 10 con consentimiento, datos crudos con sha256, κ y SUS calculados con el protocolo; decisión registrada ante desacuerdo.
- **Fuera de alcance:** cambiar el gold en función de las respuestas dentro de la misma corrida. **Estimación:** **no estimable** (reclutamiento); análisis ≈ 1 día.

## F8 — Actualización de resultados y conclusiones
- **Objetivo:** evaluar H1 conjuntivamente con las definiciones oficiales y actualizar toda la documentación.
- **Archivos que cambian:** `CIERRE_POC.md`, `README.md`, `EVIDENCE_INDEX.md`, `REPRODUCIBILITY.md`, ADR-0019, enmiendas B1–B10 de `MASTER-SPEC`/`DECISION-CLOSURE` (cambio separado y justificado), **paquete de evidencia nuevo** (el 2026-09-24-final no se reescribe), borrador de tesis (sustituir la H1 comparativa).
- **Dependencias:** F1–F7. **Riesgos:** presentar como éxito un resultado exploratorio; mezclar resultados históricos y nuevos; H1 exige las **tres** condiciones simultáneas (`F1 ≥ 0.85` ∧ `L_resp < 2.0 s` ∧ `SUS > 75`).
- **Datos que no se modifican:** los históricos (se presentan **junto a** los nuevos, etiquetados como versión anterior). **Pruebas:** las de preservación; un test de consistencia documental (ningún documento afirma H1 confirmada salvo que los tres resultados oficiales lo respalden).
- **Criterio de cierre:** H1 evaluada con los tres resultados oficiales o declarada no evaluable; limitaciones actualizadas; paquete de evidencia con `MANIFEST.sha256`.
- **Fuera de alcance:** cambios de arquitectura. **Estimación:** 1–2 días tras F7.

## 5. Estimación total (orientativa)

| Bloque | Esfuerzo técnico | Espera externa |
|---|---|---|
| F0–F4 (métrica, gold, réplicas, línea base, inferencia) | ≈ 3–4 días tras la aprobación de la regla | aprobación de P1–P3 |
| F5 (hardware objetivo) | 1–3 días | obtención del hardware |
| F6 (Git LFS) | 0.5–1 día | cuota / términos de OpenAI |
| F7 (panel) | ≈ 1 día de análisis | **reclutamiento de ≥ 10 evaluadores (no estimable)** |
| F8 | 1–2 días | — |

Lo que no se puede acelerar: la respuesta humana del SUS y la del panel, y una medición en hardware que aún no está disponible.
