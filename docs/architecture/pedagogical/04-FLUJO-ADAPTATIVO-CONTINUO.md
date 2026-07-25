# FLUJO ADAPTATIVO CONTINUO — UPAO-MAS-EDU

**Documento 4 de la Arquitectura Pedagógica v1.0.** Estado: cerrado.

**Regla de apertura (no negociable):** este documento no crea principios. Cada
afirmación aquí debe poder trazarse a un PP existente
([03-CONSTITUCION-PEDAGOGICA.md](03-CONSTITUCION-PEDAGOGICA.md)). Si aparece un vacío
que ningún PP cubre, se declara como tal y se detiene — no se resuelve ni se inventa
un PP nuevo sobre la marcha.

**Qué responde este documento:** la Constitución dice *qué* debe cumplirse. Este
documento dice *en qué momento, en qué orden y a qué escala* se cumple durante el
recorrido real de un estudiante — sin tocar todavía interfaz, componentes ni código.

---

## 1. La unidad atómica del flujo: el Ciclo

Todo lo que sigue se apoya en una sola unidad que ya existe en el producto
(`ModuleExperienceView.tsx`, fases `concept→practice→decision`) y que este documento
formaliza como la unidad mínima donde PP0-PP8 se cierran completos:

> **Un Ciclo es el recorrido completo de un hecho de evidencia, desde que se
> genera hasta que produce (o no) una adaptación observable.**

Un Ciclo no es una pantalla ni una actividad — es la distancia entre "el estudiante
hizo algo verificable" y "el sistema respondió con algo que él puede sentir". Un
módulo contiene varios Ciclos (uno por competencia relevante); una misión completa se
cierra cuando sus Ciclos convergen en la Síntesis (PP3).

**Todo Ciclo comienza con una intención pedagógica del estudiante, no con un dato.
La evidencia no aparece espontáneamente: surge como consecuencia de una acción
realizada para resolver un desafío. El runtime nunca adapta por la evidencia en sí
misma, sino por lo que esa evidencia revela sobre el proceso de aprendizaje del
estudiante que la produjo.**

Los ocho momentos que siguen describen qué hace el sistema con esa evidencia — no
reemplazan ni compiten con la intención que la originó; la presuponen.

---

## 2. Los ocho momentos de un Ciclo

Esta secuencia opera literalmente el orden ya cableado en `enrutar()`
(`walkthrough.py:261-312`) — no se inventa un orden nuevo, se nombra pedagógicamente
el que ya gobierna el runtime.

**Momento 1 — Apertura de evidencia.**
Un hecho entra al sistema: una respuesta de pre-test, un cycle-evidence de práctica,
(cuando se conecte) un resultado de sandbox. Opera **PP0**: esto nunca es "la última
palabra", es una entrada más a una cadena que no se cierra.

**Momento 2 — Interpretación.**
Diagnosticar (o Tutorizar, en paralelo, para la señal conductual) lee el hecho y
produce una hipótesis: dominado/no-dominado, fluidez/confusión/frustración. Sigue
siendo evidencia interna — todavía no le pertenece al estudiante.

**Momento 3 — Tensión pedagógica.**
Remediar propone reforzar; Orientar propone avanzar. Esto solo ocurre si hay
hipótesis suficiente. Si no hay tensión (una sola propuesta), se deriva decisión
directa — el Ciclo no se detiene esperando un rival que no existe.

**Momento 4 — Decisión.**
El consenso resuelve. Opera **PP1** en su forma más literal: nadie fuera del runtime
participa de esto — ni el Boundary, ni el frontend, ni una regla de producto.

**Momento 5 — Traducción a experiencia.**
Adaptar convierte la decisión en una categoría pedagógica concreta — hoy, modalidad y
profundidad; conceptualmente, cualquier dimensión que el catálogo de formas de PP4
reconozca (forma de interacción, nivel de andamiaje, estrategia de apoyo), en la
medida en que el runtime la implemente como categoría pedagógica, nunca como recurso
físico o referencia de plataforma (frontera ya fijada en `adaptar/productor.py:7-10`).
Aquí operan **PP4** (la decisión debe llegar con una forma concreta) y **PP5** (esa
forma no puede repetir lo que ya falló).

*Nota de honestidad:* hoy `DISENO_POR_ACCION` solo puebla `modalidad` y
`profundidad` — las otras dimensiones no existen todavía en el código. Ampliar la
descripción conceptual de este Momento no las implementa — solo evita describir a
Adaptar como permanentemente limitado a dos campos, cuando su frontera real
(categorías pedagógicas, nunca recursos físicos) siempre permitió más. *Qué forma
concreta del catálogo de PP4 le corresponde a una decisión dada — y por tanto si
esa forma es automática o requiere consentimiento — lo resuelve la
[Adenda A al Documento 5](ADENDA-A-seleccion-forma.md).*

**Momento 6 — El estudiante vive el Ciclo.**
La forma elegida en el Momento 5 se presenta. Aquí opera **PP6 en toda su extensión
(v3)**: la forma debe insertarse en el lugar donde el estudiante ya está — nunca
trasladarlo a un contexto nuevo para dársela. Esto coincide con un mecanismo que ya
existe en el código: `submitCycleEvidence` (`students.py:538`) inserta el refuerzo
dentro del mismo Ciclo activo, sin redirigir al estudiante a otra pantalla. El flujo
declara esto como el comportamiento por defecto, no como un caso especial.

**Momento 7 — Nueva evidencia.**
El estudiante interactúa con la forma del Momento 6 y eso genera un hecho nuevo — el
Ciclo no termina en el Momento 6, se realimenta al Momento 1. Esta realimentación es
la forma concreta que toma PP0 dentro de un Ciclo.

**Momento 8 — Validación y modelado.**
Cuando existe el hecho posterior (Momento 7), Validar compara antes/después y
produce el veredicto; Modelar lo interpreta como una dimensión del modelo del
estudiante. Este Momento puede no ocurrir de inmediato — el propio runtime lo
permite quedar pendiente hasta que el estudiante vuelva a esa competencia (ver §5).

---

## 3. Las tres escalas donde PP0-PP8 operan distinto

**Escala micro — dentro de un Ciclo.** Momentos 1-8. Gobernado por PP0, PP1, PP4,
PP5, PP6 (cláusula cognitiva), PP8.

**Escala meso — dentro de un módulo.** Un módulo consolida cuando todos sus Ciclos
relevantes llegan a un Momento 8 con veredicto positivo. Gobernado por **PP2**: el
desbloqueo del módulo siguiente es la agregación de esos veredictos — nunca una
decisión nueva.

**Escala macro — entre módulos y entre sesiones.** Al cerrar una misión, PP3 agrega
los veredictos en la Síntesis Pedagógica. Al cerrar sesión, Modelar consolida en
memoria persistente (`ejecutar_walkthrough(cerrar_sesion=True)`) — solo al cierre,
nunca a mitad de sesión (RFC-0005), restricción real que este flujo hereda.

---

## 4. Dónde el flujo cierra la brecha que la auditoría encontró

La señal de Tutorizar (Momento 2, rama conductual) no tiene traducción proactiva. Este
documento fija dónde debe insertarse cuando se resuelva: en el Momento 6, como una
forma más reconocida por PP4 — nunca como interrupción fuera de secuencia.

---

## 5. Lo que este flujo declara explícitamente incompleto

- **El Momento 8 puede quedar pendiente indefinidamente.** Si el estudiante no vuelve
  a una competencia, Validar nunca dispara. Es consistente con PP0, pero significa
  que la Síntesis Pedagógica puede cerrarse con Ciclos sin validar — tratamiento
  resuelto por [PP0 + Documento 5 §4.2](05-TRADUCCION-FRONTEND.md) (tres estados,
  nunca binario).
- **La reactivación de la política v1→v2 (PP7)** sigue sin resolverse aquí.
- **La consolidación de memoria depende de un cierre de sesión explícito** que el
  sistema no infiere — restricción técnica conocida, no vacío arquitectónico (ver
  [ANEXO-A](ANEXO-A-MATRIZ-TRAZABILIDAD.md) y stress-test en
  [ESTADO.md](ESTADO.md)).

---

## 6. Trazabilidad

| Sección del flujo | Opera |
|---|---|
| Momento 1 (apertura de evidencia) | PP0 |
| Momento 2 (interpretación) | PP0 |
| Momento 3-4 (tensión/decisión) | PP1 |
| Momento 5 (traducción) | PP4, PP5 |
| Momento 6 (vivir el Ciclo, inserción in-situ) | PP6 (cláusula cognitiva) |
| Momento 7 (realimentación) | PP0 |
| Momento 8 (validar/modelar) | PP8 |
| Escala meso (consolidación de módulo) | PP2 |
| Escala macro (cierre de misión) | PP3, PP6 (narrativa) |
