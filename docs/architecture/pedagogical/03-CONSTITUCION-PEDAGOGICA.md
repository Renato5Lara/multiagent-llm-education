# CONSTITUCIÓN PEDAGÓGICA ADAPTATIVA — UPAO-MAS-EDU

**Documento 3 de la Arquitectura Pedagógica v1.0.** Estado: cerrado (v3 — PP0 y PP8
añadidos; PP6 ampliado con la cláusula de continuidad cognitiva).

**Relación con la Constitución del Runtime (P1-P17,
[FOUNDATIONAL_PRINCIPLES.md](../FOUNDATIONAL_PRINCIPLES.md)):** no la reemplaza ni la
modifica. La complementa en la capa pedagógica — el runtime ya rige *cómo se decide*;
este documento rige *qué evidencia alimenta esa decisión* y *cómo esa decisión se
convierte en experiencia*. Sus principios se citan como **PP0-PP8** para no
colisionar con la numeración del runtime.

---

## PARTE I — PRINCIPIO FUNDACIONAL

### PP0. Principio de Evidencia Continua

> **El modelo del estudiante nunca se considera definitivo. Toda interacción
> constituye evidencia potencial que puede confirmar, refinar o refutar las
> hipótesis actuales del runtime. Ninguna decisión adaptativa depende
> exclusivamente del Pre-Test — este solo aporta la evidencia inicial de una
> cadena que no se cierra mientras la sesión, o el curso, continúa.**

Es el principio del que dependen todos los demás.

**Ya parcialmente cumplido, con un límite exacto y conocido:** Diagnosticar
reinterpreta cada hecho evaluativo nuevo individualmente, no una vez por sesión
(`diagnosticar/productor.py:29-35`), y la cascada de `enrutar()` re-propone y
re-decide cuando la evidencia corrige el paisaje (`walkthrough.py:267-277`). El
**estado** del runtime ya es continuo en este sentido.

Lo que todavía no cumple PP0 del todo: la **confianza** sobre esas interpretaciones
no se mueve con la evidencia — la política v1 la mantiene fija (ver PP7). PP0 es la
razón pedagógica por la que activar una política con confianza reforzable/decayente
(Categoría B del Modelo de Evolución) no es una mejora técnica opcional, sino la
finalización de un principio ya declarado como fundacional.

---

## PARTE II — PRINCIPIO RECTOR

### PP1. El runtime decide; el Boundary traduce y agrega; nadie más decide.

> *El runtime es el único que toma decisiones pedagógicas. El Boundary nunca
> decide; únicamente traduce y agrega información para que el frontend la
> presente al estudiante.*

Ya demostrado en código (`decision_adaptativa`, `runtime_bridge.py:206-288`), ahora
declarado como regla general. Ninguna pieza de producto tiene autoridad pedagógica
propia — solo ejecuta o presenta lo que el runtime, alimentado por PP0, ya concluyó.

---

## PARTE III — PRINCIPIOS DE AGREGACIÓN

### PP2. Principio de Progresión Modular

> **El progreso entre módulos emerge del dominio de las competencias que lo
> componen. No existe una decisión de runtime independiente para "desbloquear
> el módulo siguiente".**

Cuando todas las competencias de un módulo alcanzan un veredicto de Validar
positivo, el módulo se considera consolidado y el Boundary traduce eso a
desbloqueo. **Límite explícito:** deja de ser válido si en el futuro se incorpora
carga cognitiva, tiempo recomendado o dependencias curriculares cruzadas — en ese
momento correspondería un concepto de runtime propio, vía RFC.

### PP3. Principio de Síntesis Pedagógica

> **El cierre de una misión no es un veredicto nuevo — es una síntesis
> transparente de los veredictos que Validar ya produjo por competencia. Se
> llama "Síntesis Pedagógica de la Misión", nunca "Veredicto del Evaluador".**

Corrige el hallazgo de auditoría (`evaluatorVerdict` como plantilla cliente-side que
impostaba ser un agente). **Límite explícito:** si la síntesis empezara a estimar
preparación global o a generar memoria pedagógica por sí misma, dejaría de ser
agregación y necesitaría una capacidad real del runtime.

---

## PARTE IV — PRINCIPIOS DE EXPERIENCIA

### PP4. Principio de Traducción Obligatoria

> **Ninguna decisión adaptativa del runtime puede llegar al estudiante sin
> traducirse en una experiencia pedagógica concreta.**

Catálogo de formas reconocidas (no cerrado): ejemplo adicional, animación/
visualización, reto más pequeño, pista progresiva, código guiado, narración del
tutor. La señal de Tutorizar (fluidez/confusión/frustración) es el caso hoy sin
traducción — existe el dato, no la forma.

### PP5. Principio de No-Repetición de Forma

> **Un refuerzo nunca repite la misma forma de contenido que ya resultó
> insuficiente en el intento anterior.**

Ya parcialmente implementado: `ALTERNATIVAS_POR_SENAL` (`adaptar/productor.py:75-91`)
descarta explícitamente alternativas según la señal conductual — hoy vive como
metadato sin consumir en el frontend.

### PP6. Principio de Continuidad del Reto (v3 — ampliado)

> **El estudiante no debe percibir que una actividad terminó y otra comenzó.
> Debe percibir que el mismo reto evolucionó. Cada transición debe preservar el
> contexto mental del estudiante: la adaptación nunca debe obligarlo a
> reconstruir innecesariamente el problema que estaba resolviendo — debe
> sentirse como una continuación natural del mismo desafío, no como un
> reinicio.**

Se aplica en tres escalas:

- **Narrativa:** un refuerzo insertado no reinicia el indicador de progreso; el
  desbloqueo de un módulo se presenta como consecuencia, no como comienzo (PP3 es el
  puente).
- **Cognitiva:** la forma que tome una adaptación (PP4) no debe forzar al estudiante
  a soltar el problema que tenía en la cabeza y volver a armarlo desde cero. Da un
  criterio evaluable, no solo narrativo: abrir un modal, cambiar de pantalla
  completa, reiniciar el editor, o saltar a un ejercicio sin relación aparente
  rompen PP6 aunque la decisión pedagógica detrás sea acertada — porque el costo de
  reconstrucción mental cae sobre el estudiante, no sobre el sistema.
- **Del propio lenguaje visual, a lo largo del tiempo** (ver Documento 7 §1): la
  consistencia semántica de los recursos visuales es, en última instancia, una
  extensión de esta misma cláusula cognitiva.

**Prueba de cumplimiento:** si un estudiante no puede explicar, al recibir un
refuerzo, *por qué* el sistema se lo dio — a partir de lo que él mismo hizo, no de
una plantilla genérica — PP6 no se cumplió, sin importar cuán fluida se vea la
transición visualmente.

### PP7. Principio de Proporcionalidad

> **La intensidad de la experiencia debe ser proporcional a la confianza y
> urgencia de la decisión que la origina — nunca uniforme.**

Declarado pero no activable hoy: bajo v1 toda decisión tiene esencialmente la misma
fuerza (confianza fija 0.75-0.82). Queda esperando a que PP0 se cumpla del todo
(política v2).

### PP8. Principio de Progresión Constructiva

> **Toda adaptación debe acercar al estudiante al dominio de una competencia.
> Ninguna intervención adaptativa existe únicamente para repetir contenido o
> aumentar el tiempo de permanencia. Cada ejemplo, pista, práctica o
> explicación debe tener un propósito observable dentro de la progresión hacia
> el dominio.**

Coherente con lo que el runtime ya hace en su núcleo: Remediar y Orientar solo
proponen dos acciones, "reforzar" y "avanzar-con-andamiaje" — ambas orientadas hacia
adelante. PP8 complementa a PP5: PP5 exige variedad de *forma*; PP8 exige que,
además de variar, cada forma tenga intención de avance.

**Tensión abierta que PP8 hace visible, sin resolverla aquí:** el sistema de pistas
escalonadas hoy revela la solución completa al tercer intento
(`OrderingPractice.tsx`). Eso resuelve el bloqueo inmediato, pero cabe preguntar si
"revelar la respuesta" cuenta como progresión hacia el dominio o como un atajo que
lo evita. PP8 da el criterio para juzgarlo — no lo juzga por adelantado.

---

## PARTE V — ALCANCE Y LÍMITES

No especifica componentes de React, animaciones concretas ni paleta visual (fase de
Traducción al Frontend). No decide si/cuándo activar la política v2. No introduce
ningún asunto, capacidad ni concepto nuevo en `backend/runtime/` — PP2 y PP3 son
deliberadamente agregación de Boundary, no runtime nuevo.

---

## PARTE VI — TRAZABILIDAD

| Principio | Origen |
|---|---|
| PP0 | Petición explícita del usuario — "el diagnóstico nunca termina", elevado a principio fundacional |
| PP1 | Formulación literal del usuario |
| PP2 | Decisión del usuario sobre C1 (Modelo de Evolución Pedagógica) |
| PP3 | Decisión del usuario sobre C2, incluyendo el renombre a "Síntesis Pedagógica de la Misión" |
| PP4 | Hallazgo de auditoría: señal de Tutorizar sin traducción experiencial |
| PP5 | Código ya existente: `ALTERNATIVAS_POR_SENAL`, `adaptar/productor.py:75-91` |
| PP6 | Visión repetida por el usuario ("el reto evolucionó, no terminó"); ampliado con la cláusula de continuidad cognitiva y su extensión al lenguaje visual (Doc 7 §1) |
| PP7 | Hallazgo de auditoría: política v1 con confianza uniforme |
| PP8 | Petición explícita del usuario — evitar adaptación como "más de lo mismo" |
