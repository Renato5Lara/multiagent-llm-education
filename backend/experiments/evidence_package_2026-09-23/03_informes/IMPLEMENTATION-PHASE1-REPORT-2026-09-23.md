# Implementation Phase 1 — Informe de cierre de sesión (2026-09-23)

Contrato: `DECISION-CLOSURE-2026-09-23.md` (asesoría aprobada). Repo: `feat/pretest-m1-v4` @ `d31d29c` (sin commits nuevos; árbol sucio, ver §17).
Estados usados: **VERIFICADO** (ejecutado y comprobado) · **IMPLEMENTADO** · **PARCIAL** · **NO IMPLEMENTADO** · **BLOQUEADO**.

## 11. Qué parte del vertical slice funciona realmente — VERIFICADO

`python -m adaptation_swarm.run_slice` (Visual-Dominant × Bucles, semilla fija) ejecuta de punta a punta:
perfil → AG0 (LangGraph) → AG1 (W) → PSO → selección desde la biblioteca por Redis (AG2+AG3+AG4, audio MP3 real) → 𝓕 → p_best/g_best → convergencia → `MultimodalPackage`.
Checklist §26 del prompt: AG0–AG4 reales · Redis transporta mensajes reales · LangGraph controla el ciclo · W · PSO con iteraciones reales · p_best/g_best · φ · 𝓕 real · artefactos de código/diagrama/texto/audio reales · paquete · `stop_reason`/`k_stop`/`T_conv` · `correlation_id` reconstruye el ciclo (también desde Postgres) · reproducible con semilla fija — **todas VERIFICADAS por pruebas de integración**.

## Estado por componente

| Componente | Estado | Evidencia |
|---|---|---|
| Contratos (`swarm-msg-v1`, FIPA-ACL, IDs, estados, errores) | VERIFICADO | `test_messages_bus.py` |
| Bus Redis Streams (grupos por agente, idempotencia, pendientes, log, memoria compartida) | VERIFICADO | Redis real; el ciclo falla explícitamente sin Redis |
| AG1 Profil-Agent (W, Σ=1, determinista) | VERIFICADO | `test_agents_library.py`, `test_dataset_profiles.py` |
| AG2 Code-Agent (LLM + sandbox real) — solo Python | VERIFICADO (C++ NO IMPLEMENTADO) | 90 variantes pasan los asserts en sandbox podman |
| AG3 Diagram-Agent (AST → Mermaid) — solo fuente | VERIFICADO (render NO IMPLEMENTADO) | 270 diagramas válidos derivados del AST |
| AG4 Text-Agent + TTS OpenAI real | VERIFICADO | 90 textos, 270 MP3 reales con hash de entrada = hash del texto |
| AG0 + grafo LangGraph | VERIFICADO | `test_cycle_integration.py` |
| PSO (ecuaciones literales, φ, RNG PCG64, N=20, parada literal) | VERIFICADO | `test_pso_*.py` (ecuaciones a mano, precedencia ε/k_max, determinismo) |
| Fitness (Simil, Coher, Redund, CostT; α=.40 β=.30 γ=.15 δ=.15) | VERIFICADO | `test_fitness.py` |
| Gold preregistrado + F1/matriz 4×4 + bootstrap | VERIFICADO | `test_gold_f1.py` |
| Dataset 100 perfiles (4×5×5, 30 conceptos reales, sin Recursividad) | VERIFICADO | `datasets/synthetic_profiles/`, manifiesto con sha256 |
| Biblioteca M1 versionada (30 conceptos × 24 artefactos) | VERIFICADO | `lib-v5-9ae9ffdd`; revalidada entera por `test_library_full_coverage.py` |
| Persistencia Postgres (7 tablas) + trazabilidad | VERIFICADO | `test_persistence.py` (reconstrucción perfil→ciclo→iteración→mensajes→paquete) |
| Endpoint `POST /api/adaptation` | VERIFICADO | `test_api_adaptation.py` + carga real |
| Métricas (T_conv it/ms, CR, latencia, throughput, overhead M2, CPU/RAM/Redis) | IMPLEMENTADO+VERIFICADO | `metrics/` |
| Locust (5 escenarios) | VERIFICADO | `backend/loadtest/results/*` |
| JMeter (5 escenarios) | PARCIAL: plan validado con 1 escenario (25 hilos) | `loadtest/results/jmeter_u25_summary.json` |
| SUS | NO IMPLEMENTADO (solo la función de puntaje estaba prevista; no se recolectó nada) | — |
| Panel de expertos (validación del gold) | NO IMPLEMENTADO | requiere personas |

## Resultados MEDIDOS (no son declaraciones de cumplimiento)

**Corrida `corrida-poc-1` (100 casos, lib-v5, PSO N=20, en proceso, 100 ciclos reales con Redis + Postgres):**
- 100/100 completados, 0 fallidos. `stop_reason`: 100 `epsilon`, 0 `k_max`, 0 `error`. **CR = 1.00**. `k_stop`: media 1.65, mediana 1, **máx 4** (≤15 ✔ RNF02, aunque `T_conv≤15` es tautológico por `k_max=15`).
- **F1_adapt (macro, clases definidas) = 0.803**, IC95 bootstrap [0.711, 0.877]; accuracy 0.81; macro-4 (audio 0/0→0) = 0.602. **Por debajo del umbral 0.85 → RNF03 NO se cumple con esta configuración.** Matriz (filas gold code/diagram/text/audio; columnas predicción): `[[42,5,3,0],[5,20,0,0],[4,2,19,0],[0,0,0,0]]`.
- Calidad de búsqueda: brecha media al óptimo global (fuerza bruta, 6.561 configs) = 0.0068; 10/100 casos en el óptimo global exacto; brecha máx 0.045.
- Latencia de ciclo en proceso (sin HTTP): P50 45 ms, P95 60 ms.
- Sensibilidad pre-registrada (α∈{.3,.4,.5}, N∈{10,20,30}): F1_adapt 0.803–0.816, concordancia de predicciones con la referencia 0.99–1.00, CR=1.00 en todas → resultado estable frente a esas variaciones (`experiments/results/adaptation_swarm_sensitivity.json`).

**Carga HTTP (Locust; 30 s por escenario; persistencia mínima síncrona activada; 8 CPU compartidos con el generador de carga):**

| Config | Usuarios | req/s | P50 ms | P95 ms | P99 ms | Error % |
|---|---|---|---|---|---|---|
| 1 worker | 1 / 10 / 25 / 50 / 100 | 16.7 / 17.6 / 17.4 / 16.9 / 16.5 | 58 / 530 / 1300 / 2400 / 4700 | 75 / 810 / **2100** / 4400 / 8500 | 86 / 930 / 2300 / 5600 / 9300 | 0 |
| 4 workers | 1 / 10 / 25 / 50 / 100 | 10.3 / 41.6 / 45.0 / 44.3 / 44.2 | 93 / 220 / 520 / 1000 / 1800 | 110 / 410 / **910** / 2100 / 4200 | 160 / 680 / 1100 / 2700 / 5500 | 0 |

Lectura honesta: con 1 worker el sistema satura ≈17 req/s (un núcleo al 100 %) → **RNF04 (≥20 req/s) NO se cumple** y P95 a 25 usuarios = 2.1 s (**RNF01 <2.0 s NO se cumple** por 0.1 s). Con 4 workers: ≈45 req/s con error 0 % (**RNF04 cumplido en esta medición**) y P95 a 25 usuarios = 0.91 s (**RNF01 cumplido para ≤25 usuarios**); a 50 y 100 usuarios el P95 supera 2 s (la asesoría solo fija RNF01 hasta 25). Con 4 workers y 1 usuario la latencia es mayor (93 vs 58 ms; no atribuido). JMeter (25 hilos, 4 workers): 44.7 req/s, P95 947 ms. Memoria de Redis máx ≈ 424 MB en 100 usuarios (tras aligerar el log).
RNF05 (SUS) no medido.

## Errores encontrados y corregidos (y dos incidentes propios)

1. **`pip` del `.venv` apunta a otra copia del repo**: `redis`/`numpy` se instalaron primero en `/home/rlara/Documentos/Proyecto/...`; se desinstalaron de allí y se reinstalaron con `python -m pip` (memoria guardada).
2. **Constructor de biblioteca abortaba** ante un concepto fallido y dejaba directorios `.building-*`; ahora aísla el concepto (se descarta entero y se reporta) y limpia. Dos constructores corrieron a la vez por un relanzamiento mío (versiones `lib-v2`/`lib-v3`, con costo de API duplicado); quedan como versiones selladas obsoletas.
3. Diagramas con paréntesis desbalanceados (etiquetas truncadas) y textos breves fuera de longitud; código "idéntico a la referencia" en conceptos triviales (se acepta marcado `identical_to_reference=true` solo tras validar en sandbox y pedir una forma distinta; el LLM no recibe el código de referencia); dos conceptos cuya especificación de comportamiento era insuficiente (se añadió descripción y estado global).
4. **Redis "Too many connections" bajo carga** mataba silenciosamente el consumidor de AG3 y colgaba ciclos: subió `max_connections`, `publish_many` en lote, el bucle del agente ya no muere ante un fallo por mensaje (log + contador + reintento), log de auditoría sin contenido pesado y `MAXLEN` 5.000. Regresión cubierta por prueba.
5. Estado del grafo perdía la clave `pso` (LangGraph descarta claves fuera del esquema); persistencia final ya no relanza si Redis cae; respuestas de AG0 por instancia (multi-proceso).
6. Tres pruebas propias mal planteadas (aritmética/umbral) corregidas; los errores de colección `selenium`/`get_tavily_client` de la suite existente son **preexistentes**.

## Decisiones técnicas tomadas (detalle en ADR-0019)
Orden de dimensiones; variantes (audio = perfil de narración sobre el texto elegido); N=20 incluye la partícula heurística; regla perfil→W (λ=0.40); desempate τ sobre enteros ⇒ Balanced=`code` y `audio` nunca es clase gold; macro-F1 con dos variantes (`defined` principal / `all4`); CostT desde tiempos de generación medidos; respuestas por instancia de AG0; endpoint seguro por defecto (503 sin `SWARM_API_KEY`); ampliaciones de biblioteca con enlaces duros.

## Riesgos pendientes
- **F1_adapt = 0.803 < 0.85** con la configuración de referencia congelada; cualquier ajuste posterior sería post-hoc y debe declararse.
- La regla de parada literal con 𝓕 constante a tramos hace que el enjambre pare en k≈1–2: el PSO aporta poco sobre la partícula heurística (hipótesis a discutir con el asesor; la regla no se tocó — DEC-10).
- `audio` nunca es etiqueta gold (tabla preregistrada) ⇒ clase sin soporte.
- Textos generados por LLM sin verificación semántica (p. ej. un texto de "Bucle while" dice "desde cero" mientras el código cuenta desde 1).
- `CostT` mide latencia de red del proveedor con pocas muestras (monotonía por variante no garantizada).
- Todo el trabajo (y el stack CMG y la migración `928a10b002db`, padres de la migración nueva) **sigue sin versionar**; la biblioteca pesa ≈1.1 GB (5 versiones + caché TTS; versiones intermedias obsoletas).
- Coste de API real consumido (LLM + ~400 llamadas TTS) dentro de la partida de $50/mes; no se midió con exactitud.
- Prueba de carga con generador y SUT en el mismo host (8 CPU/7 GB).

## Comandos exactos (desde `backend/`, Redis y Postgres activos)
```
podman-compose up -d redis                       # (raíz del repo)  ·  .venv/bin/alembic upgrade head
.venv/bin/python -m adaptation_swarm.run_slice --json /tmp/slice.json
.venv/bin/python -m pytest tests/adaptation_swarm -q         # 141 pruebas
.venv/bin/python -m adaptation_swarm.run_experiment --sweep
.venv/bin/python -m adaptation_swarm.run_experiment --run-label mi-corrida
SWARM_API_KEY=k .venv/bin/python -m uvicorn app.main:app --port 8765 --workers 4
SWARM_API_KEY=k SCENARIO_LABEL=w4 bash loadtest/run_scenarios.sh http://localhost:8765 30
```
