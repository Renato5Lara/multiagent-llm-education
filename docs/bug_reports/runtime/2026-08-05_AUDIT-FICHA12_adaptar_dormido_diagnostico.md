# Ficha 12 — Diagnóstico de "Adaptar dormido"

## Metadata

- **Fecha:** 2026-08-05
- **Rama:** `feat/confidence-calibration-remediation-orientation`
- **Protocolo pedido (Fase 4):** (1) confirmar qué significa exactamente
  "Adaptar dormido"; (2) encontrar la evidencia original del hallazgo
  HF-0/Exp-1; (3) determinar si sigue vigente después de la migración a
  LangGraph Runtime; (4) clasificar: problema real actual / comportamiento
  esperado / deuda experimental / hallazgo superado por arquitectura
  nueva; (5) no implementar cambios hasta tener diagnóstico. **Ningún
  archivo de código modificado.**
- **Origen:** hallazgo colateral de HF-0 (auditoría de oportunidades
  Hugging Face, 2026-08-03), registrado en memoria como "hallazgo
  prioritario (P3, ficha futura separada)" — esta es esa ficha.

---

## 1. ¿Qué significa exactamente "Adaptar dormido"?

**No significa que el nodo `adaptar` no se ejecute.** Confirmado en
`backend/runtime/engine/graph/walkthrough.py:107-128`: `_decision_sin_adaptar`
rutea al nodo `"adaptar"` cada vez que hay una decisión activa sin diseño
todavía asignado — se ejecuta en **cada** sesión real que necesita
adaptación, sin excepción. El nodo está vivo y su lógica de regla
(`DISENO_POR_ACCION`) recibe mantenimiento activo y reciente (commits
`5c6c7ac`, `7fef752`, `1eaf4e5`, `e5b301a` — modalidad diagnosticada,
retroceso de profundidad ante frustración, gobierno de andamiaje por
señal, adaptación por nivel).

**Lo que está dormido es específicamente `producir_llm`** — la
implementación LLM de Adaptar existe (`backend/runtime/domain/adaptar/
productor_llm.py`), fue sondeada y corregida contra un proveedor real
(ADR-0007 §3.2, ver §2), pero **nunca se invoca en producción**. Cada
petición HTTP real construye el walkthrough sin pasarle un
`productor_adaptar` explícito, así que siempre cae al valor por defecto
del propio `walkthrough.py` — la regla, `producir_adaptacion`. Es
"dormido" en el sentido de "construido y validado, pero apagado en el
borde de producción" — no en el sentido de "código muerto" ni de "nodo
inalcanzable".

---

## 2. Evidencia original del hallazgo (HF-0/Exp-1, 2026-08-03)

Memoria `hf0_auditoria_exp1_huggingface_cerrado_2026_08_03.md`:

> "de las 8 capacidades con `productor_llm.py`
> (diagnosticar/remediar/orientar/evaluar/modelar/tutorizar/validar/adaptar),
> solo **Diagnosticar, Remediar y Orientar** están conectadas al Boundary
> real (...); las otras 5 tienen su `producir_llm` probado contra OpenAI
> real en tests pero `engine/graph/walkthrough.py` nunca las recibe
> sobreescritas en producción — corren siempre en modo regla. Hallazgo no
> anticipado: **la decisión más relevante para la tesis (`Adaptar`:
> modalidad/profundidad/andamiaje, la única categórica genuinamente
> abierta) está dormida, no en vivo**"

Y la conclusión de cierre explícita del tesista, la misma fecha:

> "No se abre P3 (activar `Adaptar` en producción) — se registra como
> hallazgo prioritario para una ficha independiente futura, porque activar
> `Adaptar` es un cambio funcional/arquitectónico (capacidad dormida
> pasando a producción) y merece su propio Engineering Gate, distinto de
> un experimento de infraestructura de proveedor."

Esta ficha es esa "ficha independiente futura" — cumple el paso de
diagnóstico que esa decisión dejó pendiente, sin activar nada todavía.

---

## 3. ¿Sigue vigente después de la migración a LangGraph Runtime?

**Pregunta mal planteada por la premisa, y es importante decirlo así:**
no hay ninguna migración posterior que pudiera haber superado este
hallazgo. HF-0/Exp-1 **ya se produjo sondeando `backend/runtime/`
directamente** — el propio LangGraph Runtime, no BaseAgent ni ningún
mecanismo legacy. No existe una versión "antigua" de Adaptar que esta
migración haya reemplazado; `backend/runtime/domain/adaptar/` **es** la
única implementación que ha existido de esta capacidad.

Verificado hoy, en HEAD, con evidencia directa (no releída de memoria):

- `backend/runtime/boundary/inbound/productores.py` (el único lugar que
  decide qué implementación corre en producción) define
  `productor_diagnostico_activo()`, `productor_remediar_activo()`,
  `productor_orientar_activo()` — **cero mención de `adaptar`**, igual
  que hace dos días.
- Los dos únicos call-sites reales de `ejecutar_walkthrough` en el
  Boundary (`boundary/inbound/hechos.py:41-47`,
  `boundary/inbound/escalada.py:111-117`) pasan explícitamente
  `productor_diagnostico`, `productor_remediar`, `productor_orientar` —
  **nunca `productor_adaptar`** — así que siempre reciben el valor por
  defecto de `walkthrough.py` (la regla).
- `git log --since=2026-08-03` sobre `productores.py` y
  `domain/adaptar/` no muestra ningún commit — cero cambios en el
  período. Los commits recientes sobre Adaptar (`5c6c7ac`…`e5b301a`)
  mejoran la **regla**, no tocan la conexión al Boundary.

**Conclusión: el hallazgo sigue exactamente vigente, sin ninguna
variación.** No es un artefacto de una arquitectura superada — es una
propiedad actual y verificada de la arquitectura vigente.

---

## 4. Hallazgo adicional — ADR-0007 ya clasificó y validó Adaptar como CLAIM

No estaba en el HF-0 original, pero cambia la lectura del "por qué":
`ADR-0007-integracion-llm-productores-conocimiento.md` §3.2 (evidencia
CLAIM, 2026-07-11 — **un mes antes** de HF-0) ya sondeó `producir_llm`
de Adaptar contra un proveedor real y lo corrigió:

> "Adaptar | El modelo inventó una taxonomía de modalidad de ESTUDIO
> ajena al dominio — no una mala forma, un eje de razonamiento distinto |
> Corridas consecutivas sin vocabulario ajeno, enumerando explícitamente
> el vocabulario cerrado del dominio"

Es decir: la implementación LLM de Adaptar no es un spike sin terminar —
**pasó por el mismo proceso de validación empírica que Diagnosticar,
Remediar y Orientar**, con su propia corrección de deriva semántica ya
aplicada y documentada. Lo mismo aplica a Validar y Modelar (también en
la tabla CLAIM de ADR-0007, también ausentes de `productores.py`) — el
patrón "validado pero no conectado" no es exclusivo de Adaptar, aunque
Adaptar sea el caso pedagógicamente más relevante para la tesis (la
única decisión categórica genuinamente abierta, según HF-0).

ADR-0007 clasifica **cómo** debe construirse el prompt de cada capacidad
(FACT vs. CLAIM) — no decide **cuáles** capacidades se conectan al
Boundary en producción. Esa segunda decisión (activar solo 3 de 6
capacidades CLAIM-validadas) no tiene un documento propio que la
declare cerrada — vive implícitamente en el historial de commits de
`fba188a`/`7b2551e` (Diagnosticar y Remediar/Orientar conectados) y en
la decisión de cierre de HF-0 citada en §2, que explícitamente pospuso
Adaptar a una ficha futura con su propio Engineering Gate.

---

## 5. Clasificación

Las tres hipótesis planteadas al abrir esta fase no describen con
precisión lo que la evidencia muestra — vale decirlo explícitamente en
vez de forzar el resultado dentro de una de las tres:

- **No es Caso A (bug real: "el sistema no re-adapta cuando cambia el
  perfil").** El nodo `adaptar` se ejecuta en cada sesión que lo
  necesita y sí reacciona a cambios de señal/perfil — solo que su
  razonamiento es siempre el de la regla (`DISENO_POR_ACCION`), nunca el
  del LLM. No hay ningún caso observado de adaptación que debiera
  ocurrir y no ocurre.
- **No es Caso C (superado por la migración a LangGraph Runtime).**
  Como se muestra en §3, el hallazgo nació sondeando el propio LangGraph
  Runtime — no hay una versión previa que esta arquitectura haya
  reemplazado.
- **Se acerca a Caso B (comportamiento esperado/limitación de diseño),
  pero con una precisión importante:** no es una limitación arquitectónica
  inherente (nada en RFC-0002/ADR-0007 prohíbe conectar Adaptar al
  Boundary — al contrario, ADR-0007 §3.2 ya validó que puede hacerse con
  seguridad). Es una **decisión de alcance explícita y ya cerrada por el
  tesista** el 2026-08-03: no activar una capacidad funcionalmente nueva
  como subproducto de un experimento de infraestructura de proveedor.

**Clasificación final: deuda experimental intencional, con decisión de
cierre ya registrada, pendiente de una activación futura que requiere su
propio Engineering Gate — no un defecto, no un huérfano de arquitectura,
no algo que deba corregirse silenciosamente aquí.**

Esto es consistente con la Cláusula de trazabilidad y el Engineering Gate
de CLAUDE.md: activar `producir_llm` de Adaptar en `productores.py`
introduciría un comportamiento ejecutable nuevo en producción (P1: "¿qué
decisión implementa?" no tiene todavía una respuesta con RFC/ADR propio
que autorice el paso de "validado" a "activo") — exactamente el tipo de
cambio que HF-0 ya decidió no tomar sin su propio Gate.

---

## 6. No se implementa ningún cambio en este documento

Confirmado: no se modificó `productores.py`, ni `walkthrough.py`, ni
ningún archivo de `domain/adaptar/`. El diagnóstico queda disponible
para cuando el tesista decida abrir el Engineering Gate de activación —
que debería responder, como mínimo: ¿qué mejora medible aporta la
versión LLM de Adaptar frente a la regla vigente (que ya recibe
mantenimiento activo y funciona)?, ¿qué RFC/ADR autoriza el cambio de
alcance?, ¿qué evidencia de tesis se fortalece?, siguiendo la misma
metodología de investigación (§METODOLOGÍA DE INVESTIGACIÓN, CLAUDE.md)
que gobierna cualquier otra funcionalidad nueva del sistema.
