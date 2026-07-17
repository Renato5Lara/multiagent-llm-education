# ADR-0007 — Estrategia de integración LLM para productores de conocimiento

- **Estado:** Aceptado (2026-07-11, Engineering Review — evidencia
  empírica de la fase de integración de proveedores LLM reales sobre
  las 8 capacidades de RFC-0002)
- **Fecha:** 2026-07-11
- **Preserva:** RFC-0002 §3 (modelo de capacidades), RFC-0003 §1/§3
  (asimetría fact/claim, INV-4/INV-5), ADR-0004 (E-2: respuesta
  incompleta del proveedor es defecto de programación, se propaga),
  ADR-0005 §3/§7 (guardián P13, dobles de LLM en unitarios), P12
  (determinismo arquitectónico), P13 (capacidades antes que agentes)
- **Criterio de aceptación:** antes de implementarse, toda nueva
  capacidad basada en LLM deberá identificar explícitamente si produce
  FACT o CLAIM según el tipo de sobre emitido por su reducer. La
  clasificación deberá justificarse mediante el contrato del dominio y
  verificarse posteriormente con evidencia empírica durante su
  integración con un proveedor real.

## 1. Contexto

La fase de integración de proveedores LLM reales sustituyó
`FakeLLMProvider` por `OpenAIProvider` en las 8 capacidades de
RFC-0002 y sondeó cada `productor_llm.py` contra un proveedor real
antes de tocar código. El hallazgo no fue solo que el prompt no
especificaba forma (eso ocurrió en las 8 capacidades): apareció un
patrón consistente sobre **qué puede legítimamente aportar el LLM**
según el tipo de dato que la capacidad produce. Ese patrón se probó,
no se asumió — cada capacidad se sondeó primero, se clasificó con
evidencia, y solo entonces se corrigió. La evidencia completa vive en
`§3 Evidencia`; esta sección solo motiva por qué existe el ADR.

Motivación adicional: los guardianes P13 (ADR-0005 §7) comparan la
versión regla contra la versión LLM usando `FakeLLMProvider`, que por
construcción espeja el resultado esperado. Las 8 capacidades pasaron su
guardián P13 en verde desde antes de esta fase — y las 8 fallaron igual
contra un proveedor real antes de su corrección. Este ADR deja
constancia de que ambas suites verifican propiedades independientes:
una no implica la otra (§3.3).

## 2. Decisión

### 2.1 Criterio de clasificación

El criterio que decide cómo debe implementarse `productor_llm.py` es
**el tipo de sobre que construye el reducer al que apunta** —
`registrar_fact` (produce `FactEntry`) o
`registrar_claim`/`validar_decision` (produce `ClaimEntry`) — nunca la
derivabilidad del valor que el LLM produce, ni el nombre o propósito
superficial de la capacidad. Un valor puede ser mecánicamente derivable
del estado (una comparación, una copia literal) y aun así pertenecer a
la estrategia CLAIM si el reducer construye un `ClaimEntry`: lo que
determina la estrategia es la naturaleza del sobre (RFC-0003 §1: fact
= observación objetiva; claim = interpretación respaldada), no la
complejidad del cálculo.

### 2.2 Estrategia para FACT — grounding

Aplica cuando el reducer construye un `FactEntry` (INV-4: sin `tipo`,
`asunto`, `respaldo` ni `confianza` — un fact no lleva esos campos
estructuralmente). El roundtrip (`ejecutar_roundtrip`) se ejecuta y se
valida, pero **su resultado se descarta deliberadamente**: el
`contenido` del fact se construye siempre con el cálculo determinista
que el productor ya hizo antes de invocar al proveedor. El LLM solo
verifica que el proveedor está disponible y responde con la forma
esperada — nunca es la fuente del dato registrado.

Justificación (RFC-0003 §1): *"un fact solo puede ser cuestionado por
un nuevo fact — nunca por una opinión"*. Sin grounding, el fact
registrado sería la opinión del modelo, no una observación objetiva —
contaminaría la historia inmutable (P14) con una alucinación
indistinguible de un hecho real.

### 2.3 Estrategia para CLAIM — regla o vocabulario explícito

Aplica cuando el reducer construye un `ClaimEntry` (`tipo`, `asunto`,
`respaldo`, `confianza` — RFC-0003 INV-5). El LLM sí puede ser la
fuente del veredicto o la propuesta, incluso cuando ese valor sea
mecánicamente derivable — porque el sobre conserva algo que un fact
estructuralmente no tiene: `confianza` declarada y `razonamiento`. La
condición para que esto sea seguro, y no una alucinación disfrazada de
interpretación, es que **el prompt declare explícitamente la regla o
el vocabulario cerrado del dominio** — nunca se asume que el modelo la
conoce ni que la infiere correctamente sin que se le diga.

### 2.4 Consecuencias normativas

- Toda capacidad LLM nueva, o modificación de una existente, se
  clasifica primero (FACT/CLAIM) contra el reducer que invoca, antes de
  escribir el prompt.
- Un productor FACT nunca debe usar `respuesta[...]` del roundtrip para
  construir `contenido` — solo para confirmar disponibilidad/forma.
- Un productor CLAIM nunca debe asumir que el modelo conoce el
  vocabulario o la regla del dominio sin declararla en el prompt.
- Toda capacidad LLM requiere dos suites de evidencia, no una: el
  guardián P13 (contrato estructural) y un test contra proveedor real
  (forma, semántica, vocabulario, estabilidad) — ver §3.3.

## 3. Evidencia

### 3.1 Evidencia FACT

Obtenida sondeando Evaluar y Tutorizar contra un proveedor real:

| Capacidad | Prompt sin declarar la regla | Corrección |
|---|---|---|
| Evaluar | Campo `total` en vez de `items_totales`; el modelo declaró `"conteo_correcto": false` sobre un conteo correcto | Roundtrip descartado; `contenido` = valores deterministas ya calculados |
| Tutorizar | Con `incorrectos=3, total=6` (la regla exige `"confusion"`), el modelo respondió `"frustracion"` — contradijo el umbral del dominio, no solo la forma; en otro caso devolvió `"frustration"`/`"fluency"` en inglés, fuera del vocabulario cerrado | Roundtrip descartado; `senal` = resultado de la regla siempre |

### 3.2 Evidencia CLAIM

Obtenida sondeando Diagnosticar, Remediar, Orientar, Validar, Modelar y
Adaptar contra un proveedor real:

| Capacidad | Sin la regla/vocabulario explícito | Con la regla/vocabulario explícito |
|---|---|---|
| Diagnosticar | Forma libre, sin campos exigidos | 100% correcto declarando el umbral de la regla |
| Remediar | Estructura anidada, campos fuera de la raíz exigida | 100% correcto restringiendo la acción al único valor de la regla |
| Orientar | El modelo emitía su propio juicio sobre si convenía avanzar — invadía la deliberación del Kernel | 100% correcto aclarando que la salida es propuesta, no decisión |
| Validar | No-determinismo real a `temperature=0`: el mismo prompt exacto produjo respuestas distintas en llamadas idénticas; además incorrecto cuando la decisión empeoró | Corridas consecutivas correctas y estables declarando la regla del dominio |
| Modelar | Estructura anidada inventada, sin los campos de la raíz exigida | Corridas consecutivas con el veredicto idéntico al de origen, sin reinterpretarlo |
| Adaptar | El modelo inventó una taxonomía de modalidad de ESTUDIO ajena al dominio — no una mala forma, un eje de razonamiento distinto | Corridas consecutivas sin vocabulario ajeno, enumerando explícitamente el vocabulario cerrado del dominio |

El caso de Validar es la evidencia más fuerte de por qué la regla debe
declararse siempre, incluso cuando "parece obvia": a `temperature=0`
sin la regla explícita, el proveedor no fue reproducible sobre el mismo
input exacto. `temperature=0` reduce la varianza; no la elimina por sí
sola — la reproducibilidad real vino de eliminar la ambigüedad del
prompt, nunca del parámetro de muestreo.

### 3.3 Aprendizaje metodológico

Los guardianes P13 y los tests contra proveedor real verifican
propiedades independientes; ninguna prueba de una implica la otra. Las
8 capacidades tuvieron su guardián P13 en verde antes de sondearse
contra un proveedor real, y las 8 fallaron igual contra el proveedor
real hasta corregirse. Toda capacidad LLM requiere ambas suites.

### Nota de procedencia

La evidencia de este ADR proviene de la fase de integración de
proveedores LLM reales del runtime (9 cambios incrementales, uno por
capacidad más la infraestructura compartida, identificados en el
historial de commits de `backend/runtime/domain/` y
`backend/tests/runtime/walkthrough/test_M3_PR*`). Se cita aquí como
referencia trazable, no como parte de la norma — el ADR debe poder
leerse y aplicarse aunque esos commits cambien de identificador.

## 4. Alternativas rechazadas

- **Grounding universal** (aplicar la estrategia FACT también a
  claims): rechazado — anularía el aporte legítimo del LLM
  (razonamiento, confianza) que el propio sobre de `ClaimEntry` existe
  para capturar; degradaría toda capacidad claim a ejecutar solo la
  regla, sin razón de ser para la versión LLM.
- **Confianza ciega en el LLM sin declarar la regla** (dejar que el
  modelo infiera el vocabulario o el criterio del dominio): rechazado
  — causó forma incorrecta y/o deriva semántica en las 8 capacidades
  sondeadas sin la regla explícita; el caso de vocabulario de modalidad
  de estudio demuestra que la deriva puede ser conceptual, no solo de
  forma.
- **Clasificar por el nombre o propósito superficial de la capacidad**
  (asumir que una capacidad "verificadora" debe tratarse como fact):
  rechazado con evidencia — el criterio correcto es el tipo de sobre
  que el reducer construye, no la intuición sobre qué "hace" la
  capacidad.
- **Un único patrón de prompt para todas las capacidades**: rechazado
  — el patrón claim requiere declarar una regla o un vocabulario
  cerrado de uno o más campos según cuántos controla el LLM; la forma
  exacta no es mecánicamente idéntica entre capacidades.

## 5. Consecuencias

- Toda capacidad LLM nueva debe pasar por la clasificación de §2.1
  antes de escribir su prompt, y cumplir el criterio de aceptación de
  este ADR.
- **Riesgo relacionado — "Prompt Drift":** quedaron tres fuentes de
  verdad para el mismo vocabulario de dominio — las tablas del código
  de dominio, el texto de cada prompt (hardcodeado por capacidad) y la
  documentación de vocabulario — sin ningún mecanismo que las mantenga
  sincronizadas. Este ADR identifica el riesgo de Prompt Drift, pero
  **deliberadamente no define el mecanismo de sincronización** entre
  tablas de dominio, prompts y documentación. Ese problema pertenece a
  otra decisión arquitectónica futura; este ADR solo lo registra.
- Ningún guardián P13 existente verifica vocabulario cerrado por
  pertenencia a un conjunto — dependen de que `FakeLLMProvider` espeje
  la regla por construcción. Extender esa verificación a los
  guardianes P13 estructurales queda fuera de este ADR.
- Los candidatos de refactor de implementación identificados durante
  esta fase (duplicación de guard clauses, del wrapper de intención de
  transición, del esqueleto de los dobles de proveedor) no son
  consecuencia de este ADR — son duplicación de implementación, no de
  estrategia de integración; quedan como deuda técnica de ingeniería
  ordinaria.
