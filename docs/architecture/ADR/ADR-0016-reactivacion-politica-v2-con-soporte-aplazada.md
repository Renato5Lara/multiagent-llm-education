# ADR-0016 — Reactivación de `POLITICAS["v2"]` con consumidores tolerantes a `Aplazada`

- **Estado:** Propuesto — no aceptado todavía (ver §6, "Decisión
  pendiente"). La precondición técnica que `ADR-0015 §8` dejó abierta
  ya está cerrada con evidencia real; falta una decisión de producto,
  no una pieza de ingeniería.
- **Fecha:** 2026-08-04
- **Preserva:** `runtime/kernel/deliberation/mecanica.py` (sin
  cambios), `runtime/kernel/deliberation/politica.py` (`POLITICAS`,
  sin cambios — `"v2"` ya definida por `ADR-0012`),
  `runtime/kernel/deliberation/confianza.py` (sin cambios), `ADR-0012`/
  `ADR-0013`/`ADR-0014`/`ADR-0015` (sin cambios de comportamiento)
- **Criterio de aceptación:** ver §5 y §6

## 1. Contexto

`ADR-0015` activó `POLITICAS["v2"]` en producción y la revirtió el
mismo día tras validación E2E real: el kernel convergía correctamente
(430/430 `tests/runtime/`, más una deliberación real con
margen=0.1131), pero **la integración de producto no propagaba
`urgente`** desde `app/services/runtime_bridge.py` — el bridge que de
verdad sirve `/api/students/*` — y varios consumidores de `Entrega`
asumían implícitamente que siempre existía una decisión. Su §8 dejó
una precondición explícita para cualquier reactivación futura:

> "conectar `urgente` a un disparador real de producción... y hacer
> que cada consumidor de `Entrega`/decisión maneje explícitamente el
> caso 'todavía sin decisión' — no asumirlo implícitamente. Solo
> entonces se reintenta esta activación."

Esta ADR documenta que esa precondición **ya se cumplió, con
evidencia real**, en la misma sesión:

- **Propagación de `urgente`** (commit `4fd6ed8`) —
  `registrar_evidencia_evaluacion` (`runtime_bridge.py`) gana
  `urgente: bool = False`, propagado a `PeticionHechoDelMundo`;
  `submit_evaluation` y `submit_cycle_evidence` (`students.py`) pasan
  `urgente=True` porque la `Entrega` viaja en su misma respuesta HTTP
  síncrona — el criterio exacto de `runtime.py:243`, ya correcto en
  `POST /hechos` desde antes. Clasificación completa de los 7 sitios
  de producción en `ROADMAP-RFC-0006.md §8` ("Contrato de `urgente`
  por consumidor").
- **Consumidores tolerantes a `Aplazada`** (commit `e0a83ff`,
  `tests/test_aplazada_consumidores_boundary.py`) — auditoría estática
  encontró que `module_orchestration_service.py` y
  `pedagogy_runtime_bridge.py` **ya** manejaban
  `Entrega(asunto=None, diseno=None)` sin romper (guards de Épica 2,
  julio) — nunca ejercitados contra una `Aplazada` real porque `v1`
  (δ=0) la hace estructuralmente inalcanzable. El hueco era de
  cobertura, no de código. Se cerró con dos pistas, ambas con
  Postgres real + LLM real (`OpenAIProvider`, `gpt-4o-mini`):
  1. Política de prueba δ=0.99 (mismo patrón que
     `test_parteE_walkthrough_aplazamiento.py`) — fuerza `Aplazada`
     determinista; ambos consumidores no rompen.
  2. `POLITICAS["v2"]` real, sin registrar nada nuevo — no fuerza el
     desenlace. Resultado observado esta corrida: **`Aplazada`,
     margen=0.0000** (empate exacto entre Remediar/Orientar sobre
     `"siguiente-paso(sesion)"`, `evidencia_faltante="evidencia sobre
     'siguiente-paso(sesion)'... margen 0 < delta 0.10"`) — el mismo
     tipo de caso límite matemático que `ADR-0013` ya había
     encontrado (`dominio_marginal`). Ninguno de los dos consumidores
     rompió; ambos reflejaron el estado real.

## 2. Decisión (propuesta, no aplicada)

Igual que `ADR-0015 §2`: cambiar `VERSION_POLITICA` en
`app/services/runtime_connection.py` de `"v1"` a `"v2"` — una
constante, un archivo. El mecanismo de selección
(`Identidad.version_politica` fijada atómicamente al abrir, INV-1/
INV-2; `resolver_politica()` como único punto de lectura en
`walkthrough.py`) no cambió desde `ADR-0015` y sigue siendo correcto.
Esta ADR no ejecuta ese cambio — permanece **Propuesto** hasta
resolver §6.

## 3. Engineering Gate (CLAUDE.md)

1. **¿Qué decisión implementa?** Cierra la precondición que
   `ADR-0015 §8` dejó pendiente explícitamente — no responde a un RFC
   nuevo.
2. **¿Introduce concepto nuevo?** No. `urgente` y `POLITICAS["v2"]`
   ya existían (RFC-0006 §4 Parte E, `ADR-0012`); esta ADR solo
   documenta su propagación completa hasta el tráfico real.
3. **¿Rompe algún principio P1-P17?** No. `mecanica.py`/`politica.py`/
   `confianza.py` intactos; los dos commits que preceden esta ADR
   tocan exclusivamente el Boundary de producto (`runtime_bridge.py`,
   `students.py`) y pruebas.
4. **¿Requiere modificar un RFC?** No.

## 4. Alcance NO cubierto (deliberado)

Idéntico a `ADR-0015 §4`, sin cambios: sin selección por cohorte ni
activación gradual/porcentual; sin tocar `pesos_asunto`/
`asuntos_reservados`; sin migración de sesiones ya persistidas
(quedan en `v1` para siempre, INV-1/INV-2); sin capacidad de swarm
nueva.

Adicional a esta ADR: **no se modifica `pedagogy_runtime_bridge.py`
ni `module_orchestration_service.py` para distinguir `Aplazada` de
"sin evidencia"** (ver §6) — ambos ya toleran el estado sin romper,
que es lo que esta ADR necesitaba probar. Enseñarles a leer S3
(`estado.deliberaciones`) en vez de solo S1 (`Entrega`) sería ampliar
un contrato semántico, no un hardening — decisión de producto
explícitamente fuera de este alcance.

## 5. Criterios de cierre técnico (ya cumplidos)

- `tests/runtime/`: 430/430 (sin regresión desde `ADR-0015`).
- `tests/test_students.py`: 18/18.
- Suite de integración app-level afectada por la propagación de
  `urgente`: 36/38 (2 fallas preexistentes, confirmadas idénticas sin
  el diff vía `git stash`, causa raíz distinta y no relacionada —
  registrada en memoria de proyecto, ver `bug_items_totales_ausente_
  rompe_clasificacion_reforzar`).
- `tests/test_aplazada_consumidores_boundary.py`: 3/3 — consumidores
  tolerantes bajo δ=0.99 sintético y bajo `POLITICAS["v2"]` real
  (llamando `runtime_bridge` directamente).
- `tests/test_e2e_adr0016_v2_produccion.py`: 2/2 — el mismo recorrido,
  pero por HTTP real (`client.post` → FastAPI → `students.py` →
  `runtime_bridge`), con `POLITICAS["v2"]` real:
  - `submit_evaluation` (evaluación de módulo, la ruta más común):
    confirma `identidad.version_politica=="v2"`, contrato HTTP
    coherente. Hallazgo real, no anticipado: con `objetivos=` siempre
    no vacío, Remediar/Orientar por-objetivo nunca compiten entre sí
    (disparadores mutuamente excluyentes sobre el mismo `dominada`) —
    esta ruta no alcanza `mecanica.convocar()` con una sola evidencia.
    En su lugar, bajo `θ=0.5` real (`v1` usa `θ=0`, estructuralmente
    inalcanzable), la confianza calibrada observada (0.4385) resultó
    insuficiente — RFC-0006 §3 Parte C, `derivar_decision_directa`
    devuelve `None`, el walkthrough termina en `END` sin decisión.
    **Tercer camino hacia `Entrega(None, None)`**, distinto de
    `Aplazada` (D1/D2) — mismo contrato exacto para los consumidores
    (`proyectar_entrega` no distingue la causa: sin claim vigente de
    Adaptar, da igual si fue D1/D2 aplazado, D3 insuficiente, o
    ninguna evidencia todavía), así que la evidencia de §6 sigue
    aplicando sin necesidad de una prueba de consumidor aparte.
  - `submit_cycle_evidence` (evidencia continua, no pasa `objetivos=`,
    opera sobre `"siguiente-paso(sesion)"`): SÍ alcanza
    `mecanica.convocar()` (confirmado: Remediar 0.4385 vs Orientar
    0.0000, tensión D2 real). No fuerza el desenlace; contrato HTTP
    verificado coherente bajo `Resuelta` y bajo `Aplazada`.
- Validación E2E con `VERSION_POLITICA="v2"` real: `Aplazada` real
  producida, margen=0.0000, ningún consumidor rompió.

Estos criterios demuestran que la reactivación es **técnicamente
segura**, ahora con evidencia a dos niveles (llamada directa y HTTP
real). No son, por sí solos, criterio de aceptación de esta ADR — ver
§6 y §9 (falta el recorrido en navegador real).

## 6. Decisión pendiente (bloquea `Propuesto → Aceptado`)

`module_orchestration_service.py` y `pedagogy_runtime_bridge.py` leen
exclusivamente S1 (`Entrega`, la propuesta vigente de Adaptar) y nunca
S3 (`estado.deliberaciones`). Consecuencia demostrada con evidencia
real en `test_aplazada_consumidores_boundary.py`: un estudiante que
**sí** envió evidencia, cuya deliberación quedó **`Aplazada`**, se ve
exactamente igual para estos consumidores que un estudiante que
**nunca** evaluó nada — ambos producen
`Entrega(asunto=None, diseno=None)`, y
`pedagogy_runtime_bridge.sugerir_prioridad_semanal` cuenta a los dos
como `estudiantes_con_evidencia=0`.

Bajo `v1` esto era irrelevante (`Aplazada` estructuralmente
inalcanzable). Bajo `v2` real, con margen=0.0000 observado en la
primera corrida, es un estado que **va a ocurrir en producción** con
alguna frecuencia no despreciable.

**La pregunta que esta ADR no resuelve:** ¿la capa pedagógica
(Panel Docente, sugerencia semanal, orquestación de módulo) debe
distinguir "sin evidencia" de "evidencia con deliberación aplazada"?

- Si la respuesta es **no** (el docente no necesita esa distinción
  hoy — una `Aplazada` se resuelve sola en el próximo `urgente=True`
  o escala vía Parte F): esta ADR pasa a Aceptado tal cual está,
  documentando la limitación como comportamiento conocido y
  aceptado, no como deuda.
- Si la respuesta es **sí**: hace falta que estos consumidores lean
  S3 además de S1 — una capacidad nueva (RFC-0006 ya expone
  `estado.deliberaciones`/`derivar_consenso`, así que no es un
  concepto nuevo del kernel, pero sí un cambio de contrato de estos
  dos servicios de producto) que requiere su propia mini-ficha antes
  de escribir código, no una decisión tomada de pasada aquí.

No se decide en esta sesión — se deja explícitamente abierta.

## 7. Riesgo residual conocido, no bloqueante

`competencia_sugerida=None` cuando `registrar_evidencia_evaluacion` se
llama sin `items_totales` (bug real, encontrado durante Fase 3,
registrado en memoria de proyecto). No bloquea esta ADR: los 3
llamadores reales de producción (`submit_evaluation`,
`submit_cycle_evidence`, `_registrar_diagnostico_en_runtime`) siempre
proporcionan `items_totales`; el escenario roto solo existe en 2
tests. Investigación de causa raíz diferida, sin relación con
`urgente` ni con `Aplazada`.

**Mecanismo adicional documentado, no un riesgo (Fase 4, §5):** bajo
`v2`, `submit_evaluation` puede dejar `runtime_decision.diseno=None`
por **D3-insuficiencia** (`θ=0.5`, RFC-0006 §3 Parte C) — evidencia
con confianza calibrada real por debajo de `θ`, sin que exista ninguna
`Aplazada` ni ninguna tensión D1/D2. Es un tercer camino, ya cubierto
por la misma evidencia de consumidores de §6 (`proyectar_entrega` no
distingue la causa de una `Entrega` vacía), pero vale nombrarlo
explícitamente: bajo `v2` real, un estudiante puede ver
`runtime_decision=None`-ish más seguido que bajo `v1` **incluso sin
llegar nunca a una deliberación** — dato relevante para quien lea esta
ADR preguntándose "¿con qué frecuencia pasa esto en producción?".

## 8. Estrategia de rollback

Idéntica a `ADR-0015 §7`: revertir `VERSION_POLITICA` a `"v1"` es un
cambio de una línea, sin migración, sin efecto sobre sesiones ya
abiertas bajo `v2` (permanecen `v2` para siempre — INV-1/INV-2).

## 9. Próximo paso antes de `Aceptado`

1. Resolver §6 (decisión de producto, no de ingeniería).
2. **Hecho (misma sesión):** recorrido E2E por HTTP real bajo `v2`
   real, `tests/test_e2e_adr0016_v2_produccion.py` — `submit_evaluation`
   y `submit_cycle_evidence`, ambos con `identidad.version_politica
   =="v2"` confirmada y contrato HTTP coherente en todo desenlace
   observado (`Resuelta`, `Aplazada`, D3-insuficiencia). Evidencia
   registrada en §5.
3. **Pendiente:** el mismo recorrido en navegador real (login →
   evaluación real → UI del estudiante recibe una respuesta coherente,
   sin estado inconsistente ante `Aplazada`/D3-insuficiencia) — el
   nivel de validación que `ADR-0015 §5` exigió y que HTTP-vía-
   `TestClient` no sustituye del todo (Regla de Cierre E2E real,
   CLAUDE.md).
4. Solo entonces: `VERSION_POLITICA = "v2"` en
   `runtime_connection.py`, y esta ADR pasa a Aceptado.

---

*Origen: precondición dejada explícitamente pendiente por
`ADR-0015 §8`, cerrada con evidencia real (commits `4fd6ed8`,
`e0a83ff`, `fc68456`) en la misma sesión. Rama:
`feat/confidence-calibration-remediation-orientation`. Permanece
Propuesto hasta resolver la decisión de producto de §6 y completar el
recorrido en navegador real de §9.*
