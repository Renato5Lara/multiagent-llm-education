# MODELO DE EVOLUCIÓN PEDAGÓGICA — de estático a gobernado por el runtime

**Documento 2 de la Arquitectura Pedagógica v1.0.** Estado: cerrado, sin enmiendas
posteriores. Puente entre la Auditoría ([01-AUDITORIA.md](01-AUDITORIA.md)) y la
Constitución ([03-CONSTITUCION-PEDAGOGICA.md](03-CONSTITUCION-PEDAGOGICA.md)).

Sin interfaz. Sin código. Sin CSS. Responde una sola pregunta: qué debe dejar de ser
estático para que el runtime gobierne la experiencia sin romper la arquitectura
existente — y, donde no hay certeza, lo señala como pregunta abierta en vez de
inventarlo.

---

## 0. El hallazgo que organiza todo este documento

**El runtime ya gobierna una superficie completa de la experiencia — el contenido
dentro de un módulo — a través de exactamente un mecanismo:** `decision_adaptativa()`
(`runtime_bridge.py:206-288`) traduce la `Entrega` vigente del runtime (una decisión
de Adaptar: modalidad + profundidad) en `content_order`, `emphasis_topics` y
`skip_hint_topics`.

Ese mecanismo funciona, está probado, y respeta la regla de oro de RFC-0010:
*"traducción, jamás interpretación"*.

Casi ningún elemento estático necesita un concepto nuevo del runtime. Necesita el
mismo mecanismo, aplicado a superficies donde hoy nadie lo llama.

---

## 1. El precedente que se repite: `Entrega` como fuente de verdad

```
runtime decide (Adaptar/Validar producen un claim/veredicto)
    ↓
Boundary consulta el estado vigente (consultar_entrega_vigente / consultar_estado)
    ↓
Boundary TRADUCE eso a una forma que una superficie del producto entiende
    ↓
el producto la muestra — nunca decide nada por su cuenta
```

---

## 2. Clasificación de los elementos estáticos

### CATEGORÍA A — Wiring puro (cero conceptos nuevos)

**A1. Estado de desbloqueo de módulos.** Hoy calculado una vez desde el pre-test
(umbral fijo ≥75%). El asunto `"siguiente-paso(sesion)"` ya responde, por competencia,
la misma pregunta. Evolución: releer la decisión vigente por competencia cada vez que
cambia, traduciéndola a estado de desbloqueo — sin concepto nuevo en el runtime.

**A2. El veredicto de cierre de misión.** Validar ya produce el veredicto real
(`funciono: bool`). Evolución: exponerlo vía una superficie nueva de
`boundary/surfaces/`, siguiendo el patrón ya existente.

**A3. Evidencia del sandbox.** `registrar_evidencia_evaluacion()` ya acepta
`items_incorrectos`/`items_totales` de cualquier instrumento. Un ejercicio de código
con N casos de prueba es estructuralmente idéntico a un MCQ con N ítems. Cero cambios
en `backend/runtime/`.

**A4. Señal conductual de Tutorizar sin uso proactivo.** El patrón de superficie "algo
pendiente" ya existe (`escaladas_pendientes.py`). Una superficie más del mismo tipo,
sin que el runtime cambie nada.

### CATEGORÍA B — Decisión de política, no de diseño

**B1. Confianza reforzable/decayente (política v1 → v2).**
`POLITICAS: dict[str, Politica]` ya está diseñado para admitir una `"v2"` con pesos
reales. No es "estático → dinámico" en el mismo sentido que A1-A4 — es una decisión
de si conviene activarlo, dado que los productores de regla actuales tienen
confianzas fijas.

### CATEGORÍA C — Posible concepto nuevo: pregunta abierta, no decisión

**C1. ¿"Siguiente módulo" es el mismo asunto que "siguiente-paso(sesion)", o es un
grano distinto?** *(Resuelta por el usuario en la Constitución — ver PP2: es la misma
decisión, a mayor escala. Progreso entre módulos emerge del dominio de las
competencias que los componen.)*

**C2. ¿La agregación de varios veredictos de Validar en un solo "veredicto de misión"
es traducción o interpretación?** *(Resuelta por el usuario en la Constitución — ver
PP3: es síntesis/agregación transparente, renombrada "Síntesis Pedagógica de la
Misión".)*

---

## 3. Respuesta directa a la pregunta central

Cuatro superficies (A1-A4) pueden pasar de estáticas a gobernadas por el runtime hoy
mismo, sin ningún concepto nuevo — solo completando el mismo patrón de traducción que
`decision_adaptativa` ya demostró que funciona. Una superficie (B1) es una decisión de
política ya prevista en el código, pendiente de una precondición. Dos preguntas (C1,
C2) no tenían respuesta en este documento — se resolvieron después, con autoridad del
usuario, al escribir la Constitución.

## 4. Lo que este documento deliberadamente no decidió

No decidió si C1/C2 requerían RFC nuevo — solo que la pregunta existía. No decidió si
B1 debía ir antes o después de resolver C1/C2. No propuso ninguna interfaz, evento,
tabla ni nombre de superficie definitivo. No estimó esfuerzo ni priorizó entre A1-A4.

## 5. Recomendación de orden (cumplida)

Se recomendó que el usuario resolviera C1 y C2 antes de escribir la Constitución —
así ocurrió; ver PP2 y PP3 en
[03-CONSTITUCION-PEDAGOGICA.md](03-CONSTITUCION-PEDAGOGICA.md).
