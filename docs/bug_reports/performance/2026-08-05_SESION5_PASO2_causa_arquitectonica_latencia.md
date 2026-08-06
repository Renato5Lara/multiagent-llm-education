# Sesión 5 — Paso 2: Causa arquitectónica de la latencia de personalización

## Metadata

- **Fecha:** 2026-08-05
- **Rama:** `investigacion/sesion5-rendimiento`
- **Protocolo:** observar → medir → **explicar la causa** → clasificar →
  decidir → implementar. Este documento responde los 8 puntos pedidos
  explícitamente antes de clasificar nada como defecto. **Ningún
  archivo de código modificado — solo lectura.**
- **Insumo:** Paso 1 (`2026-08-05_SESION5_PASO1_medicion_rendimiento.md`)
  — 6 mediciones reales de `POST /api/students/cycle-evidence`
  (2042–6232 ms), causa correlacionada con 1 o 2 llamadas a OpenAI por
  petición.
- **Pyodide:** confirmado cerrado en Paso 1, no reabierto aquí.

---

## 1-2. Cadena completa: del endpoint al productor LLM

```
POST /api/students/cycle-evidence          (backend/app/api/routes/students.py:540)
  └─ registrar_evidencia_evaluacion(..., urgente=True)   (app/services/runtime_bridge.py:57)
       └─ registrar_hecho(peticion, almacen, almacen_memoria)  (runtime/boundary/inbound/hechos.py:21)
            └─ ejecutar_walkthrough(
                   productor_diagnostico=productor_diagnostico_activo(),
                   productor_remediar=productor_remediar_activo(),
                   productor_orientar=productor_orientar_activo(),
                   urgente=True,
               )                              (runtime/engine/graph/walkthrough.py:475)
                 └─ LangGraph StateGraph, nodo "aplicar" con
                    ruteo condicional vía enrutar()  (walkthrough.py:301-356)
```

`productor_diagnostico_activo()` / `_remediar_activo()` / `_orientar_activo()`
(`runtime/boundary/inbound/productores.py:36-51`) seleccionan la
implementación LLM (`producir_diagnostico_llm` / `producir_remediacion_llm`
/ `producir_orientacion_llm`, cada una con `OpenAIProvider()`) **siempre
que `OPENAI_API_KEY` esté configurada** — que lo está en este entorno
(confirmado por el log de arranque de `uvicorn`: "OpenAI LLM generation
available"). Sin la clave, las tres caen a sus versiones deterministas
por regla (`producir_*_regla`), sin ninguna llamada de red.

**Las tres capacidades son candidatas a LLM. Nunca se observaron las
tres en una misma petición** (máximo 2, nunca 3) — la razón está en el
punto 3.

---

## 3. Por qué algunas peticiones hacen 1 llamada y otras 2

`enrutar()` (`walkthrough.py:301-356`) es una función pura de
`(estado, política)` — un árbol de decisión con **orden de prioridad
fijo**, re-evaluado después de cada nodo:

```
1. adaptar          (si hay decisión sin adaptar)
2. validar           (si hay decisión lista para validar)
3. modelar            (si hay veredicto sin modelar)
4. decidir             (si hay decisión derivable)
5. deliberar            (si hay tensión bloqueante)
6. tutorizar             (si hay hecho evaluable sin tutorizar)
7. diagnosticar           (si hay evidencia pendiente de diagnosticar)  ← SIEMPRE antes de 8/9
8. remediar                (si hay interpretación pendiente de remediar)
9. orientar                 (si hay interpretación pendiente de orientar)
10. decidir (directo)         (propuesta única, sin rival)
11. END
```

Para una llamada nueva a `cycle-evidence`, el hecho recién registrado
(`"competencia" in contenido`) siempre cumple la guardia
`_evidencia_pendiente_de_diagnosticar` (`walkthrough.py:200-226`) — **el
grafo pasa por "diagnosticar" en efectivamente todas las peticiones**,
de ahí que ninguna de las 6 mediciones tuviera 0 llamadas a OpenAI.

Tras "diagnosticar" (y su claim aplicado a `estado.claims` vía el nodo
"aplicar"), `enrutar()` se reevalúa. Si la interpretación resultante
para esa competencia es:
- **`dominada=False`** (el estudiante no domina el tema) → dispara
  `_interpretacion_pendiente_de_remediar` (`walkthrough.py:229-263`) →
  ruta a "remediar" → **2ª llamada LLM**.
- **`dominada=True`** (lo domina) → dispara
  `_interpretacion_pendiente_de_orientar` (`walkthrough.py:266-298`) →
  ruta a "orientar" → **2ª llamada LLM**.
- Ninguna de las dos condiciones se cumple (p. ej. ya existe una
  propuesta "en pie" sin consumir, `palabra_en_pie`) → el grafo cae
  directo a `derivar_decision_directa` → "decidir" (sin LLM) → END →
  **solo 1 llamada** (la de diagnosticar).

`dominada` es un booleano de una sola interpretación — nunca puede ser
`True` y `False` a la vez para la misma competencia en la misma
petición. Por eso **nunca se observan 3 llamadas**: Remediar y Orientar
son mutuamente excluyentes dentro de una misma petición de
`cycle-evidence` (que siempre trae `objetivos=()`, un único asunto de
sesión — el camino de múltiples objetivos, con potencialmente varias
interpretaciones simultáneas, no aplica aquí).

---

## 4. Dependencia de datos entre las dos llamadas — verificada, no supuesta

**Confirmado con evidencia de código y de documento arquitectónico —
NO son paralelizables.**

Evidencia de código: `_interpretacion_pendiente_de_remediar`/
`_orientar` (arriba) leen `estado.claims` buscando una `INTERPRETACION`
**ya vigente**. Esa interpretación es exactamente lo que el nodo
"diagnosticar" produce y el nodo "aplicar" persiste — **remediar/
orientar no pueden ni siquiera ser candidatos de ruteo hasta que
diagnosticar terminó y su claim está aplicado al estado**. No es una
dependencia de datos "en el prompt" (remediar no necesariamente cita el
texto exacto del diagnóstico dentro de su propio prompt LLM — eso no se
verificó línea por línea aquí) — es una dependencia **de ruteo del
grafo**, y es igual de real: el segundo nodo no se invoca en absoluto
sin el resultado del primero.

Evidencia de documento (RFC-0002, tabla de capacidades,
`docs/architecture/RFC-0002-domain-model.md:143-152`):

| Capacidad | Lee del estado |
|---|---|
| Diagnosticar | modelo del estudiante + resultados recientes |
| **Orientar** | **diagnóstico** + estructura de módulos |
| **Remediar** | **evidencia de no-aprendizaje** (= interpretación de Diagnosticar) |

La dependencia está en el contrato arquitectónico mismo, no es un
detalle de implementación incidental. Coincide exactamente con el
primer diagrama del tesista (`Evidencia → LLM#1 → Resultado A → LLM#2`)
— **deben permanecer secuenciales.**

---

## 5. ¿Alguna llamada es redundante, duplicada o evitable?

**No se encontró ninguna en la muestra medida.** Ambas guardias de
ruteo (`_evidencia_pendiente_de_diagnosticar`, `_interpretacion_
pendiente_de_remediar/_orientar`) ya excluyen explícitamente el caso
trivial de redundancia: un hecho ya interpretado no vuelve a
diagnosticarse (`f.id not in interpretados`), y una propuesta ya "en
pie" no se vuelve a proponer (`palabra_en_pie`) — el propio mecanismo
de ruteo ya funciona como una forma de evitar llamadas innecesarias,
antes de llegar siquiera al productor LLM. No se identificó una
oportunidad de caché/memoización adicional sobre esto: cada llamada
observada correspondía a evidencia genuinamente nueva de esta petición,
no a una repetición de un cálculo ya hecho.

---

## 6. Tres tipos de latencia, distinguidos explícitamente

- **Latencia inevitable del proveedor** — el tiempo de red + inferencia
  de cada llamada individual a `gpt-4o-mini` (`OpenAIProvider`,
  `runtime/domain/shared/llm_openai.py:78`, modelo por defecto). Esto
  es un coste externo, fuera del control de la arquitectura del
  proyecto.
- **Latencia introducida por decisión arquitectónica propia (pero
  deliberada, no un descuido):** el orden secuencial
  diagnosticar→remediar/orientar. RFC-0002 lo fija como el contrato de
  lectura de cada capacidad; RFC-0006 lo fija como el orden del
  programa pedagógico ("el orden de los chequeos ES el programa
  pedagógico", `walkthrough.py:316`). No es negociable sin reabrir esas
  RFC — clasificar esto como "defecto" contradiría directamente la
  arquitectura ya aprobada.
- **Trabajo redundante o evitable:** **ninguno identificado** en esta
  ruta (ver punto 5).

**Conclusión de este punto:** el candidato de optimización real, si lo
hay, no está en "paralelizar dos llamadas independientes" (no lo son) —
está, como mucho, en si la naturaleza secuencial en sí misma es un
costo aceptado de la arquitectura multiagente (probablemente sí, dado
que está en dos RFC distintas) o si existe margen en otro punto (p. ej.
el propio proveedor, el modelo elegido, o el tamaño del prompt — ninguno
investigado en este documento).

---

## 7. Timeout, retry, fallback — verificado, no afectó las mediciones

`OpenAIProvider.generar()` (`llm_openai.py:94-137`) usa
`con_reintentos()` (`runtime/domain/shared/llm_provider.py:24-46`):
hasta 3 intentos, backoff exponencial (1s, 2s, 4s), **solo** ante
excepciones transitorias del SDK (`APIConnectionError`,
`APITimeoutError`, `RateLimitError`, `InternalServerError`) — cualquier
otro error se propaga en el primer intento. No hay timeout explícito
configurado en la construcción del cliente `OpenAI()` (usa el default
del SDK). No existe fallback a otro proveedor dentro de una petición ya
en curso — la selección regla-vs-LLM ocurre una sola vez, al construir
el productor activo (`productor_*_activo()`), no como reintento tras un
fallo de LLM.

**En las 6 peticiones medidas no se observó ningún reintento**: el log
de `uvicorn` muestra exactamente una línea `HTTP Request: POST
https://api.openai.com/...` por cada llamada lógica esperada (1 o 2,
nunca más), sin los saltos de 1s/2s/4s que un backoff dejaría en los
timestamps. Las mediciones de Paso 1 reflejan latencia real de
llamada única, no reintentos ocultos.

---

## 8. Contraste contra RFC/ADR — antes de clasificar cualquier cosa como defecto

- **RFC-0002 §"Ocho capacidades"** (`docs/architecture/RFC-0002-domain-model.md:143-152`):
  fija explícitamente que Orientar lee "diagnóstico" y Remediar lee
  "evidencia de no-aprendizaje" — el orden secuencial diagnosticar→
  remediar/orientar es parte del contrato de capacidades, no una
  decisión de implementación libre de revisar sin tocar el RFC.
- **RFC-0006 §5** (citado en `walkthrough.py:316-321`, "el orden de los
  chequeos ES el programa pedagógico" — "el mapa se completa antes de
  proponer"): confirma que el orden de `enrutar()` es intencional y
  ya fue objeto de una decisión arquitectónica propia (no una
  coincidencia del código).
- **P12/P13** (principios constitucionales citados en `walkthrough.py:306,372`):
  `enrutar()` debe seguir siendo una función pura de `(estado,
  política)` — cualquier cambio que introdujera paralelismo tendría
  que preservar esa pureza y no convertir el ruteo en una decisión
  externa al estado.

**Ninguna de las dos llamadas secuenciales observadas contradice
ningún RFC/ADR — al contrario, ambos las exigen explícitamente.**
Clasificar el patrón "2 llamadas secuenciales" como un defecto de
implementación sería incorrecto: es el comportamiento que la
arquitectura aprobada requiere.

---

## Clasificación final (para Paso 3 — no decidida aquí)

| Candidato | Tipo | ¿Contradice RFC/ADR? | ¿Optimizable sin tocar arquitectura? |
|---|---|---|---|
| Latencia de una sola llamada LLM (~2-4s) | Coste inevitable del proveedor | No aplica | No investigado (modelo/prompt fuera de alcance de este documento) |
| Secuencia diagnosticar→remediar/orientar | Decisión arquitectónica deliberada (RFC-0002, RFC-0006) | **No** — la arquitectura la exige | **No** — paralelizarla violaría el contrato de lectura de las capacidades |
| Llamadas redundantes/duplicadas | — | — | **No se encontraron** — no hay candidato |
| Reintentos/timeouts inflando la medición | — | — | **Descartado** — no ocurrieron en la muestra |

**No hay una optimización de "quick win" en la capa de ruteo del
Runtime.** El único margen real que este documento deja abierto para
Paso 3 (sin decidir ni implementar aquí) es evaluar el proveedor/modelo
LLM en sí (p. ej. streaming, un modelo más rápido, reducir el tamaño
del prompt) — nunca la secuencia de capacidades, que es arquitectura
aprobada, no una implementación a optimizar.

## Estado al cierre de Paso 2

Los 8 puntos pedidos quedan respondidos con evidencia de código y de
documento, no con suposiciones. Ningún archivo de código modificado.
Paso 3 (clasificar qué merece optimización real, dado que la causa
arquitectónica principal resultó no ser optimizable sin romper RFC-0002/
RFC-0006) queda pendiente de apertura explícita.
