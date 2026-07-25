# Auditoría — Épica B (Entorno de Programación del Estudiante)

> Documento de auditoría, no de diseño. Responde únicamente "¿cómo
> funciona hoy el sistema?", verificado contra el código real (y, en el
> punto 4, contra un recorrido real en navegador). **No contiene
> propuestas de solución, componentes nuevos, RFC ni código.** El
> alcance real de Épica B y su roadmap se deciden después de esta
> auditoría, no antes.

- **Fecha:** 2026-07-24
- **Motivo:** cierre de RFC-0011 (Generación de Recursos Pedagógicos);
  el tesista pidió abrir Épica B (editor, consola, `input()`, ejecución
  y simulación) con el mismo orden que funcionó ahí — auditoría del
  código real antes de proponer arquitectura.
- **Método:** tres auditorías de código en paralelo (flujo frontend de
  ejecución Python, sandbox backend, documentación arquitectónica
  previa) más un recorrido real en navegador durante la validación de
  RFC-0011/3 (mismo día). Todas las citas de archivo:línea provienen de
  lectura directa del código, no de inferencia.

---

## 1. Flujo de ejecución actual

**¿Qué componentes intervienen desde "Ejecutar" hasta el resultado?**

`frontend/src/components/experience/PythonBridge.tsx` → hook
`frontend/src/hooks/usePyodide.ts` → Pyodide (WebAssembly, cargado por
`<script>` desde CDN `cdn.jsdelivr.net/pyodide/v0.26.2/full/`,
`usePyodide.ts:9-10,26-38`). `handleRun` (`PythonBridge.tsx:289-322`)
llama `run(code, stage.simulatedInputs)`. El resultado se compara
contra `stage.expectedOutput` (`PythonBridge.tsx:297`, comparación
exacta de string — confirmado en vivo durante RFC-0011/3: "Frio" sin
tilde falló contra "Frío" con tilde).

**¿Dónde se ejecuta realmente el código?**

100% en el navegador del estudiante, vía WebAssembly (Pyodide es
CPython real compilado a WASM, no un intérprete simplificado). Cero
llamadas de red para ejecutar la práctica interactiva — no hay ningún
`api.post` desde este flujo hacia el backend.

**¿Qué parte es simulación y qué parte es ejecución real?**

La ejecución del código Python es real (Pyodide/CPython genuino). Lo
simulado es exclusivamente la **entrada** que recibe `input()` — nunca
la ejecución en sí.

Existe además un **sandbox de ejecución real en el backend**
(`backend/app/sandbox/`, corre en contenedores Docker aislados,
funcional) — pero está completamente desconectado del flujo del
estudiante (ver §3 y §4).

---

## 2. Tratamiento de `input()`

**¿Cómo se detecta actualmente?**

No hay detección dinámica del código del estudiante. El autor del
contenido pedagógico declara estáticamente, por cada peldaño que use
`input()`, un arreglo `simulatedInputs: string[]`
(`frontend/src/types/moduleExperience.ts:296-303`). No hay ningún
análisis del código en tiempo de ejecución que cuente cuántas veces
aparece `input(`.

**¿Dónde se inyectan los valores?**

`usePyodide.ts:104-108`:
```js
py.setStdout({ batched: (output) => lines.push(output) })
if (stdinValues && stdinValues.length > 0) {
  let cursor = 0
  py.setStdin({ stdin: () => (cursor < stdinValues.length ? stdinValues[cursor++] : '') })
}
```
Es una cola FIFO de strings precargados, consumida en el orden en que
el código llama a `input()`. `PythonBridge.tsx:372-386` muestra ese
valor al estudiante ANTES de ejecutar ("Simularemos que el usuario
escribe: …") — decisión de transparencia ya presente en el código
(comentario, `PythonBridge.tsx:372-374`): *"input() no tiene terminal
real en el navegador: en vez de ocultar el valor simulado, se muestra
explícitamente."*

**¿Qué limitaciones tiene el mecanismo actual?**

- El valor está fijado en tiempo de autoría del contenido, no en
  tiempo de ejecución — el estudiante nunca escribe el dato que
  recibirá su propio `input()`.
- Si el código llama a `input()` más veces que elementos tiene el
  arreglo, la cola devuelve `''` (string vacío) en silencio — no falla,
  no espera, no avisa.
- Sin `simulatedInputs`, cualquier `input()` real lanza `OSError`
  (comentado explícitamente en `usePyodide.ts:97-99`: *"Sin este
  parámetro, `input()` falla con OSError (sin stdin conectado)"*).
- El sandbox Docker del backend (el único lugar donde SÍ correría
  ejecución real con stdin real) bloquea `input` como llamada
  prohibida en ambas implementaciones de política (`policy.py` y
  `ast_policy.py`, ver §3) — está impedido incluso si algún día se
  conectara al estudiante.

**¿Qué componentes dependen de este comportamiento?**

`PythonBridge.tsx` (UI del mensaje "Simularemos…"), `usePyodide.ts`
(mecanismo), `PythonMicroPracticeDef.simulatedInputs` (tipo,
`moduleExperience.ts`), y el único contenido real que lo usa hoy:
`frontend/src/lib/experiences/module1/ciclo3-input.ts` (seis peldaños
encadenados — observar, manipular, completar, corregir,
escribir-con-andamiaje, escribir-sin-andamiaje — todos con
`simulatedInputs` fijo, p. ej. `['Ana']`, `['Nico']`, `['20']`).
`frontend/src/lib/experiences/conceptPrimers.ts` solo tiene un ejemplo
de texto no ejecutable (`INPUT_PRIMER`), no usa el mecanismo.

---

## 3. Arquitectura del entorno — componentes y responsabilidades

| Componente | Ubicación | Responsabilidad real |
|---|---|---|
| Editor | dentro de `PythonBridge.tsx` | edición inline del código del peldaño actual, sin pantalla completa |
| Consola/salida | dentro de `PythonBridge.tsx` (estado `output`/`error`) | no es un componente separado ni reutilizable |
| Ejecución | `usePyodide.ts` | Pyodide/WASM, 100% cliente |
| Validación | `PythonBridge.tsx:297` | comparación exacta de string contra `expectedOutput` |
| PythonBridge (orquestador) | `PythonBridge.tsx` | encadena los "stages" de una micropráctica dentro de `ModuleExperienceView.tsx` |
| Sandbox Docker #1 — `SandboxRunner` | `backend/app/sandbox/runner.py` + `policy.py` | el que SÍ usa el router HTTP `POST /api/sandbox/execute*` — **sin autenticación** (ningún `Depends` de usuario en `sandbox.py`) |
| Sandbox Docker #2 — `SandboxExecutor` | `backend/app/sandbox/executor.py` + `docker_manager.py` + `ast_policy.py` | implementación paralela e independiente, **sin ningún llamador HTTP** — solo un benchmark y un test de ataque |
| `SandboxValidationPanel.tsx` | `frontend/src/components/swarm/` | consume eventos SSE de la demo del swarm (`useDemoSSE.ts`) — no llama a ningún endpoint de sandbox |

**Quién invoca realmente `SandboxRunner` (el único con router HTTP, aunque no vía HTTP):**
- `ReviewerAgent.review_until_validated` (`backend/app/services/reviewer_agent.py`) —
  valida código **generado por IA** para ejemplos de contenido, nunca código de un estudiante.
- `SwarmDemoOrchestrator` (`backend/app/demo/orchestrator.py`) — demo visual del swarm con
  estudiante/módulo **sintéticos**, emite eventos SSE que `SandboxValidationPanel.tsx` consume.
- Generación de plan semanal docente (`weekly_pedagogy_service.py` → `PedagogicalOrchestrationService`) —
  flujo del **docente**, no del estudiante en vivo.

Ambas políticas AST (`policy.py`, `ast_policy.py`) son implementaciones
independientes y pueden divergir; ambas bloquean `input` explícitamente
como llamada prohibida.

---

## 4. Experiencia del estudiante — flujo real reconstruido

Recorrido verificado en navegador real (misma sesión de validación de
RFC-0011/3, cuenta de validación E2E existente):

```
Concepto (tarjetas explicativas, a veces infografía si el perfil es visual)
   ↓
Práctica (ordenar pasos, con 3 niveles de pista escalonada — "apoyo")
   ↓ (si el ciclo trae pythonBridge)
   Peldaños Python encadenados:
   Observa código ya resuelto → Ejecutar
   → Cambia un detalle → Ejecutar
   → Completa el código (hueco) → Ejecutar
   → Encuentra y corrige un error → Ejecutar
   → Escríbelo tú (con andamiaje) → Ejecutar
   → Profundiza (sin andamiaje, desde cero) → Ejecutar
   ↓
Consolidar (el sistema decide "reforzar" o "ya dominas esto — reto")
```

**Dónde el comportamiento actual deja de parecerse a un entorno real de
programación:** exactamente en `input()`. El mensaje "Simularemos que
el usuario escribe: …" aparece siempre ANTES de ejecutar, y ese valor
nunca lo escribe el estudiante — borra la distinción entre un dato fijo
(`edad = 20`) y un dato pedido al usuario (`edad = int(input(...))`),
que es precisamente el concepto que ese ciclo (`ciclo3-input.ts`)
pretende enseñar. El propio código es consciente de la limitación
(comentarios explican el porqué), pero el efecto pedagógico observado
es el mismo que motivó esta auditoría.

---

## 5. Restricciones técnicas

**Desacoplado / fácil de extender:**
- `usePyodide.ts` es un hook aislado con una interfaz pequeña y limpia
  (`run(code, stdinValues)`) — cualquier evolución del mecanismo de
  `input()` es técnicamente local a este hook + `PythonBridge.tsx`, sin
  tocar `backend/runtime/`, el Boundary, ni ningún RFC/ADR (§ siguiente).
- `POST /cycle-evidence` (RFC-0011 y anteriores) solo recibe agregados
  (`attempts`, `solved`, `hints_used`, `time_ms`) — no depende de CÓMO
  se ejecutó el código del estudiante, solo del resultado.

**Muy acoplado / riesgo de romper:**
- La validación por comparación exacta de string (`expectedOutput`)
  está fuertemente acoplada al contenido ya autorado — cualquier
  cambio en cómo se presenta la salida (p. ej. mostrar el prompt de
  `input()` dentro del propio stdout) puede romper ejercicios
  existentes si no se recalibra.
- El contenido pedagógico (`ciclo3-input.ts` y cualquier ciclo similar
  futuro) está acoplado a la forma actual de `simulatedInputs` —
  migrar el mecanismo de entrada implica re-autorar contenido, no solo
  cambiar código.

**Decisiones arquitectónicas previas que limiten esta evolución:**
Ninguna. Búsqueda exhaustiva en `docs/architecture/*.md` (RFC-0000 a
RFC-0010, ADR-0001 a ADR-0010, FOUNDATIONAL_PRINCIPLES.md,
BLUEPRINT.md, VOCABULARY.md): sin menciones a sandbox, consola,
editor, REPL, stdin, `input()`, PythonBridge o Docker. Las únicas
menciones adyacentes son RFC-0003 H5 y RFC-0007 H5 (adoptada), sobre
**cómo se registra en la provenance** que una evidencia vino de
"ejecución de código" — no restringen el mecanismo de ejecución en sí.

**Afordancia ya existente y no usada:**
`docs/architecture/pedagogical/02-MODELO-EVOLUCION.md:57-60` (A3) ya
declara que `registrar_evidencia_evaluacion()` acepta
`items_incorrectos`/`items_totales`, y que un ejercicio de código con N
casos de prueba es estructuralmente idéntico a un MCQ con N ítems —
"cero cambios en `backend/runtime/`". Si algún día se decide conectar
el sandbox Docker real (ejecución real, no solo edición en el
navegador) al flujo del estudiante, ya existe un canal de evidencia
preparado.

---

## 6. Hallazgos, clasificados

**Hecho confirmado por el código:**
- El `input()` en la práctica interactiva del estudiante siempre es
  simulado vía `simulatedInputs`; nunca se escribe en vivo.
- La ejecución de Python en la práctica del estudiante es 100%
  cliente, vía Pyodide (WASM real) — cero llamadas al backend.
- Existen dos sandboxes Docker en el backend, funcionales, y ninguno
  conectado al flujo del estudiante.
- El endpoint HTTP `POST /api/sandbox/execute*` no tiene autenticación.
- Ambos sandboxes bloquean `input` como llamada explícitamente
  prohibida — no soportarían `input()` aunque se conectaran hoy.
- No existe ningún RFC/ADR que gobierne el entorno de programación.
- El hallazgo "sandbox huérfano del flujo del estudiante" ya estaba
  documentado en `pedagogical/01-AUDITORIA.md` antes de esta sesión.
- `registrar_evidencia_evaluacion()` ya acepta una estructura
  compatible con evidencia de sandbox, sin cambios en el runtime.

**Hipótesis (no verificadas directamente en esta auditoría):**
- Si Pyodide admite un `stdin` genuinamente interactivo (una función
  que pause la ejecución hasta que el estudiante escriba, no solo un
  callback síncrono sobre un arreglo precargado) — no se probó código
  real para esto; habría que verificarlo antes de comprometerse a
  cualquier diseño que lo asuma.
- El comportamiento de "string vacío si se piden más inputs de los
  disponibles" se infiere del código, no se ejecutó un caso real que
  lo dispare.

**Riesgo:**
- Endpoint de sandbox sin autenticación expuesto — independiente de
  Épica B, es una superficie de seguridad real que ya existe hoy,
  fuera del alcance de esta auditoría pero registrada para no perderla.
- Dos implementaciones de política AST independientes
  (`policy.py`/`ast_policy.py`) que pueden divergir en qué bloquean.
- Contenido pedagógico fuertemente acoplado a la forma actual de
  `simulatedInputs`.
- Validación por comparación exacta de string, ya observada rompiendo
  por un simple acento ("Frio" vs "Frío") durante un recorrido real.

**Oportunidad:**
- El desacoplamiento real de `usePyodide.ts` permite evolucionar el
  mecanismo de `input()` sin tocar el Runtime, el Boundary ni ningún
  RFC/ADR — misma disciplina que funcionó en RFC-0011 (extender en vez
  de crear un subsistema nuevo).
- La afordancia ya existente en `registrar_evidencia_evaluacion()`
  deja un canal listo si además se decidiera conectar el sandbox
  Docker real al flujo del estudiante.
- Al no existir ningún RFC/ADR previo sobre esta área, Épica B puede
  diseñarse con hoja en blanco arquitectónica real — sin el riesgo de
  "reabrir" nada congelado, a diferencia de RFC-0011 (que sí tuvo que
  verificar cuidadosamente los límites de la Arquitectura Pedagógica
  v1.0 y RFC-0002 §3).

---

## Próximo paso

Esta auditoría no decide el alcance de Épica B. Con esto en mano,
corresponde al tesista decidir qué parte del problema se aborda
primero (¿solo `input()` interactivo dentro de Pyodide? ¿conectar el
sandbox Docker real? ¿ambos? ¿ninguno todavía?) antes de redactar
cualquier roadmap.
