# ADR-0019 — Subsistema `adaptation_swarm`: 5 agentes + PSO + Redis + LangGraph (PoC de la asesoría 2026-09-23)

- **Estado:** Aceptado — autorización expresa del asesor (`Respuestas de las dudas.odt`, DEC-01/02/03/04/07/09) y
  `DECISION-CLOSURE-2026-09-23.md`.
- **Alcance:** solo `backend/adaptation_swarm/` (+ tablas `swarm_*`, `agent_messages`, `multimodal_*`, endpoint
  `/api/adaptation`). No modifica `backend/runtime/` (Kernel) ni el flujo real de estudiantes.

## Por qué existe un segundo subsistema multiagente

El asesor confirmó el **reemplazo** de la arquitectura de deliberación+consenso por AG0–AG4 sobre PSO para el
estudio vigente (DEC-01). El Kernel (`runtime/`) no se toca, se reclasifica como antecedente histórico/trazabilidad
y sigue atendiendo a estudiantes reales. A diferencia del clúster legacy retirado en ADR-0011/ADR-0017 (motor huérfano
sin autorización), este subsistema tiene autorización explícita y está aislado por una frontera verificable:
`tests/adaptation_swarm/test_boundaries.py` falla si `adaptation_swarm` importa `runtime` o `app.agents`/`app.swarm`.

## Arquitectura

AG0 (LangGraph) ⇄ Redis Streams ⇄ AG1..AG4. AG0 es el único agente con grafo; AG1–AG4 no tienen estado de ciclo.
`BusMessage` `swarm-msg-v1` (compatible FIPA-ACL). Biblioteca M1 versionada en `datasets/adaptation_library/<lib-vN-hash>/`.
El PSO (`pso/`) es puro: ecuaciones literales de la asesoría, φ(x)=min(2,max(0,round(x))), RNG `PCG64(seed)`.

## Decisiones técnicas tomadas en la implementación (no estaban fijadas por el cierre)

1. **Orden de dimensiones** de x ∈ ℝ⁸: `e_code, v_code, e_diagram, v_diagram, e_text, v_text, e_audio, v_audio`.
2. **Variantes**: código 0 mínima / 1 explicada / 2 con casos límite y `ejemplo_uso()`; diagrama 0 estructura / 1 detalle /
   2 completo (Inicio/Fin, etiquetas, subgrafo) derivado del **AST** del código elegido; texto 0 breve / 1 estándar /
   2 extendido; audio = *perfil de narración* (×1.15 / ×1.0 / ×0.85) sobre el texto elegido. Así el audio narra exactamente el
   texto del paquete (hash encadenado) y las 81 combinaciones (3⁴) son físicamente realizables. Por concepto:
   3 código + 9 diagramas + 3 textos + 9 audios = 24 artefactos.
3. **N = 20 incluye** la partícula heurística derivada de W (partícula 0, etiquetada `heuristic_seed`); v⁽⁰⁾ = 0.
4. **Regla perfil→W (AG1)**: `w = estilo + boost·[diagrama, código]`, `boost = 0.40·max(0, error−0.5)·(1−nivel/2)`, normalizado.
5. **Desempate τ=0.05 aplicado sobre e_m decodificados (enteros {0,1,2})**: equivale a empate exacto. Consecuencia:
   Balanced-Multimodal siempre tiene gold `code` (centroide uniforme → prioridad código>diagrama>texto>audio), y
   `audio` **nunca** es clase gold; solo puede aparecer como falso positivo.
6. **Macro-F1**: el cierre pide "promedio sobre 4 clases" pero no define 0/0; se reportan `macro_f1_defined` (excluye clases
   sin gold ni predicción; es el principal `f1_adapt`) y `macro_f1_all4` (0/0 ⇒ 0).
7. **CostT** usa el tiempo mediano de *generación* medido al construir la biblioteca (congelado en el manifiesto), lo que
   incluye la latencia de red del proveedor: la monotonía por variante no está garantizada con pocas muestras.
8. **Respuestas por instancia**: `BusMessage.instance` dirige las respuestas al stream privado de cada AG0 (despliegue
   multiproceso sin robo de respuestas); los streams de AG1–AG4 son compartidos.
9. **Endpoint seguro por defecto**: 503 sin `SWARM_API_KEY`; `X-Swarm-Key` compare_digest.
10. **Generación de código**: el LLM recibe firmas y asserts del catálogo CMG como *especificación de comportamiento* (no el
    código). Si converge a la forma canónica (p. ej. `a and b`), se acepta marcado `identical_to_reference=true` tras
    validarlo en sandbox y solo después de pedir una forma distinta.

## Limitaciones declaradas

- ~~**C++ no implementado** (la asesoría admite Python/C++): solo Python.~~ **[SUPERADO 2026-09-25 — ver «Actualización».]**
- ~~**Render de Mermaid** no implementado: se genera y valida la *fuente* Mermaid (sin renderer en el repo).~~ **[SUPERADO 2026-09-25 — ver «Actualización».]**
- El texto lo redacta un LLM: se valida longitud/vocabulario/identificadores, **no** corrección semántica.
- La regla de parada literal `|ΔF|<ε` sobre 𝓕 constante a tramos puede detener el ciclo en k=1–2 (medido, ver el informe
  de la corrida); no se altera (DEC-10).
- Ninguno de los umbrales (RNF01–RNF05) se da por cumplido sin medición real.

## Actualización 2026-09-25 (el texto original de arriba se conserva como historial)

Estado: **Aceptado** (sin cambios en las decisiones). Se actualizan solo las limitaciones que dejaron de ser ciertas y se registran las que la auditoría final añadió. Detalle y matriz: `backend/adaptation_swarm/CIERRE_POC.md`.

- **C++ ya está implementado** como variante de la biblioteca: sandbox podman (`tools/cpp_sandbox`, compilación `g++ -std=c++17` y ejecución sin red), 90/90 en `lib-v10-5dd83cd4` (87 en `lib-v9`). **Pero las corridas principales** (`corrida-poc-1`/`2`, `lib-v5`/`lib-v9`) **entregaron código Python**; ninguna usó `lib-v10`. El C++ está validado en la biblioteca y el sandbox, no como modalidad de esas corridas.
- **El render de Mermaid ya es real**: mermaid-cli sobre Chrome del sistema (`tools/mermaid_render`), 270/270 SVG en `lib-v10`; se distingue el rechazo del parser de un fallo de Chrome/Puppeteer (`tests/adaptation_swarm/test_cpp_render.py`).
- **Límites nuevos** (no cambian las decisiones de arriba): el audio nunca es clase gold, así que `F1_adapt = macro_f1_defined` promedia 3 clases (con 4 sería 0.6024); el gold depende solo del arquetipo; `corrida-poc-1` y `corrida-poc-2` no son réplicas independientes; la latencia medida es de **selección desde biblioteca offline**; `g_best` no cambia tras la inicialización en 48/100 (poc-1) y 43/100 (poc-2) ciclos.
- **Umbrales:** ya hay medición. `F1_adapt = 0.8031 < 0.85` (RNF-03 no se cumple); RNF-01/RNF-04 se cumplen solo con 4 workers; SUS sin respuestas. **La hipótesis H1 de la asesoría no está confirmada.**
- **Riesgo abierto:** `g++` no tiene timeout de compilación propio y el timeout externo de `CppSandbox` no elimina el contenedor.
