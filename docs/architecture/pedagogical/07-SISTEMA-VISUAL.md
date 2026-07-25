# SISTEMA VISUAL DE LA EXPERIENCIA — UPAO-MAS-EDU

**Documento 7 de la Arquitectura Pedagógica v1.0.** Estado: cerrado, con un vacío
declarado (§3) heredado deliberadamente hacia la implementación.

**Principio metodológico:** *no diseñar para decorar; diseñar para hacer visible la
arquitectura.*

**Qué responde:** cómo un lenguaje visual —no una implementación— hace perceptible lo
que los [Documentos 5](05-TRADUCCION-FRONTEND.md) y
[6](06-ARQUITECTURA-EXPERIENCIA.md) ya establecieron. No nombra componentes,
tecnologías, colores concretos ni herramientas. Todo lo que sigue debe poder
implementarse igual de bien en Stitch, Figma, React nativo o cualquier otro medio.

---

## 1. El mecanismo central: Reserva Semántica

*(Política derivada de PP1, PP5 y PP6 — no un principio nuevo.)*

> **Cada relación establecida en los Documentos 5 y 6 (foco, persistencia,
> aparición, memoria, cierre, consentimiento, incertidumbre) se expresa
> mediante un recurso visual reservado exclusivamente para ese significado.
> Ningún recurso representa dos significados distintos; ningún significado se
> expresa con más de un recurso a la vez.**

Esto no es estética — es la condición para que la arquitectura pedagógica siga siendo
legible sin haberla explicado con texto. Si el mismo énfasis que marca "esto es el
reto" se reutiliza para marcar "esto es una pista", la Centralidad del Reto (Doc 6,
2a) deja de ser perceptible aunque el código la respete por dentro.

**La Reserva Semántica no solo evita ambigüedad instantánea — protege el aprendizaje
del lenguaje visual a lo largo del tiempo. El estudiante termina aprendiendo el
sistema visual de la misma manera que aprende el contenido: por repetición
consistente entre recurso y significado. Reasignar un recurso ya aprendido no es una
mejora visual — es un costo cognitivo nuevo, equivalente a que el sistema cambiara de
vocabulario a mitad de curso.**

*Traza a:* PP6 (continuidad cognitiva) — aplicada aquí, por primera vez, al
aprendizaje del propio lenguaje visual a lo largo de semanas, no solo a transiciones
dentro de un Ciclo.

---

## 2. Respuestas por pregunta

**2.1 Jerarquía sin texto.** La prominencia relativa sigue el orden ya establecido —
reto > progreso > adaptación automática > memoria recuperable. *Traza a Doc 6 §1, 2a.*

**2.2 Foco perceptible.** Existe un único recurso reservado para señalar "esto es el
foco primario ahora" — nunca reutilizado, ni siquiera para algo igual de importante
en otro momento: la Síntesis al cierre usa su propio recurso, no el que marcaba al
reto durante el Ciclo. *Traza a 2a/2h.*

**2.3 Automática vs. con consentimiento.** Una adaptación automática se lee como
parte del mismo espacio del reto, sin umbral perceptible. Una con consentimiento se
lee como un umbral real. La diferencia debe reconocerse sin etiqueta que la explique.
*Traza a Doc 6, 2d.*

**2.4 "Pendiente de evidencia" sin sugerir fracaso.** Necesita registro propio, no un
punto intermedio entre éxito y error. *Traza a Doc 5 §4.2, PP0.*

**2.5 Continuidad entre Ciclos, módulos y misiones.** Dentro de un Ciclo: ninguna
señal de reinicio. Entre módulos: la transición lleva un rastro visible de la
Síntesis que la originó. Entre sesiones: el retorno se lee como continuación, no
como bienvenida. *Traza a PP6, Doc 6 §4.*

**2.6 Recursos por categoría del espacio.** Persistencia, Aparición, Memoria y
Cierre necesitan cuatro registros distintos y mutuamente excluyentes — no
variaciones de intensidad del mismo recurso. *Traza a Doc 6 §1.*

**2.7 Lenguaje que refuerza PP6.** Ninguna transición sustituye instantáneamente
todo el campo visual sin dejar rastro perceptible del estado anterior.

**2.8 Patrones a evitar.** Cualquier recurso que dé a un elemento no-reto peso igual
o mayor que el reto mientras el Ciclo está abierto; la señal de foco primario
reutilizada en otro elemento; más de una señal de "esto requiere tu atención ahora"
activa a la vez (viola 2h); cualquier recurso que delate la existencia del mecanismo
interno (viola Fondo Inaccesible, 2e).

---

## 3. Vacío declarado (se mantiene abierto — decisión, no omisión)

¿Debe existir algún indicio visual durante los Momentos 2-4? Se mantiene sin
resolver, y no por descuido: depende de una variable que ningún documento de esta
cadena modela — la política de visibilidad del tiempo de espera, que a su vez
depende del comportamiento temporal real del sistema (latencia, asincronía), no de
un principio pedagógico. PP1 exige que el mecanismo permanezca invisible; no dicta si
la mera espera debe acompañarse de una señal neutra. Ambos extremos son legítimos
bajo PP0-PP8 — la decisión correcta depende de datos que esta cadena documental,
deliberadamente, nunca modeló. **Se hereda como decisión de implementación.**

---

## 4. Alcance y límites

No nombra componente, color, tipografía, tecnología ni herramienta. "Recurso visual
reservado" es una categoría funcional — algo que puede variar en peso, posición,
persistencia o umbral — no prescribe cuál variable se usa ni cómo.

---

## 5. Trazabilidad

| Respuesta | Origen |
|---|---|
| 2.1 Jerarquía | Doc 6 §1, 2a |
| 2.2 Foco | Doc 6 2a, 2h |
| 2.3 Consentimiento | Doc 6 2d |
| 2.4 Pendiente de evidencia | Doc 5 §4.2, PP0 |
| 2.5 Continuidad | PP6, Doc 6 §4 |
| 2.6 Categorías del espacio | Doc 6 §1 |
| 2.7 Refuerzo de PP6 | PP6 |
| 2.8 Anti-patrones | 2a, 2e, 2h |

---

## 6. Prueba de Consistencia Visual

No introduce reglas nuevas — es el criterio para auditar cualquier implementación
futura contra este documento.

1. Si se eliminan todos los textos de ayuda, ¿la jerarquía visual sigue permitiendo
   identificar el foco del Ciclo?
2. Si se sustituye la tecnología (React, Flutter, Stitch, Figma, lo que sea), ¿las
   relaciones semánticas permanecen intactas?
3. Si un estudiante usa el sistema durante varias semanas, ¿los mismos significados
   siguen expresándose con los mismos recursos visuales?

Una respuesta negativa a cualquiera de las tres no es un defecto visual — es
evidencia de que la implementación rompió la Reserva Semántica (§1) en algún punto.
