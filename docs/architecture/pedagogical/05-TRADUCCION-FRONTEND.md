# TRADUCCIÓN DE LA PEDAGOGÍA AL FRONTEND — UPAO-MAS-EDU

**Documento 5 de la Arquitectura Pedagógica v1.0.** Estado: cerrado. Ampliado por
[ADENDA-A](ADENDA-A-seleccion-forma.md) y [ADENDA-B](ADENDA-B-semantica-rechazo.md).

**Rol de este documento:** especificación de comportamiento UX. Traduce PP0-PP8
([03-CONSTITUCION-PEDAGOGICA.md](03-CONSTITUCION-PEDAGOGICA.md)) y los 8 Momentos del
Ciclo ([04-FLUJO-ADAPTATIVO-CONTINUO.md](04-FLUJO-ADAPTATIVO-CONTINUO.md)) a reglas de
lo que el estudiante percibe, no de lo que ve. No contiene pantallas, componentes,
layout, color, tipografía, motion, ni referencia a React o Google Stitch.

**Criterio de validación:** toda regla cita el PP o el Momento del que se deriva.
Donde no hay base clara, se declara en vez de inventarse.

---

## 1. Marco de referencia

Este documento usa los 8 Momentos y las 3 escalas del Flujo como estructura, sin
repetirlos.

---

## 2. Comportamiento UX por Momento

### Encuadre — antes de cualquier Momento

Qué debe percibir el estudiante: que está actuando sobre un desafío propio, no
completando un formulario para el sistema. Ninguna superficie debe presentarse como
"para que el sistema recolecte información" — el desafío es el objeto de atención; la
evidencia es un efecto secundario de resolverlo. *Traza a:* encuadre del Flujo, PP0.

### Momento 1 — Apertura de evidencia

| Pregunta | Respuesta | Traza |
|---|---|---|
| ¿Qué debe percibir el estudiante? | Que está intentando resolver algo — no que está "generando datos". | PP0 |
| ¿Qué debe permanecer visible? | El desafío completo, tal como lo estaba trabajando. | PP6 |
| ¿Qué puede cambiar? | Nada todavía. | Momento 1 |
| ¿Qué nunca debe desaparecer? | El objeto del desafío, mientras el intento está en curso. | PP6 |
| ¿Qué debe mantenerse contextualizado? | El propio intento del estudiante. | PP6 |
| ¿Qué adaptación puede insertarse? | Ninguna. | Momento 1 |
| ¿Qué rompería PP6 aquí? | Interrumpir al estudiante antes de que termine de intentar. | PP6, PP0 |
| ¿Requiere interacción explícita? | Sí, siempre. | PP0 |
| ¿Primer plano / fondo? | El desafío en primer plano. El runtime, invisible. | PP1 |

### Momentos 2-4 — Interpretación / Tensión / Decisión

Internos al runtime; no producen nada observable por diseño.

| Pregunta | Respuesta | Traza |
|---|---|---|
| ¿Qué debe percibir el estudiante? | Nada directamente atribuible a "el sistema está decidiendo sobre mí". | PP1 |
| ¿Qué debe permanecer visible? | La continuidad del Momento 1. | PP6 |
| ¿Qué nunca debe desaparecer? | El hilo de lo que el estudiante estaba haciendo. | PP6 |
| ¿Qué adaptación puede insertarse? | Ninguna. | PP1 |
| ¿Requiere interacción explícita? | No — automático. | PP1 |
| ¿Primer plano / fondo? | Completamente en el fondo. | PP1 |

**Nota de alcance:** que estos Momentos sean invisibles para el estudiante no
significa que deban serlo para otros actores — "Modo Evidencia" es una capacidad de
observabilidad distinta, para un actor distinto, fuera del alcance de este documento.

### Momento 5 — Traducción a experiencia

| Pregunta | Respuesta | Traza |
|---|---|---|
| ¿Qué debe percibir el estudiante? | Que lo que recibe responde específicamente a lo que él hizo. | PP4, PP6 |
| ¿Qué debe permanecer visible? | El desafío/contexto original. | PP6 |
| ¿Qué puede cambiar? | La forma del contenido — nunca la identidad del desafío en curso. | PP4 |
| ¿Qué nunca debe desaparecer? | El hilo del desafío; la trazabilidad de por qué llegó esta forma. | PP6 |
| ¿Qué debe mantenerse contextualizado? | La razón de la adaptación, anclada al desafío. | PP6 |
| ¿Qué adaptación puede insertarse? | Cualquier forma del catálogo de PP4 que no repita la que ya falló (PP5). | PP4, PP5 |
| ¿Qué rompería PP6 aquí? | Cualquier forma que obligue a abandonar el contexto. | PP6 |
| ¿Requiere interacción explícita? | Ver §4.1 (Política de Consentimiento Adaptativo). | PP4 |
| ¿Primer plano / fondo? | La forma elegida entra en primer plano; el mecanismo, en el fondo. | PP1 |

### Momento 6 — El estudiante vive el Ciclo

| Pregunta | Respuesta | Traza |
|---|---|---|
| ¿Qué debe percibir el estudiante? | Continuidad — evolución del mismo reto, no actividad nueva. | PP6 |
| ¿Qué debe permanecer visible? | El problema/contexto exacto, en el mismo lugar. | PP6 (cognitiva) |
| ¿Qué puede cambiar? | El nivel de apoyo, la forma de interacción, el andamiaje disponible. | Momento 5 |
| ¿Qué nunca debe desaparecer? | El estado mental en curso. | PP6 (cognitiva) |
| ¿Qué debe mantenerse contextualizado? | Toda ayuda ofrecida, anclada al punto exacto del desafío. | PP6 |
| ¿Qué adaptación puede insertarse? | Refuerzo, pista o ejemplo, siempre en el mismo lugar — comportamiento por defecto. | PP6 |
| ¿Qué rompería PP6 aquí? | Sacar al estudiante a un contexto nuevo; reiniciar progreso ya hecho. | PP6 |
| ¿Requiere interacción explícita? | Ver §4.1. | §4.1 |
| ¿Primer plano / fondo? | El desafío activo siempre en primer plano. | PP6 |

### Momento 7 — Realimentación

| Pregunta | Respuesta | Traza |
|---|---|---|
| ¿Qué debe percibir el estudiante? | Que su acción quedó registrada como parte de su progreso. | PP0 |
| ¿Qué debe permanecer visible? | El mismo contexto del Momento 6. | PP6 |
| ¿Qué nunca debe desaparecer? | El desafío activo, hasta que el Ciclo concluya. | PP6 |
| ¿Qué es automático? | La captura del hecho nuevo. | PP0 |

### Momento 8 — Validar / Modelar

| Pregunta | Respuesta | Traza |
|---|---|---|
| ¿Qué debe percibir el estudiante? | Nada de forma inmediata — su efecto se hace visible a escala meso/macro. | PP1, PP8 |
| ¿Qué rompería el flujo aquí? | Mostrar un juicio inmediato tras una sola interacción, fuera del cierre de misión. | PP8 |

---

## 3. Comportamiento UX en las escalas meso y macro

### Escala meso — consolidación de módulo (PP2)

El desbloqueo se percibe como consecuencia, nunca como puerta cuya razón no puede
reconstruirse. La relación causal debe permanecer explicable.

### Escala macro — cierre de misión (PP3, Síntesis Pedagógica)

La Síntesis nombra específicamente lo que el estudiante hizo — nunca felicitación
genérica. Permanece anclada al cierre de esa misión específica, nunca desplazada a un
área de "reportes" desconectada. Es el único punto de la escala macro que amerita
reclamar la atención explícita del estudiante.

---

## 4. Políticas resueltas

### 4.1 Política de Consentimiento Adaptativo

*(Resuelve el vacío original sobre agencia del estudiante.)*

> **Una adaptación es automática si conserva el mismo objeto de atención y el
> mismo tipo de interacción que el estudiante ya tenía. Requiere consentimiento
> explícito si cambia el objeto de atención, cambia el tipo de interacción, o
> implica abandonar el intento en curso.**

- **Automáticas:** reordenar contenido, ejemplo adicional, cambio de ilustración,
  pista contextual breve, ajuste de profundidad.
- **Con consentimiento:** abrir sesión con el tutor, iniciar laboratorio guiado,
  cambiar de tipo de actividad, abandonar el ejercicio activo, iniciar remediación
  extensa.

*Traza a:* PP4 (catálogo de formas) + PP6 (el estudiante como protagonista del reto).
*Ampliada por:* [ADENDA A](ADENDA-A-seleccion-forma.md) (quién elige la forma
concreta) y [ADENDA B](ADENDA-B-semantica-rechazo.md) (qué significa un rechazo).

### 4.2 Estados de la Síntesis Pedagógica

*(Resuelve el vacío original sobre representar incertidumbre sin fracaso.)*

> **Ninguna competencia dentro de una Síntesis Pedagógica se representa en solo
> dos estados. Existen tres: Dominado, En progreso, Pendiente de evidencia.**

- **Dominado** — Validar registró `funciono=True`.
- **En progreso** — hay evidencia y decisión, pero el veredicto todavía no fue
  positivo, o hay Ciclos activos sobre la competencia dentro de esta misión.
- **Pendiente de evidencia** — el Momento 8 nunca se alcanzó para esa competencia en
  esta misión — el estado explícito para "no lo sabemos todavía".

*Traza a:* PP0 + PP3 — un colapso a dos estados sería una interpretación nueva no
autorizada por PP3.

---

## 5. Invariantes de Invisibilidad

> **El estudiante nunca debería percibir:** deliberaciones internas del runtime,
> consenso o desacuerdo entre productores, valores de confianza numérica,
> reintentos o correcciones internas, estados transitorios del sistema, memoria
> técnica del modelo del estudiante, ni sincronizaciones entre capas.

Todo eso pertenece al mecanismo (Momentos 2-4, 8), nunca a la experiencia. Es la
contraparte explícita de PP1: si el Boundary alguna vez expusiera un residuo de estos
elementos hacia el estudiante, estaría violando PP1 aunque técnicamente no haya
"decidido" nada.

---

## 6. Alcance y límites

No decide layout, navegación ni responsive (Documento 6). No decide estética
(Documento 7).

---

## 7. Trazabilidad — verificación cruzada por principio

| Principio | Consecuencia de comportamiento | Momento(s) donde opera |
|---|---|---|
| PP0 | La evidencia nunca es el propósito visible. | Encuadre, Momento 1, 7 |
| PP1 | Todo lo interno al runtime es invisible para el estudiante. | Momentos 2-4, 8 |
| PP2 | El desbloqueo de módulo se percibe como consecuencia. | Escala meso |
| PP3 | La Síntesis cita evidencia real del estudiante. | Escala macro |
| PP4 | Toda decisión llega con una forma concreta y reconocible. | Momento 5 |
| PP5 | La forma nunca repite lo que ya falló. | Momento 5 |
| PP6 (narrativa) | Ninguna transición se siente como inicio de algo nuevo. | Momento 6, escalas meso/macro |
| PP6 (cognitiva) | Ninguna adaptación obliga a reconstruir el problema. | Momento 6 |
| PP7 | No aplica todavía en comportamiento observable. | — |
| PP8 | Ningún veredicto se muestra fuera de contexto ni a mitad de un desafío. | Momento 8 |
