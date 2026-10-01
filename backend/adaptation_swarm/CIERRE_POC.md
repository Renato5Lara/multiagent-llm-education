# Cierre de la PoC `adaptation_swarm` — estado frente a la asesoría

> **Fecha:** 2026-09-25 · **Estado auditado:** `HEAD = 9c4808f` · **Fuente:** auditoría final de cumplimiento (solo lectura) y su corrección posterior.
> **Qué pregunta responde este documento (y por qué es nuevo):** *«¿qué requisitos de la asesoría demuestra la PoC, con qué evidencia y qué límites exactos, y qué no puede afirmarse?»*
> `EVIDENCE_INDEX.md` indexa la evidencia y `REPRODUCIBILITY.md` explica cómo repetirla; ninguno cruza requisito por requisito contra la asesoría. Aquí no se repite lo que esos documentos ya dicen: se enlaza.
>
> **Regla de lectura:** este documento **no declara confirmada la hipótesis H1** de la asesoría (`F1_adapt ≥ 0.85 ∧ L_resp < 2.0 s ∧ SUS > 75.0`, conjuntiva). F1 no cumple, el SUS no tiene datos y la latencia cumple solo con una configuración declarada.
> No convierte pruebas de infraestructura en cumplimiento metodológico, no presenta `F1_adapt = 0.8031` como éxito frente a `0.85`, no presenta un SUS sin respuestas como validado y no presenta la reconstrucción parcial de `corrida-poc-1` como la base original.

> **ACTUALIZACIÓN 2026-09-25 — respuesta del asesor (§8).** El asesor confirmó que la implementación actual no basta para cerrar la validación metodológica: `F1_adapt` debe redefinirse como inclusión/exclusión multimodal 4×4 con audio, el gold de Balanced se redefine sin el desempate, se requieren 10 réplicas con semillas independientes, una línea base fuerza bruta frente a PSO y mediciones en hardware cercano a 8 vCPU / 32 GB; la hipótesis oficial es conjuntiva. **`F1_adapt = 0.8031` pasa a ser un resultado HISTÓRICO de la definición anterior (`gold-v1`) y no se reutiliza como resultado final.** Este documento **no reescribe** los resultados históricos: se conservan tal cual. Plan: `ROADMAP_POST_ASESOR.md`.

Estados: **demostrado** · **parcialmente demostrado** · **abierto** (medido y no alcanza el umbral, o sin evidencia de la ventaja alegada) · **no ejecutado**.

## 1. ESTADO DE CIERRE DE LA PoC

**Veredicto:** la PoC queda **cerrada como PoC técnica con limitaciones** (construcción, demostración y medición computacional). **No** queda cerrada como validación de la hipótesis: la fase de evaluación (DSRM fase 5) está incompleta por el SUS y por el gold sin validar, y H1 no se confirma. Los identificadores `Rnn` remiten a la matriz de la §2.

### 1.1 Demostrado
- Arquitectura **AG0–AG4** ejecutada de extremo a extremo (100/100 ciclos por corrida, 0 fallos) sobre Redis Streams, LangGraph y PostgreSQL, con PSO de ecuaciones literales de la asesoría y fitness de 4 términos (R07–R11; las pruebas con Redis y PostgreSQL son evidencia documentada de sesiones anteriores, **no re-verificada** en la auditoría del 2026-09-25).
- **Paquete de 4 modalidades**: código validado en sandbox (Python 90/90 variantes; C++ 90/90 solo en `lib-v10`), diagramas Mermaid derivados del AST y renderizados a SVG (270/270), texto y **audio TTS real** (OpenAI) con identidad e integridad por sha256 (R05, R12, R13, R15).
- **Dataset sintético n = 100** con las marginales exactas de la asesoría (25/25/25/25 y 20×5; 5 réplicas por celda) (R17).
- **Convergencia** según el criterio literal (`k_stop` medio 1.65–1.79, máx 5; CR = 1.00) y brecha media al óptimo global de 0.007–0.014 en 𝓕 (R19, R08).
- **Reproducibilidad del núcleo**: la re-ejecución en proceso del PSO+𝓕 con el código de `HEAD` reproduce exactamente los 100 casos de `corrida-poc-1` (R26, parcial).

### 1.2 Parcialmente demostrado
- **RNF-01 / RNF-04 (latencia y throughput):** con **4 workers**, P95@25 usuarios ≈ 1.1 s y ≈ 41 req/s con 0 % de error; con **1 worker no se cumplen** (P95@25 ≈ 2.2 s; ≈ 16 req/s). Generador y servidor comparten host; la latencia es de **selección desde una biblioteca offline** (R20, R21).
- RF-02, RF-03, RF-04, RF-06: el mecanismo está probado, pero `W`, mensajes, iteraciones y desglose de 𝓕 **de los 100 casos no están versionados** (R02–R04, R06).
- Texto (sin evaluación humana), overhead de comunicación y coherencia (definición del tesista, sin umbral de la asesoría), entorno real frente al declarado, reproducibilidad de la pila completa y reconstrucción parcial de `corrida-poc-1` (R14, R22, R25, R26, R28).

### 1.3 Abierto
- **RNF-03 `F1_adapt ≥ 0.85`: NO CUMPLE.** `F1_adapt = 0.8031` (IC95 0.711–0.877) en ambas corridas; la sensibilidad pre-registrada llega a 0.8164 como máximo (R18; límites de la definición en la §3). **Es el resultado HISTÓRICO de la definición anterior** (`gold-v1`, etiqueta única, audio fuera de la métrica): tras la respuesta del asesor (§8) la evaluación oficial usará una definición nueva y una corrida nueva, y este valor no se reutiliza como resultado final.
- La **ventaja del enjambre** frente a alternativas (fuerza bruta, monolítico, reglas): no hay línea base ni comparación de tiempos (R08, R27).
- **Almacenamiento externo del audio** (mecanismo pendiente; la copia sellada es local) (R16).
- **Timeout de compilación de C++** (`g++` sin límite propio; el timeout externo no mata el contenedor) (R29).

### 1.4 No ejecutado
- **SUS (RNF-05):** 0 participantes, 0 respuestas. **Validación del gold por panel:** 0 valoraciones (R23; ver §4).
- **Shapiro-Wilk + t de Student / Wilcoxon sobre `L_resp` y `F1_adapt`** (asesoría §4.5): solo existe código para el SUS (R24).
- **Curvas de convergencia** (asesoría §4.1): no hay código ni datos por iteración versionados (R19).
- **Benchmark empírico frente a LMS / reglas / LLM monolítico (OE2):** solo análisis documental (R27).
- **TTS y LLM reales** en la validación del 2026-09-25 (la generación es evidencia previa, respaldada por los manifiestos), y las pruebas con PostgreSQL + Redis en esa auditoría (documentadas, no re-verificadas).

### 1.5 No debe afirmarse
1. Que **H1 está confirmada** (ni total ni parcialmente confirmada como conjunto).
2. Que el `F1_adapt` mide «la calidad de la adaptación multimodal»: mide coincidencia de la modalidad dominante con una etiqueta del generador de perfiles, sobre 3 de 4 clases (§3).
3. Que `F1_adapt = 0.8031` cumple, «casi cumple» o es estadísticamente equivalente a `0.85`: el IC95 incluye 0.85, pero el criterio de la asesoría es `≥ 0.85` y **no se cumple**.
4. Que el enjambre **redujo la latencia o la carga** frente a una línea base: no existe tal comparación.
5. Que la latencia baja es mérito del enjambre: es consecuencia de **seleccionar desde una biblioteca generada offline** (M1), que el asesor aceptó de forma condicionada.
6. Que RNF-01/RNF-04 se cumplen **sin matiz**: con 1 worker no se cumplen; el cumplimiento es con 4 workers, en una máquina de 8 hilos y 7.5 GiB de RAM.
7. Que `corrida-poc-1` y `corrida-poc-2` son **réplicas independientes**: comparten semilla, dataset y configuración; solo cambia la biblioteca (0/100 etiquetas cambian). El F1 idéntico es **una** medición vista con dos bibliotecas.
8. Que las corridas demostraron **código Python/C++**: las dos corridas usaron `lib-v5` y `lib-v9`, solo Python; el C++ se validó en la biblioteca (`lib-v10`, 90/90) y en el sandbox, pero **ninguna corrida usó `lib-v10`**.
9. Que el SUS, la usabilidad o la validez del gold estén «pendientes de superar»: **no hay dato alguno**; no se simulan.
10. Que la reconstrucción PostgreSQL de `corrida-poc-1` sea la **base original**: solo contiene `swarm_runs` (1) y `swarm_cycles` (100); no hay `swarm_iterations`, `agent_messages` ni `multimodal_packages`.
11. Que un clon del repositorio puede re-ejecutar ciclos (falta el audio) ni que las corridas se reproducen desde el commit registrado (`d31d29c` no contiene `adaptation_swarm/`).
12. Que existe preservación externa del audio.
13. Que `F1_adapt = 0.8031` sea el resultado final de la PoC: tras la respuesta del asesor (2026-09-25) es el resultado **histórico** de la definición anterior (§8).

## 2. Matriz de cumplimiento (29 requisitos)

Columnas: (1) requisito · (2) implementación real · (3) evidencia versionada · (4) prueba ejecutada en la auditoría del 2026-09-25 · (5) estado · (6) limitación exacta · (7) dónde declararlo.

### A. Requisitos funcionales

| # | Requisito | Implementación real | Evidencia versionada | Prueba ejecutada (auditoría 2026-09-25) | Estado | Limitación exacta | Dónde declararlo |
|---|---|---|---|---|---|---|---|
| R01 | RF-01 perfil JSON estandarizado, parsing n=100 | `profiles/models.py` (`ProfileRequest`), `POST /api/adaptation` | `datasets/synthetic_profiles/profiles-v1.jsonl` (sha256 en el manifiesto), `dee4f5c` | `test_dataset_profiles` (suite 243) | **demostrado** | Perfiles **sintéticos** (Dirichlet en torno a centroides por arquetipo); no hay estudiantes reales. | Cap. 3 (muestra), Cap. 6 (validez externa) |
| R02 | RF-02 AG1 asigna W | Regla perfil→W (ADR-0019 #4), `agents/ag1_*` | Código; `W` por ciclo se persiste en `swarm_cycles` | No (necesita Redis+PG: `test_agents_library`) | **parcialmente demostrado** | Los CSV de exportación de BD versionados (`db_corrida-poc-*_cycles.csv`, 12 columnas) **no incluyen `W`**: el vector de las 100 corridas no se puede inspeccionar desde Git. | Anexo de evidencia; nota en EVIDENCE_INDEX |
| R03 | RF-03 búsqueda/ensamble paralelo con trazas de mensajes | AG0 + Redis Streams + AG1–AG4 (`agents/`, `bus/`) | `n_messages` por caso en el JSON (45–73); pruebas de solapamiento (`inflight_overlap`) en `test_cycle_integration` | Solo `test_metrics::test_parallelism_evidence` (puro) | **parcialmente demostrado** | La traza de mensajes de los 100 casos **no está versionada** (solo contadores); el solapamiento se prueba en un ciclo de la rebanada, no agregado sobre los 100. | Cap. 5 (RF03) con esa reserva |
| R04 | RF-04 orquestador ejecuta PSO y 𝓕, log de iteraciones | `pso/`, `fitness/`, AG0 (LangGraph) | `2e3bf02`; `PSO-AUDIT-corrida-poc-1.md` (resumen); `pso_diagnostics` en el resumen de poc-2 | `test_pso_engine`, `test_pso_phi`, `test_fitness`, `test_pso_diagnostics` (suite 243) | **parcialmente demostrado** | Algoritmo y ecuaciones demostrados. El **log de iteraciones por caso no se conservó**: `swarm_iterations` de poc-1 no es recuperable (ver R28); solo hay agregados. | Cap. 5; Anexo reproducibilidad |
| R05 | RF-05 paquete con las 4 modalidades | `MultimodalPackage`, validación de paquete | Resumen de corridas: `audio_in_every_package=true`, 100/100 paquetes | Sandbox Python 90/90, C++ 12/12, Mermaid 6/6; integridad de audio | **demostrado** | «Código Python/C++»: las corridas entregaron **Python**; C++ existe solo desde `lib-v10`, que **ninguna corrida usó**. | Cap. 5 (`EVIDENCE_INDEX.md` §2 corregido el 2026-09-25) |
| R06 | RF-06 métricas de cada ciclo en BD | Tablas `swarm_runs`, `swarm_cycles`, `swarm_iterations`, `agent_messages`, `multimodal_*` | Migración Alembic `b2f4c9d10a02`; `test_persistence` | Sí, **solo** `swarm_runs`/`swarm_cycles` en PG real (cargador; validación del 2026-09-25, `fe5bd64`) | **parcialmente demostrado** | Esquema y persistencia probados en el entorno aislado (documentado). La base **original** de las corridas no se puede reproducir completa (R28). | Cap. 5; Anexo reproducibilidad |

### B. Arquitectura, algoritmo e infraestructura

| # | Requisito | Implementación real | Evidencia versionada | Prueba ejecutada (auditoría 2026-09-25) | Estado | Limitación exacta | Dónde declararlo |
|---|---|---|---|---|---|---|---|
| R07 | AG0–AG4 (5 agentes) | AG0 con LangGraph; AG1–AG4 servicios sin estado por Redis Streams (ADR-0019) | 100/100 ciclos, 0 fallos (ambas corridas); `test_boundaries` | `test_boundaries`; sandboxes de AG2/AG3 | **demostrado** | AG1–AG4 son **procesadores de mensajes sin estado de ciclo**; las «partículas» del enjambre son candidatos, **no agentes** (DECISION-CLOSURE §5.1). Debe redactarse así para no sobredimensionar «inteligencia de enjambre entre agentes». | Cap. 3 (arquitectura), Cap. 6 |
| R08 | PSO y fitness (ecuaciones literales, parada ε=0.001/k_max=15) | φ=min(2,max(0,round(x))), N=20, w=0.729, c1=c2=1.494 | `2e3bf02`; ADR-0019; sensibilidad `10995c6` | `pso_engine`, `pso_phi`, `fitness`, `sensitivity_preserved` | **demostrado** (implementación) · **abierto** (ventaja alegada) | 𝓕 es constante a tramos: `g_best` **no cambia tras la inicialización en 48/100 (poc-1) y 43/100 (poc-2)** ciclos; 16.6–17.1 % de partículas duplicadas. El espacio son solo 6.561 configuraciones y la fuerza bruta se calcula (brecha media al óptimo 0.0068 / 0.0136; 10 y 14 casos en el óptimo); **no hay medición de tiempo PSO vs fuerza bruta**, así que «el enjambre reduce carga y latencia» (asesoría §1.4) **no está demostrado**. | Cap. 6 (discusión) |
| R09 | Redis como bus real | Redis Streams (`bus/redis_bus.py`) | `test_messages_bus`, cargas con `sample_resources` | No (requiere contenedor) | **demostrado** (documentado, no re-verificado hoy) | Redis del entorno aislado, no institucional. Memoria máx. medida 448 MB (Locust) / 842 MB (JMeter) con 4 workers. | Cap. 5 |
| R10 | PostgreSQL | SQLAlchemy + Alembic | Cadena Alembic desde BD vacía (bootstrap verificado) | Sí, bootstrap y carga en PG real (validación del 2026-09-25) | **demostrado** | ver R28 | Anexo reproducibilidad |
| R11 | API | `POST /api/adaptation` (clave `X-Swarm-Key`, 503 sin ella), router en `HEAD` | `test_api_adaptation`; `loadtest/` | No (requiere servicios) | **demostrado** (documentado, no re-verificado hoy) | Es el camino medido en las pruebas de carga. | Cap. 5 |

### C. Contenido multimodal

| # | Requisito | Implementación real | Evidencia versionada | Prueba ejecutada (auditoría 2026-09-25) | Estado | Limitación exacta | Dónde declararlo |
|---|---|---|---|---|---|---|---|
| R12 | Código (Python/C++) | Generado por LLM (`openai`), validado en sandbox podman; C++ traducido y compilado | Manifiestos: 90 `code` por versión; `lib-v10`: C++ 90/90 | **90/90 variantes Python + C++ 12/12** en sandbox real | **demostrado** | El LLM converge a veces a la forma de referencia (`identical_to_reference`); aislamiento del contenedor verificado hoy (red, raíz `EROFS`, `CapEff=0`). Riesgo abierto: `g++` sin timeout propio y el timeout externo no mata el contenedor. | Cap. 5; Cap. 6 (riesgo) |
| R13 | Diagramas Mermaid/SVG | Mermaid derivado del **AST** del código; render con mermaid-cli+Chrome | 270 `diagram` + 270 `svg` por versión; auditoría semántica lib-v8/v9/v10: 0 hallazgos | Mermaid **6/6** (parser directo, render válido/ inválido, distingue Chrome de parser) | **demostrado** | ADR-0019 lo declaraba «no implementado»; actualizado el 2026-09-25. Validación semántica = heurísticas de la propia herramienta, no juicio humano. | Cap. 5 |
| R14 | Texto conceptual | LLM (`openai`), 90 por versión | Auditoría semántica: lib-v5 6/90 hallazgos → lib-v8..v10 0/90 | Suite semántica (`test_semantic_validation`) | **parcialmente demostrado** | Se valida longitud, vocabulario e identificadores; **no** corrección pedagógica ni por personas (panel: 0 valoraciones). | Cap. 6 |
| R15 | Audio real (TTS) | OpenAI TTS; audio narra exactamente el texto elegido (hash encadenado) | 270 mp3 por versión con `provider=openai`, sha256 en manifiestos | `library_inventory --check --require-complete` (exit 0); cobertura de hashes de audio | **demostrado** (existencia, identidad, integridad) | **TTS y LLM reales no se ejecutaron en esta validación**; la generación es evidencia previa (manifiestos). El audio se entrega por referencia (`GET` aparte, fuera de `L_resp`). | Cap. 5 |
| R16 | Almacenamiento externo del audio | Decisión C: híbrida (audio fuera de Git); copia sellada local | `DECISION-CLOSURE §14`, `07_biblioteca/sealed_copy/` (solo listas de hash, 0 mp3) | Integridad local verificada | **abierto** | Mecanismo **PENDIENTE**: sin proveedor/LFS/almacenamiento institucional; la copia sellada está **en el mismo equipo**. Un clon **no puede re-ejecutar ciclos** sin el audio. | DECISION-CLOSURE §14, REPRODUCIBILITY §9 (ya lo dicen); Cap. 6 |

### D. Métricas y validación

| # | Requisito | Implementación real | Evidencia versionada | Prueba ejecutada (auditoría 2026-09-25) | Estado | Limitación exacta | Dónde declararlo |
|---|---|---|---|---|---|---|---|
| R17 | Dataset sintético n=100 (25/25/25/25; 20×5) | `profiles/`, seed `20260923` | `profiles-v1.jsonl`, `gold-v1.jsonl` (sha256) | Conteos verificados hoy: 100 únicos; 25×4; 20×5; **5 réplicas por celda**; 1 concepto por perfil (30 conceptos distintos) | **demostrado** | Marginales exactas por construcción. **Recursividad excluida** (decisión delegada, no confirmada por el asesor). 30 conceptos usados vs 32 del currículo. | Cap. 3 |
| R18 | **RNF-03 F1_adapt ≥ 0.85** + matriz 4×4 + gold | `gold/f1.py`, tabla pre-registrada (20 celdas) | `corrida-poc-1/2` congeladas, `F1-AUDIT`, sensibilidad | `test_frozen_runs_preserved`, `test_gold_f1`, `test_sensitivity_preserved` | **abierto — NO CUMPLE** | **F1_adapt = 0.8031 < 0.85** (IC95 bootstrap 0.711–0.877; accuracy 0.81; F1 por clase: code 0.832, diagram 0.769, text 0.809). Sensibilidad pre-registrada: máx. 0.8164, tampoco alcanza. Ver §3 para las limitaciones de la definición. | Cap. 5 (resultado) y Cap. 6 (por qué no se cumple) |
| R19 | RNF-02 T_conv ≤ 15 iter; CR ≥ 98 %; curvas de convergencia | `metrics/convergence.py` | poc-1: k_stop media 1.65 (máx 4), T_conv 41.2 ms; poc-2: 1.79 (máx 5); CR = 1.00 (DEC-10: `stop_reason=epsilon`) | Recomputo desde los casos (suite 243) | **parcialmente demostrado** | Cumple, pero es **tautológico** (`k_max=15`) y la parada literal se activa en plateaus. **Curvas de convergencia (§4.1): no existe código ni datos versionados** para generarlas → **no ejecutado**. | Cap. 5/6 |
| R20 | RNF-01 L_resp < 2.0 s (P95, ≤ 25 usuarios) | `POST /api/adaptation`; L_resp = HTTP → último byte del JSON | `loadtest/results/` (Locust y JMeter, 1 y 4 workers), `f2a602d` | No (sin servicios); solo estructura de scripts y resúmenes (`test_loadtest_structure`, suite 243); las cifras se leyeron de los `summary.md` archivados | **parcialmente demostrado** | **4 workers: P95@25 = 1.10 s (Locust) / 1.12 s (JMeter) ✔. 1 worker: 2.2 s / 2.3 s ✘.** P95@50 = 2.1–2.4 s y @100 = 4.0–4.5 s (fuera del criterio, que es ≤25). Latencia = **selección desde biblioteca offline (M1)**, sin descarga de audio ni persistencia asíncrona; «4 workers» es configuración del tesista. | Cap. 5 con ambas configuraciones; Cap. 6 (M1) |
| R21 | RNF-04 throughput ≥ 20 req/s, error < 1 % | Idem | Idem | Idem | **parcialmente demostrado** | **4 workers: 39–42 req/s con 10–100 usuarios (9.6 y 18.7 req/s con 1 usuario), 0 % errores ✔. 1 worker: 14.5–17.6 req/s ✘.** Generador y servidor **comparten host**; bucle cerrado (`wait_time = constant(0)`); una sola corrida por escenario y herramienta. | Cap. 5; Cap. 6 |
| R22 | M2 overhead de comunicación; M4 coherencia temática | `comm_overhead_ms`; `Coher(S)` dentro de 𝓕 | Media 179 ms (poc-1) / 167 ms (poc-2) en el resumen | Recomputo (suite) | **parcialmente demostrado** | La asesoría **no da fórmula ni umbral** (MASTER-SPEC M2/M4 = gap de especificación); la definición es del tesista. El overhead medio (~170 ms) **supera** la latencia de ciclo en proceso (P95 60–73 ms) porque suma mensajes que se solapan: **no es aditivo**. El desglose de 𝓕 por caso (`g_best_breakdown`) no está versionado. | Cap. 5, con la definición explícita |
| R23 | RNF-05 SUS > 75 (n ≥ 10) | `metrics/sus.py`, `sus_cli`, tablas vacías | `human_eval_status.json`: **0 participantes, 0 respuestas**; `0961b58` | `test_sus_panel` (solo cálculo, con datos de prueba) | **no ejecutado** | **Sin respuestas no hay puntaje.** No puede afirmarse ni un valor ni «pendiente de superar». Tampoco hay validación del gold por el panel (0 valoraciones, 20 celdas). | Cap. 6; H1 no evaluable |
| R24 | Protocolo inferencial §4.5 (Shapiro-Wilk; t de una muestra / Wilcoxon vs L₀=2.0 s y F1₀=0.85) | Solo para SUS (`sus.py`) | Bootstrap IC95 del F1 | No | **no ejecutado** (L_resp y F1) | No hay Shapiro/t/Wilcoxon sobre L_resp ni F1. El F1 es un agregado sobre 100 casos: no hay distribución por caso sobre la cual aplicar el test de la asesoría tal como está redactado. El IC95 del F1 **incluye 0.85**. | Cap. 4/6: declarar la desviación |
| R25 | Entorno declarado (Python 3.12, 8 vCPU / 32 GB, Docker, JMeter y Locust, monitoreo CPU/RAM/Redis) | Python **3.14.7**, podman, portátil i7-11370H (8 hilos) con **7.5 GiB** de RAM | `06_entorno/environment.json`, `sample_resources.py` | Entorno leído hoy | **parcialmente demostrado** | Desviaciones: versión de Python, hardware (≈ ¼ de la RAM), podman en lugar de Docker, generador de carga en el mismo host. JMeter y Locust **sí** se ejecutaron (5 escenarios cada uno); CPU/RAM/Redis sí se muestrearon. | Cap. 3 (entorno real) |

### E. Reproducibilidad, benchmark y pendientes

| # | Requisito | Implementación real | Evidencia versionada | Prueba ejecutada (auditoría 2026-09-25) | Estado | Limitación exacta | Dónde declararlo |
|---|---|---|---|---|---|---|---|
| R26 | Reproducibilidad | Semilla `f(batch_seed, profile_id, replicate)`, `config_hash`, versiones, paquete con `MANIFEST.sha256` | `frozen_runs.md` (hashes), paquete `2026-09-24-final` | Verificación de hashes; recomputo de F1 desde los casos guardados; **re-ejecución en proceso del núcleo PSO+𝓕 de los 100 casos de `corrida-poc-1` con el código de `HEAD`** (`test_sensitivity_preserved`, suite 243) | **parcialmente demostrado** | **Verificar ≠ reproducir.** El replay reproduce exactamente `g_best_S`, `g_best_F`, `k_stop` y la etiqueta de los 100 casos y las métricas de las 6 configuraciones de sensibilidad, pero solo del **núcleo** (semilla → 𝓕 desde los artefactos de la biblioteca → parada literal); **no** re-ejecuta la pila completa (AG0–AG4 por Redis, ensamblado del paquete, persistencia, HTTP). Las corridas registran `git.commit = d31d29c` con `dirty = true`, y `adaptation_swarm/` no existe en ese commit (`git diff d31d29c HEAD` añade 99 archivos). Re-ejecutar la pila exige Redis, PG y el audio. | Anexo de reproducibilidad |
| R27 | OE2: benchmark frente a LMS, reglas y LLM monolítico | Tabla comparativa documental (asesoría §2.1) | — | — | **no ejecutado** (empíricamente) | No existe línea base ejecutada (ni LLM monolítico ni reglas). Las latencias de las soluciones A/B/C son afirmaciones de la asesoría. La única referencia interna es `argmax(W)`: F1 = 0.615. El GAP tecnológico **no está verificado empíricamente** (MASTER-SPEC §15 lo advierte). | Cap. 2/6: presentarlo como análisis documental |
| R28 | Reconstrucción de `corrida-poc-1` en BD | `tools/load_corrida_poc1_fixture.py` (`fe5bd64`) | `test_corrida_poc_1_loader`, `test_corrida_poc_1_reconstructed_postgres` (opt-in) | Sí (validación del 2026-09-25): PG real, 5/5 | **parcialmente demostrado** | Solo 1 fila de `swarm_runs` + 100 de `swarm_cycles`. **No** hay `swarm_iterations`, `agent_messages` ni `multimodal_packages` (no existen artefactos originales); `pso_audit` no es ejecutable sobre ella. **No es la base original.** | REPRODUCIBILITY §5.1 (ya declarado) |
| R29 | Pendientes técnicos declarados | — | `adaptation_swarm/sandbox_cpp.py` (`_SCRIPT`: `timeout 5` solo envuelve la ejecución, no `g++`; `CppSandbox.run` no nombra ni elimina el contenedor al vencer su `wait_for`) | — | **abierto** | Timeout de compilación de C++ (no afecta a las pruebas actuales). TTS/LLM reales no ejecutados en esta validación. | Cap. 6 (limitaciones) |

## 3. Limitaciones estructurales del F1 (necesarias para no sobreinterpretar 0.8031)

> **Nota 2026-09-25:** estas limitaciones describen la definición **histórica** (`gold-v1`). El asesor la sustituyó (D1, D2; §8): el audio entra en la métrica y el desempate de Balanced hacia `code` queda rechazado. Se conservan para interpretar el resultado histórico y como justificación de la nueva definición.

1. **`audio` nunca es clase gold** (ADR-0019 #5): fila y columna de la matriz 4×4 en cero. `F1_adapt = macro_f1_defined` promedia **3** clases; con las 4 (0/0 ⇒ 0) es **0.6024**. El audio **no influye** en el F1: la métrica no evalúa la adaptación de la modalidad audio.
2. **`Balanced-Multimodal` siempre tiene gold `code`** (empate exacto ⇒ orden código>diagrama>texto>audio); el gold real es `code` 50, `diagram` 25, `text` 25 (50 % `code`).
3. **El gold depende solo del arquetipo**: no varía con la dificultad, aunque la tabla tenga 20 celdas. Es, en la práctica, «arquetipo → modalidad».
4. **La «predicción» es la salida del propio enjambre** (`argmax e_m(g_best)`), no un clasificador independiente; el F1 mide **coincidencia con la etiqueta del generador de perfiles**, no calidad de adaptación percibida.
5. **El techo lo fija la definición, no el PSO**: el F1 del óptimo global de 𝓕 (fuerza bruta) es **0.803**, igual al medido; `argmax(W)` da 0.615. De los 19 errores: 13 por W ≠ gold y 6 porque el óptimo de 𝓕 no incluye el gold.
6. **Las dos corridas no son réplicas independientes**: misma semilla, dataset y configuración; solo cambia la biblioteca (0/100 etiquetas cambian; 71 con el mismo `g_best`). El F1 idéntico es **una** medición vista con dos bibliotecas.
7. El IC95 (0.711–0.877) **incluye 0.85**: no permite afirmar que el valor verdadero sea menor, pero **tampoco cumplimiento**; frente al criterio de la asesoría (≥ 0.85) el resultado se declara **no cumplido**.
8. Sin validación externa del gold (panel: 0 valoraciones).

## 4. VALIDACIÓN HUMANA PENDIENTE

**Estado:** 0 participantes, 0 respuestas SUS y 0 valoraciones del gold (`06_entorno/human_eval_status.json` del paquete; `python -m adaptation_swarm.sus_cli status` → «PENDIENTE DE RECOLECCIÓN HUMANA»).
Con menos de 10 evaluadores el código **no calcula conclusiones** (`metrics/sus.py`: `analyze_sus`, `analyze_gold_panel`). Nada de esta sección puede completarse con software.

### 4.1 Qué se debe recolectar
1. **SUS (RNF-05; asesoría §3.5.4 y §4.4):** cuestionario de 10 ítems (Likert 1–5) a **al menos 10** evaluadores expertos (docentes de programación e ingenieros de software).
2. **Validación del gold por el mismo panel (DECISION-CLOSURE §7.2, punto 2):** cada evaluador valora las **20 celdas** (arquetipo × dificultad) de la tabla `gold-v1`: «¿la modalidad dominante esperada es razonable para ese perfil y esa dificultad?» (sí/no; opcionalmente 1–5 y un comentario).

### 4.2 Prerrequisitos abiertos (decisiones que este documento NO toma ni inventa)
- **Consentimiento:** `backend/adaptation_swarm/human_eval/CONSENT_TEMPLATE.md` es una plantilla **sin validar** por comité de ética o asesor (DEC-16). **Actualización 2026-09-25 (D8b):** el asesor validará la plantilla y, según su respuesta, no se requiere trámite institucional adicional; la validación formal sigue pendiente de registrarse.
- **Versión en español del SUS:** `SUS_INSTRUMENT_ES.md` es una traducción habitual **no seleccionada ni citada formalmente** (DEC-16). **Actualización 2026-09-25 (D8a):** el asesor indicó adoptar una **versión española publicada y validada** del SUS; la referencia concreta está **por citar** (`ROADMAP_POST_ASESOR.md`, P7).
- **Material que usará el evaluador:** `TASK_SCRIPT_v1.md` pide una **gráfica de convergencia** y una **traza de mensajes** y admite que **no existe un visor HTML dedicado** (no se declara implementado). Hay que decidir, antes de recolectar, si se adapta el guion a lo que existe (JSON de `run_slice`, artefactos de la biblioteca) o si se construye el visor (trabajo fuera del alcance documental). Lo que se decida debe quedar fijado y versionado: es lo que el SUS evalúa.
- **Perfil y reclutamiento:** criterio de selección, proporción docentes/ingenieros y forma de contacto: no definidos.
- **Umbral de acuerdo del panel del gold:** la asesoría, DECISION-CLOSURE y el código no lo fijaban. **Fijado por el asesor el 2026-09-25 (D7b): κ ≥ 0.70**, y un **desacuerdo mayoritario exige reportar, redefinir la `rule_version` y repetir la corrida.** Queda por precisar qué es «desacuerdo mayoritario» y si κ ≥ 0.70 es global, por celda o ambos (P4). El mismo panel (n ≥ 10) valida el gold y responde el SUS (D7a, D7c).
- **Dónde se guardan los datos reales:** `sus_cli` escribe en la base a la que apunte `DATABASE_URL`. No debe usarse la base aislada de pruebas (efímera; su volumen puede reiniciarse) ni mezclarse con datos de desarrollo sin una decisión explícita.

### 4.3 Protocolo (según los materiales existentes en `backend/adaptation_swarm/human_eval/`)
1. Registrar al participante con **seudónimo** (E01, E02…), rol y, opcionalmente, años de experiencia, con su consentimiento (`sus_cli add-participant … --consent`).
2. Sesión de 25–30 min con `task-script-v1`, sobre los artefactos de **una versión de biblioteca fija** y con los perfiles indicados en el guion (Visual-Dominante × Bucles; Lógico-Sintáctico × Funciones).
3. Aplicar el SUS (10 ítems, Likert 1–5) **después** de usar el artefacto (`add-sus` o `import-sus`).
4. Solo si el evaluador forma parte del panel: valorar las 20 celdas del gold (`add-gold` o `import-gold`).
5. **La tabla gold no se modifica en función de las respuestas** dentro de esta corrida: un desacuerdo se reporta y, si se decide cambiar la tabla, será una `rule_version` nueva y una nueva corrida (nunca una edición).

### 4.4 Datos que deben conservarse
- **Por participante:** seudónimo, rol, años (opcional), consentimiento (sí/no y fecha), fecha y modalidad de la sesión.
- **Contexto experimental de cada sesión:** versión del guion (`task-script-v1`), versión y traducción del instrumento SUS, `library_version`, commit de git (y si el árbol estaba limpio) y los perfiles y `correlation_id`/JSON mostrados.
- **Respuestas crudas:** los 10 ítems (1–5) **sin transformar**, el puntaje derivado, y los votos del gold (20 celdas sí/no, valoración 1–5 y comentario si existen).
- **Exclusiones:** cualquier participante o respuesta excluida, con el criterio (definido **antes** de ver los datos).
- **Exportación y huella:** `sus_cli export` a CSV, su **sha256** y una copia fuera de la base.
- **No conservar:** nombre, correo ni otros datos personales (el consentimiento solo autoriza seudónimo y respuestas).

### 4.5 Cálculo (ya implementado y probado; no se modifica)
- **Puntaje SUS por evaluador:** ítems impares → (respuesta − 1); ítems pares → (5 − respuesta); suma × 2.5 → 0–100 (asesoría §4.4).
- **Agregado:** media, desviación estándar, mínimo, máximo e IC95 (t de Student).
- **Contraste (asesoría §4.5):** Shapiro-Wilk (α = 0.05); si p > 0.05 (o no es calculable), t de Student de una muestra contra 75 (H1: media > 75); si no, Wilcoxon de rangos con signo contra 75 (H1: mediana > 75).
- **Panel del gold:** % de acuerdo global y por celda, κ de Fleiss y celdas con desacuerdo mayoritario. Con marginales muy sesgados κ puede ser bajo aun con acuerdo alto: **reportar siempre el % de acuerdo junto a κ**.

### 4.6 Criterio de aceptación
- **SUS:** media **> 75.0** con **n ≥ 10** (asesoría §4.4, «Grado B+»). El código informa `exceeds_threshold = media > 75 ∧ p < 0.05` (asesoría §4.5) y lo califica de **hallazgo estadístico, no de veredicto automático**. Si la media es ≤ 75 o p ≥ 0.05, RNF-05 **no se cumple** y se reporta tal cual.
- **Gold:** **κ ≥ 0.70** (fijado por el asesor el 2026-09-25, D7b; alcance de κ y «desacuerdo mayoritario» por precisar, P4). Un desacuerdo mayoritario obliga a reportar, redefinir la `rule_version` y repetir la corrida. El panel **no se ejecuta antes de congelar la nueva definición del gold** (`ROADMAP_POST_ASESOR.md`, F7).
- **Efecto sobre H1:** H1 es conjuntiva (`F1 ≥ 0.85 ∧ L_resp < 2.0 s ∧ SUS > 75`). **Aun con SUS > 75, H1 no queda confirmada mientras `F1_adapt < 0.85`.**

### 4.7 Prohibición de fabricar respuestas
No se permite **fabricar, simular, imputar, rellenar, duplicar ni «completar»** respuestas SUS ni votos del gold; no usar LLM, agentes ni scripts como evaluadores; no reutilizar los datos ficticios de `test_sus_panel` fuera de sus pruebas (ni mezclarlos con una base que contenga datos reales); no reportar un puntaje SUS con n < 10; no descartar respuestas por su valor; no redactar la conclusión antes del análisis. Como recomendación metodológica (no exigida literalmente por la asesoría), no contar como evaluadores a quienes desarrollaron el artefacto ni a quienes no lo hayan usado.

## 5. Revisión de consistencia entre documentos

Documentos cruzados: `Asesoria.docx` (copia del 2026-09-23), `MASTER-SPEC-2026-09-23.md`, `DECISION-CLOSURE-2026-09-23.md`, `EVIDENCE_INDEX.md`, `REPRODUCIBILITY.md` y este documento; además `README.md`, `ADR-0019`, `DECISION-REGISTER` y el borrador de tesis (`.docx` del 2026-09-21).
Precedencia (DECISION-CLOSURE §2): asesoría > respuestas del asesor > decisiones técnicas derivadas > arquitectura actual > código histórico.

### 5.1 Contradicciones dentro del repositorio — **corregidas** en este cambio
| # | Documento | Afirmación obsoleta o incompleta | Realidad verificada | Corrección aplicada |
|---|---|---|---|---|
| A1 | `README.md` | «17 archivos, 218 pruebas»; `test_library_sandbox_integration.py`, `test_corrida_poc_1_preserved.py` («necesita cargar la corrida en PostgreSQL») y `test_cpp_render.py` «quedan fuera de Git por ahora» | Versionados (`081b426`, `fe5bd64`, `9c4808f`); `test_corrida_poc_1_preserved.py` es puro; suite sin servicios = 19 archivos, 243 pruebas | Sección «Pruebas» reescrita |
| A2 | `README.md` | «Estado de los resultados» no mencionaba corridas no independientes, latencia con 1 worker, reconstrucción parcial ni H1 | Ver §1.5 | Estado ampliado y puntero a este documento |
| A3 | `REPRODUCIBILITY.md` §9 | Misma afirmación sobre archivos «fuera de Git»; «las pruebas `test_corrida_poc_1_preserved` … leen filas reales de `swarm_runs`» | Falso desde `081b426`; contradecía su propia §5.1 | Viñetas corregidas |
| A4 | `REPRODUCIBILITY.md` §5/§9 | `git.dirty = true` sobre `d31d29c` sin precisar que el código no existía en ese commit; «determinista … bit a bit» sin acotar el alcance | `git diff d31d29c HEAD -- backend/adaptation_swarm` añade 99 archivos; el replay cubre el núcleo PSO+𝓕, no la pila | Precisado |
| A5 | `EVIDENCE_INDEX.md` §2 | Enumeraba «código Python y C++» y «100/100 paquetes válidos en poc-2» sin precisar que el código de las corridas era solo Python | C++ 90/90 es de `lib-v10`, que ninguna corrida usó | Precisado |
| A6 | `EVIDENCE_INDEX.md` §1/§3/§4 | No decía que las corridas no son réplicas independientes; el cumplimiento con 4 workers sin matices; SUS sin enlace al protocolo | Ver §1.5 y §4 | Precisado y enlazado |
| A7 | `ADR-0019` «Limitaciones declaradas» | «C++ no implementado»; «Render de Mermaid no implementado» | C++ 90/90 (`lib-v10`) y SVG 270/270; probados el 2026-09-25 | Actualización fechada; el texto original se conserva, marcado como superado |
| A8 | `tests/adaptation_swarm/integration_env/README.md` | «`test_corrida_poc_1_preserved.py` (necesita cargar la corrida en PostgreSQL)» | Ya es puro; la parte PostgreSQL es opt-in en otro archivo | Línea corregida |
| A9 | `experiments/EVIDENCE_PACKAGE_STATUS.md` | «`ADR-0019.md` … idénticos a los versionados» y «`README_EVIDENCE_INDEX.md` … sin contradicciones» | Dejan de ser ciertos tras A5–A7 | Dos viñetas actualizadas (el paquete congelado no se toca) |

### 5.2 Contradicciones en documentos fuera del repositorio — **no modificados** (enmienda propuesta)
| # | Documentos | Discrepancia | Enmienda propuesta |
|---|---|---|---|
| B1 | `DECISION-CLOSURE` §7.3 ↔ ADR-0019 #6 | El cierre define `F1_adapt = macro-F1` sobre las **4** clases; la implementación reporta `macro_f1_defined` (3 clases, 0.8031) y `macro_f1_all4` (0.6024) | Nota en §7.3 remitiendo al ADR-0019 #6 y a la §3 de este documento |
| B2 | `DECISION-CLOSURE` §7.1–7.2 ↔ ADR-0019 #5 | El cierre afirma que Balanced «no colapsa siempre a la misma clase por diseño»; con `e_m` enteros y τ = 0.05 el desempate equivale a empate exacto y **siempre** resuelve a `code` (gold: 25/25) | Nota en §7.2 |
| B3 | `DECISION-CLOSURE` §5.1 ↔ código | «Una partícula adicional se inicializa en el punto heurístico»; `pso/engine.initialize` la coloca como partícula 0 y **N = 20 la incluye** | Corregir «adicional» → «incluida» |
| B4 | `DECISION-CLOSURE` §9.1 ↔ §8.2 y datos | «por cada uno de los 32 conceptos»; la biblioteca cubre **30** (Recursividad y «Traza y pila de llamadas» sin usar, coherente con la exclusión de §8.2) | Corregir a 30, citando §8.2 |
| B5 | `DECISION-CLOSURE` §9.2 y §12.3 | RNF-01/RNF-04 «pendientes de medición»; barrido de sensibilidad «no ejecutado todavía» | Ya medidos/ejecutados: enlazar R20, R21 y la sensibilidad (máx. 0.8164; su orden respecto de las corridas solo se apoya en marcas de tiempo, como ya dice `adaptation_swarm_sensitivity.md`) |
| B6 | `MASTER-SPEC` §17 y §20 | «Redis AUSENTE», «PSO AUSENTE», «JMeter NO COMPROBADO»… y «Python 3.12 — CUMPLE» | Marcar §20 como histórico (estado del 2026-09-23 previo a implementar) y aclarar que «3.12» es el `Dockerfile` de la plataforma; las corridas usaron 3.14.7 |
| B7 | `MASTER-SPEC` (fila «Hipótesis») ↔ `Asesoria.docx` | El MASTER-SPEC dice que la asesoría «no presenta H1/H0»; la matriz de consistencia sí rotula «Hipótesis General (H1)» | El fondo del MASTER-SPEC se mantiene (es una **meta de desempeño conjuntiva**, no una hipótesis de diferencia entre condiciones): matizar la redacción |
| B8 | Borrador de tesis (`Formato del informe de tesis … 2026-09-21.docx`) ↔ `Asesoria.docx` | El borrador trae **otra H1** (comparativa: el contenido «diferirá de la condición de comparación» en adherencia curricular, corrección técnica, coherencia intermodal o pertinencia pedagógica), marcada «pendiente de actualización». La H1 de la asesoría es `F1 ≥ 0.85 ∧ L_resp < 2.0 s ∧ SUS > 75` | Sustituir antes de redactar resultados. **Esta PoC no pone a prueba la H1 del borrador** (no hay condición de comparación ni evaluación de adherencia curricular o pertinencia pedagógica) |
| B9 | `DECISION-REGISTER` §J (líneas 385 y 397) | «H1 confirmada» | Se refiere a la **Iteración 6.4 del runtime (08-08)**, otra hipótesis y otro subsistema; no a la H1 de esta PoC. Aclararlo para evitar la colisión de nombres |
| B10 | Dos `Asesoria.docx` | `Acesoria Docente/` (2026-09-23) y `Cursos 2026/Tesis/` (2026-06-22) tienen contenido distinto | Conservar una sola como autoridad |

### 5.3 Comprobación «ningún documento declara H1 confirmada»
Búsqueda en `README.md`, `REPRODUCIBILITY.md`, `EVIDENCE_INDEX.md`, este documento, `ADR-0019`, `EVIDENCE_PACKAGE_STATUS.md`, los informes de `experiments/results/`, `MASTER-SPEC`, `DECISION-CLOSURE`, `DECISION-REGISTER` y el borrador de tesis: **ningún documento declara confirmada la H1 de esta PoC**. La única coincidencia textual («H1 confirmada», `DECISION-REGISTER` §J) corresponde a otra hipótesis (B9). Los documentos del proyecto ya decían «no se declara cumplimiento de la asesoría» (README, EVIDENCE_INDEX).

### 5.4 Coherencia verificada (los documentos coinciden)
Umbrales de RNF-01…05 (`L_resp < 2.0 s` con P95 hasta 25 usuarios; `≥ 20 req/s` con error < 1 %; `T_conv ≤ 15`; `F1 ≥ 0.85`; `SUS > 75` con n ≥ 10) entre la asesoría, MASTER-SPEC y `loadtest/README.md`; los cinco escenarios de concurrencia (1, 10, 25, 50, 100); `F1_adapt = 0.8031` y sensibilidad máx. 0.8164 entre README, EVIDENCE_INDEX, REPRODUCIBILITY y el paquete; SUS 0/0 en `human_eval_status.json`, README y EVIDENCE_INDEX; el carácter offline de la biblioteca (M1) entre DECISION-CLOSURE §9 y `loadtest/README.md`.

## 6. Método y alcance de la auditoría de origen

Fuente de autoridad: `Acesoria Docente/Asesoria.docx` (2026-09-23). **Leídos completos:** la asesoría, DECISION-CLOSURE, EVIDENCE_INDEX, README, ADR-0019, `F1-AUDIT`, `PSO-AUDIT`, `loadtest/README.md` y los cuatro `summary.md` de carga.
**Leídos parcialmente:** MASTER-SPEC (§§1–2, 4–6.1, 13–25.1), DECISION-REGISTER (encabezados y Fases C, G, H), REPRODUCIBILITY.
**Ejecutado (2026-09-25):** suite «sin servicios» (19 archivos, **243 pasan**, PostgreSQL y Redis detenidos, 0 conexiones, 0 escrituras en `datasets/` ni `experiments/`); sandboxes reales (C++ 12/12, Mermaid 6/6, 90 variantes Python); `library_inventory --check --require-complete` (exit 0); cargador de la reconstrucción parcial sobre un PostgreSQL real limpio (5/5).
**No ejecutado:** pruebas con PostgreSQL + Redis (79 documentadas), llamadas reales a OpenAI (TTS y LLM), pruebas de carga, SUS.
El informe original vive fuera del repositorio (`Auditoria/auditoria_final_cumplimiento_poc_adaptation_swarm_2026_09_25.md`); su R26 se corrigió tras la entrega (el replay del núcleo PSO+𝓕 sí re-ejecuta los 100 casos) y esa versión corregida es la que se incorpora aquí.

## 7. Conclusiones

**Puede afirmarse:** se construyó y ejecutó de extremo a extremo una arquitectura AG0–AG4 con PSO (ecuaciones literales de la asesoría), Redis Streams, LangGraph y PostgreSQL (100/100 ciclos por corrida); cada paquete contiene las 4 modalidades reales; el PSO converge según el criterio literal y queda a 0.007–0.014 de 𝓕 del óptimo global; con la configuración de 4 workers se midió P95@25 ≈ 1.1 s y ≈ 41 req/s sin errores; el F1_adapt medido es **0.8031**, por debajo de 0.85, con auditoría que descarta un defecto de implementación; la infraestructura de SUS y del panel existe y está probada.
**No puede afirmarse:** lo de la §1.5.
**Evidencia que falta:** (1) SUS con n ≥ 10 evaluadores reales y panel del gold (§4); (2) mecanismo de almacenamiento externo del audio; (3) Shapiro-Wilk + t/Wilcoxon sobre `L_resp` (y una forma defendible de tratar el F1) o declarar la desviación; (4) curvas de convergencia y trazas de mensajes, `W` y desglose de 𝓕 de los 100 casos; (5) línea base empírica (fuerza bruta cronometrada; opcionalmente una solución monolítica o de reglas) si se quiere sostener OE2 y la justificación §1.4 de la asesoría; (6) re-ejecución de la **pila completa** (agentes por Redis, ensamblado, HTTP) con el código de `HEAD`: el núcleo PSO+𝓕 ya coincide en los 100 casos, la pila no se ha re-ejecutado; (7) las enmiendas de la §5.2.
**¿PoC cerrada?** Sí, como PoC técnica con limitaciones; **no** como validación de la hipótesis (§1).
**Único paso necesario:** recolectar la evaluación humana real (SUS con ≥ 10 evaluadores y validación del gold por ese panel; §4): es lo único que no se puede sustituir por una declaración de limitación ni por software, y desbloquea RNF-05, la validez del gold y el estado de H1.
> **Actualización 2026-09-25:** la respuesta del asesor añade pasos **previos**: aprobar una `rule_version` y congelar el gold nuevo, ejecutar 10 réplicas, la línea base, y repetir latencia/throughput en hardware cercano a 8 vCPU / 32 GB. **El panel humano solo puede ejecutarse después de congelar el gold.** Ver `ROADMAP_POST_ASESOR.md`.

## 8. Respuesta del asesor (2026-09-25) y su efecto

> **Reserva de fidelidad:** se registra el **resumen comunicado por el tesista**; el texto literal del asesor está **por anexar** (`Docuemento de tesis/ADDENDUM-DECISIONES-ASESOR-2026-09-25.md`). Este documento no reescribe los resultados históricos.

| ID | Decisión (resumen) | Efecto en este documento |
|---|---|---|
| D1 | `F1_adapt` = inclusión/exclusión multimodal 4×4, **audio obligatorio**; nueva `rule_version` y nueva corrida | R18: el 0.8031 es **histórico**; la definición oficial es nueva (pendiente P1–P3) |
| D2 | Se rechaza el desempate de Balanced hacia `code`; gold que represente las cuatro modalidades; nueva corrida sobre los 100 perfiles | §3 describe la definición histórica; B2 resuelto en su dirección, falta fijar el conjunto esperado (P2) |
| D3 / D4 | Se ratifica excluir Recursividad / N = 20 incluye la partícula heurística | B4 y B3 quedan ratificados; sin cambios de código |
| D5 | K = 10 réplicas con semillas independientes | R26: las dos corridas históricas no son réplicas; las nuevas se ejecutarán con `analysis/replicas.py` |
| D6 | Hipótesis oficial conjuntiva (`F1_adapt ≥ 0.85` ∧ `L_resp < 2.0 s` ∧ `SUS > 75`) | B7/B8 resueltos: la H1 comparativa del borrador de tesis se sustituye. **H1 sigue sin confirmarse** |
| D7 | Mismo panel (n ≥ 10) valida gold y SUS; **κ ≥ 0.70**; desacuerdo mayoritario ⇒ reportar, redefinir `rule_version`, repetir | §4.2 y §4.6 actualizados |
| D8 | SUS en versión española publicada y validada; el asesor valida el consentimiento; sin trámite institucional adicional | §4.2 actualizado; falta citar la versión (P7) |
| D9 | Git LFS para el audio; repositorio institucional como contingencia; falta verificar cuota, instalación y viabilidad | R16 sigue **abierto** hasta verificarlo (F6) |
| D10 (a–c) | Respondidas con la opción hardware cloud de 8 vCPU / 32 GB: no son definitivas las mediciones con 7.5 GiB; repetir en ese hardware (comunicaciones previas: «cercano a 8 vCPU / 32 GB») | R20, R21, R25: pasan a **históricas / exploratorias** |
| D11 | Shapiro-Wilk + prueba correspondiente sobre latencias por petición; unidad por caso para el F1; línea base fuerza bruta frente a PSO | R08, R24, R27: siguen abiertas; implementación preparada (ver abajo) |

**Clasificación (corrección del tesista, 2026-09-25):** D9a–D9f fueron **respondidas con la opción Git LFS** y D10a–D10c con la opción **hardware cloud de 8 vCPU / 32 GB**. **Detalles no especificados** (no se completan por suposición): pronunciamiento específico sobre descarga pública del audio (D9a), términos de OpenAI (D9d) y retención de versiones antiguas (D9e); verificación técnica de cuota/instalación/viabilidad de Git LFS (D9c); **aceptación definitiva** de M1 y de los 4 workers, que queda condicionada a la medición en el hardware objetivo (D10a/D10b). Lo comunicado por el tesista está transcrito en `TRANSCRIPCION-RESPUESTAS-ASESOR-2026-09-25.md` (carpeta de documentos de tesis; **no** es el texto original del asesor).

### 8.1 Estado del sprint acelerado (preparación, no resultados)
Implementado y probado en módulos **nuevos** (los históricos no se tocan; `test_gold_v2::test_historical_modules_and_data_are_untouched` lo comprueba): métrica multietiqueta 4×4 con audio (`gold/f1_multilabel.py`), reglas gold-v2 **candidatas y PROVISIONALES** con guardia de aprobación (`gold/rubric_v2.py`; `APPROVED_RULE_VERSIONS` **vacío**), ejecutor puro de K réplicas (`analysis/replicas.py`), informe exploratorio de alternativas de Balanced (`analysis/balanced_alternatives.py`) y línea base PSO frente a fuerza bruta (`analysis/baseline_bruteforce.py`). **No se ejecutó ninguna corrida oficial ni se aprobó ninguna regla.** Salvaguardas reforzadas tras la auditoría: `replicas.run()` revalida la puerta oficial en lugar de confiar en el plan, solo una regla gold-v2 registrada puede aprobarse y los analizadores nuevos no escriben en `loadtest/results/` ni en `adaptation_swarm/`. Regresión pura **sin Redis**: 325 pruebas pasan (`tests/adaptation_swarm -m "not integration"`, excluyendo `test_messages_bus.py` y `test_agents_library.py`: 40 pruebas que requieren un Redis en ejecución y **no se ejecutaron**; tampoco las marcadas `integration`, que requieren PostgreSQL, Redis, LLM o contenedores).

### 8.2 Resultado exploratorio que conviene conocer (PROVISIONAL; no evidencia)
Sobre las corridas históricas y alternativas explícitas, el F1 varía entre ≈ 0.64 y ≈ 0.87 **solo según cómo se defina «incluida» y el gold**; **una sola** de las 12 combinaciones v2 supera 0.85 (con agregación por caso) y ninguna lo hace con macro o micro. Es un cálculo post-hoc: **no se usa para elegir la regla ni para declarar cumplimiento**; la regla se aprueba por criterio conceptual antes de la corrida nueva (`ROADMAP_POST_ASESOR.md` §4).

### 8.3 Resolución de las discrepancias B1–B10 tras la respuesta
B1 (F1 3 vs 4 clases) → D1; B2 (Balanced) → D2; B3 (N = 20) → D4 ratificado; B4 (30 vs 32) → D3 ratificado; B5 (M1 y 4 workers) → D10/D11, con la aceptación definitiva de M1 y de los 4 workers **condicionada a la medición en hardware cloud de 8 vCPU / 32 GB**; B6 (Python 3.12) → sin respuesta específica; B7 y B8 (hipótesis) → D6; B9 y B10 (colisión de «H1 confirmada», dos `Asesoria.docx`) → aclaraciones documentales del tesista. Las enmiendas de `MASTER-SPEC` y `DECISION-CLOSURE` siguen en un cambio documental **separado** (en esos documentos solo se añadió un aviso inicial).

## 9. Actualización 2026-09-30 — decisión del asesor sobre RF-03 y `comm_overhead_ms`

> **Registro posterior.** Las filas **R03** y **R22** de este documento se conservan **sin cambios** como historial del estado al 25/09/2026 («parcialmente demostrado»). Esta sección registra la decisión del asesor del **30/09/2026** (`Docuemento de tesis/ADDENDUM-DECISIONES-ASESOR-RF03-COMM-OVERHEAD-2026-09-30.md`, en respuesta a `CONSULTA-ASESOR-RF03-COMM-OVERHEAD-2026-09-30.md`). *Reserva de fidelidad:* respuesta transcrita según la comunicó el tesista; original por anexar.

| ID | Estado al 25/09 (histórico) | Estado tras la decisión del 30/09/2026 | Criterio |
|---|---|---|---|
| R03 (RF-03) | parcialmente demostrado | **CUMPLE** (Alternativa A) | Despacho concurrente a AG2–AG4 (`publish_many` + `asyncio.gather`), mensajes en vuelo simultáneos (`inflight_overlap = True`, 200/200 ciclos históricos auditados), logs inter-agente y `cycle_id`. `parallel_overlap` (0/200) **no** es criterio normativo: se conserva como diagnóstico; el MASTER-SPEC lo exigía como sobre-especificación técnica. No se afirma ejecución simultánea de handlers |
| R22 (M2 `comm_overhead_ms`) | parcialmente demostrado; definición del tesista | **Métrica descriptiva y de diagnóstico** (Alternativa A) | Fórmula implementada sin cambios; no es tiempo de pared, no es aditiva, puede superar `total_ms`, sin umbral normativo, no condiciona ningún RNF |

**Consecuencias (según el asesor):** solo cambio documental. No se modifican la función de aptitud (DEC-04), el PSO, el gold (P2), la regla de inclusión (P1), las semillas ni el dataset; no cambia la `rule_version`, no se reabre el pre-registro y no se reejecuta el K = 10. El K = 10 v2 (`3088e69` / `dc74ae9`) permanece congelado; el K = 10 v3 no está ejecutado. RF-06, RNF01–RNF04, F1_adapt, PSO y H1: sin afectación.
