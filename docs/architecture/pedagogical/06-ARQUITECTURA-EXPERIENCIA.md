# ARQUITECTURA DE EXPERIENCIA — UPAO-MAS-EDU

**Documento 6 de la Arquitectura Pedagógica v1.0.** Estado: cerrado. Ampliado por
[ADENDA-C](ADENDA-C-recuperacion-memoria.md).

**Pregunta que responde:** dado que el Documento 5 ya definió el comportamiento UX,
¿cómo se organiza el espacio de interacción para que ese comportamiento ocurra sin
violar PP0-PP8?

**Principio metodológico:** no crear experiencia — organizarla. Toda relación
espacial se traza a una regla ya establecida en el
[Documento 5](05-TRADUCCION-FRONTEND.md), al [Flujo](04-FLUJO-ADAPTATIVO-CONTINUO.md),
o a PP0-PP8. No se decide aquí ningún componente, color, tipografía ni posición de
píxel.

---

## 1. Inventario funcional del espacio

### Persistencia — nunca desaparece mientras aplica

- **El reto activo**, mientras el Ciclo está en curso.
- **El progreso acumulado**, a escala meso y macro.
- **El punto exacto donde el estudiante quedó**, entre sesiones.

### Aparición — entra y sale según corresponda

- **Formas automáticas** (ejemplo, ilustración, pista breve, ajuste de profundidad).
- **Formas con consentimiento** (tutor, laboratorio guiado, remediación extensa,
  cambio de actividad).
- **La Síntesis Pedagógica** — aparece en el cierre, no permanece en foco
  indefinidamente, pero queda recuperable.

### Memoria — ni persiste a la vista, ni desaparece; queda recordada

Lo que el estudiante hizo dentro de un reto (qué leyó, qué ejemplo abrió, qué pista
aceptó, qué expandió) deja de ser visible cuando deja de ser relevante — pero no se
pierde. Queda disponible para reconstruir el mismo punto exacto al volver, dentro del
mismo Ciclo o entre sesiones.

*Traza a:* PP0 + escala macro del Flujo. *Distinción importante, para no confundirla
con §1 "Sin lugar en el espacio":* Memoria es historial de la propia interacción del
estudiante — legítimamente parte de su experiencia. Los Invariantes de Invisibilidad
son mecanismo interno del sistema — nunca parte de la experiencia, bajo ninguna
forma. Una cosa se recuerda; la otra nunca existió para el estudiante. *Cómo se
recupera:* ver [ADENDA C](ADENDA-C-recuperacion-memoria.md).

### Sin lugar en el espacio — ausencia deliberada

Todo lo listado en Invariantes de Invisibilidad (Doc 5 §5): deliberaciones, consenso,
confianza numérica, reintentos, estados transitorios, memoria técnica,
sincronizaciones. No ocupan una región oculta o colapsable — no ocupan ninguna
región.

---

## 2. Principios de organización espacial

**2a. Centralidad del Reto.** El desafío activo ocupa siempre el foco primario del
espacio; nada compite por esa posición mientras un Ciclo está en curso. **Ningún
otro elemento puede reclamar el foco primario mientras el reto permanezca abierto.**
*Traza a:* Doc 5, Momento 6.

**2b. Proximidad de la Adaptación.** Toda forma que el Momento 5-6 inserte aparece
en la misma región funcional que el reto que la originó — nunca en una región
distante o separada. *Traza a:* Doc 5, Momento 6.

**2c. Persistencia Selectiva.** Solo lo que el §1 marca como Persistencia ocupa una
posición fija y visible. Todo lo demás es transitorio *en su visibilidad*, no en su
existencia — lo que sale de la vista puede quedar en Memoria, recuperable, en vez de
perderse. *Traza a:* Doc 5, tabla primer plano/fondo.

**2d. Umbral de Consentimiento.** Toda transición espacial que corresponda a una
adaptación "con consentimiento" pasa por un gesto reconocible de entrada, y debe
ofrecer un regreso directo al mismo punto del reto — nunca un reinicio. *Traza a:*
Política de Consentimiento Adaptativo (Doc5 §4.1) + PP6.

**2e. Fondo Inaccesible.** Los Invariantes de Invisibilidad no tienen una región
"cerrada" ni "colapsada" que insinúe su existencia — la ausencia es total. *Traza a:*
Doc 5 §5 + PP1.

**2f. Trazabilidad Recuperable.** La razón de una adaptación permanece recuperable
desde el mismo lugar donde la adaptación vive — nunca en una superficie distinta.
*Traza a:* Doc 5, Momento 5.

**2g. Estado No-Binario Visible.** El espacio debe poder representar "pendiente de
evidencia" como una posición propia, distinguible de "en progreso" y "dominado".
*Traza a:* Doc 5 §4.2 + PP0.

**2h. Foco Adaptativo Único.** En un mismo Ciclo existe un único foco adaptativo
primario. Las demás adaptaciones automáticas compatibles esperan, se agregan o se
subordinan — nunca compiten simultáneamente por el mismo nivel de atención que el
reto. *Traza a:* PP6 — la continuidad cognitiva implica un único foco, no varios
disputándoselo.

---

## 3. Relaciones funcionales — dónde vive cada elemento

| Elemento | Dónde vive | Por qué |
|---|---|---|
| El reto | Centro funcional — el punto de referencia respecto al cual todo lo demás se posiciona. | 2a |
| El progreso | Periferia persistente — visible sin competir por el foco, nunca ausente. | 2c, PP2/PP8 |
| Ayuda automática | Adyacente o dentro de la región del reto — nunca en región distinta. | 2b |
| El tutor | Región con umbral de consentimiento, accesible desde la proximidad del reto; su activación no desconecta al estudiante del reto que dejó. | 2d |
| La Síntesis | Anclada al cierre de la misión específica que la produjo. | 2f, PP3 |
| El laboratorio (si se conecta) | Bajo 2a, no puede vivir como destino aparte: si el reto es un ejercicio de código real, el laboratorio *es* el reto, no una herramienta anexa. | 2a — consecuencia directa |

---

## 4. Navegación conceptual por escala

- **Escala micro:** no hay navegación en el sentido de "ir a otro lugar" — solo
  aparición/desaparición de formas dentro de la misma región (2c).
- **Escala meso:** hay transición real de región, precedida siempre por la Síntesis
  como puente — nunca ocurre sin ese puente (PP6 narrativa).
- **Escala macro:** la navegación reconecta exactamente donde la sesión anterior
  dejó al estudiante — nunca reinicia el espacio desde cero (PP0).

---

## 5. Alcance y límites

No decide componentes, color, tipografía, motion ni tecnología. "Distribución
funcional del espacio" no implica posiciones de píxel ni breakpoints — cuando el
medio no permita proximidad simultánea, la relación *funcional* de 2b debe
preservarse igual; su forma concreta de mostrarse en ese medio es decisión del
Documento 7.

---

## 6. Trazabilidad

| Principio espacial | Origen |
|---|---|
| 2a Centralidad del Reto | Doc 5, Momento 6 |
| 2b Proximidad de la Adaptación | Doc 5, Momento 6 |
| 2c Persistencia Selectiva | Doc 5, tabla primer plano/fondo |
| 2d Umbral de Consentimiento | Doc 5 §4.1 |
| 2e Fondo Inaccesible | Doc 5 §5 |
| 2f Trazabilidad Recuperable | Doc 5, Momento 5 |
| 2g Estado No-Binario Visible | Doc 5 §4.2 |
| 2h Foco Adaptativo Único | PP6 |
| Memoria | PP0 + escala macro del Flujo |
