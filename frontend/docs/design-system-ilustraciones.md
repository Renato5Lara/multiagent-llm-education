# Design System — Ilustraciones e infografías

**Estado:** oficial. Fuente única de verdad (Single Source of Truth) para cualquier recurso visual de la plataforma — no solo las 8 infografías actuales, también dashboards, diagramas y tutoriales futuros.

Este documento no genera ninguna imagen, no modifica contenido pedagógico ni componentes, y no depende de Runtime, LangGraph ni adaptación. Es documentación técnica pura: las reglas que cualquier prompt, diseñador o ingeniero debe seguir para que un recurso visual nuevo se vea como parte del mismo sistema que los anteriores.

---

## 1. Propósito

**Objetivo del documento:** fijar, en un solo lugar, todas las decisiones visuales que hoy están implícitas en el código y en los 8 prompts ya redactados — para que la próxima persona (o el próximo prompt) que produzca un recurso visual no tenga que re-derivarlas mirando ejemplos sueltos.

**Alcance:** cubre identidad visual, paleta, tipografía, iconografía, diagramación, plantillas de composición y el pipeline de producción. No cubre contenido pedagógico (qué dice cada infografía) ni la arquitectura de software que la muestra (eso ya vive en `moduleExperience.ts` y los componentes de React) — este documento gobierna únicamente el **cómo se ve**, nunca el **qué dice** ni el **cómo se renderiza**.

**Responsabilidades — quién consulta qué:**
- Quien redacta un `imagePrompt` nuevo: este documento completo, especialmente §9–§12.
- Quien genera la imagen en GPT Image (o equivalente): §11 y §12 son el prefijo obligatorio de cualquier prompt.
- Quien registra el archivo resultante en código: §13.
- Quien decide si un concepto nuevo necesita infografía y de qué tipo: §10.
- Quien revisa que una pieza nueva no rompa la consistencia de la colección: §14.

**Relación con los otros documentos:**
- `infografias-prompts.md` — los 8 prompts completos, ya redactados siguiendo este Design System (no lo repiten; lo aplican).
- `infografias-auditoria.md` — inventario y estado (qué existe, qué falta) de esas 8 piezas.
- `illustrationAssets.ts` — el registro en código donde cada `imageAsset` se resuelve a un archivo real; §13 documenta el flujo hasta llegar ahí.

Este documento es normativo sobre los otros dos: si `infografias-prompts.md` alguna vez contradice una regla de aquí, este documento gana y el prompt en conflicto debe corregirse.

---

## 2. Filosofía visual

El sistema visual de las infografías prioriza, en este orden:

1. **Claridad** — el estudiante debe entender la imagen sin leer el texto de apoyo primero. Si una infografía necesita el párrafo de al lado para tener sentido, no cumplió su función.
2. **Simplicidad** — cada pieza resuelve una comparación o una descomposición, nunca varias a la vez. Ver §3.
3. **Comunicación pedagógica** — cada elemento visual (color, forma, ícono) tiene un significado fijo y repetido entre piezas (§5, §7); nada es decorativo puro.
4. **Reducción de carga cognitiva** — formato, paleta y plantilla se repiten entre las 8 piezas a propósito, para que el estudiante reconozca el patrón después de la primera infografía y no tenga que releer una leyenda nueva cada vez.
5. **Consistencia visual** — las 8 piezas (y cualquier futura) deben leerse como hechas por un mismo sistema, no como ilustraciones independientes encargadas por separado.
6. **Apoyo al aprendizaje, nunca sustituto** — la infografía complementa la explicación textual/narrada que ya existe en cada ciclo; no repite esa explicación con otras palabras ni la reemplaza.

**Por qué glassmorphism oscuro y no otro estilo:** la plataforma completa (dashboard, módulos, evidencia) ya usa fondo casi negro con paneles translúcidos — adoptar el mismo lenguaje visual en las infografías evita que se sientan "pegadas" sobre la interfaz, como un recurso ajeno insertado a último momento. Es una decisión de continuidad de producto, no una preferencia estética aislada.

**Por qué diagramas y no ilustraciones narrativas (sin personas, sin escenas completas):** el universo narrativo (robot explorador, robot doméstico) ya vive en el texto — analogías, ejemplos, PythonBridge. La infografía no reilustra esa historia: resuelve un problema distinto, más abstracto (¿qué hace precisa a una instrucción? ¿qué hace evaluable a una condición?). Mezclar ambos roles — diagrama abstracto + escena narrativa — diluiría los dos.

---

## 3. Principios pedagógicos

Cada regla existe por una razón didáctica concreta, no por gusto visual:

- **Una ilustración transmite una sola idea principal.** Dos ideas en una imagen obligan al estudiante a decidir cuál mirar primero — la decisión debe estar tomada por el diseño, no por el observador.
- **El texto dentro de la imagen es el mínimo indispensable.** Cada palabra de más compite por atención con la palabra que sí importa; el texto de apoyo ya existe fuera de la imagen (`body`, narración) — la imagen no lo duplica.
- **La imagen complementa la explicación, nunca la repite literalmente.** Si el texto ya dice "una instrucción precisa no deja nada a la imaginación", la imagen no debe limitarse a ilustrar esa frase con un ícono — debe mostrar la estructura (vago→preciso, meta→pasos) que el texto describe en palabras.
- **La jerarquía visual dirige la atención, no la decoración.** Tamaño, color y posición existen para guiar el orden de lectura (§4 "Jerarquía"); ningún elemento decorativo debe competir en peso visual con el nodo o panel que importa.
- **La iconografía tiene significado funcional, nunca ornamental.** Un ícono que no ayuda a distinguir "ambiguo" de "preciso", o "SÍ" de "NO", no debería estar ahí — ver §7 para el mapa cerrado de íconos permitidos.
- **Evitar redundancia entre imagen y explicación.** La imagen no necesita (ni debe) volver a explicar en prosa lo que el `body` ya explica — su valor es mostrar la ESTRUCTURA de la idea, algo que el texto solo puede describir de forma lineal.

---

## 4. Identidad visual

| Atributo | Definición |
|---|---|
| Estilo general | Glassmorphism oscuro + flat design. Ningún elemento fotorrealista, ninguna textura física simulada. |
| Nivel de abstracción | Diagrama (nodos, paneles, conectores, rombo), nunca escena ilustrada. |
| Personas | Ninguna. Ni realistas ni estilizadas — el foco es la estructura del concepto, no un personaje. |
| Fotografías | Ninguna. |
| 3D | Ninguno. Todo es plano (2D), sin perspectiva ni profundidad simulada con cámara. |
| Sombras | Ninguna sombra proyectada dura. La única "profundidad" permitida es la que da la traslucidez del relleno glass y el brillo sutil del borde — nunca un `box-shadow` oscuro debajo de un nodo. |
| Bordes | Finos (1–1.5px aparente), luminosos, nunca gruesos. Punteado = ambiguo/no evaluado; sólido = preciso/resuelto (ver §5, regla de significado). |
| Transparencias | Relleno de nodo/panel al **8% de opacidad** del color de rol sobre el fondo casi negro. Nunca relleno opaco. |
| Radio de esquinas | Redondeado suave (equivalente a `rounded-xl`/`rounded-2xl` de la UI real — ni esquinas vivas ni ovaladas). |
| Espaciado | Generoso; ver §8. La pieza nunca se siente apretada contra su propio marco. |
| Proporciones | Formato vertical 4:5 en las 8 piezas actuales (ver §9 y §11) — toda pieza nueva adopta la misma relación de aspecto salvo justificación explícita documentada en el momento de crearla. |

---

## 5. Paleta oficial

Ninguno de estos colores es nuevo: son los que `CLAUDE.md` ya documenta como paleta del producto, los mismos que los 8 `imagePrompt` existentes usan literalmente, o tokens ya presentes en `tailwind.config.js`. Este documento no inventa una paleta — la formaliza y le fija un significado.

| Rol | Hex | Propósito |
|---|---|---|
| Fondo | `#0a0a0f` | Lienzo completo de toda infografía. Nunca degradados fuertes ni otro tono de fondo. |
| Primario / ambiguo | `#f59e0b` (ámbar) | Nodo o panel que representa una idea/meta todavía **no ejecutable ni evaluable**. Siempre borde **punteado**. También sirve como color de "advertencia" en cualquier recurso visual futuro que lo necesite (mismo significado: "atención, esto no está resuelto todavía"). |
| Secundario / preciso | `#10b981` (esmeralda) | Nodo o panel que representa un paso o resultado **ejecutable/resuelto**. Siempre borde **sólido**. También sirve como color de "éxito" en cualquier recurso visual futuro (mismo significado: "esto ya está correcto"). |
| Condición / información | `#06b6d4` (cian) | Nodo tipo rombo (evaluación booleana) — variantes A.1/B.1, ver §9. También sirve como color de "información" en cualquier recurso visual futuro que necesite distinguir un dato de un estado. |
| Resaltado | `#7c3aed` (violeta) | Acentúa una palabra o rama puntual (las etiquetas "SÍ"/"NO", un nombre de variable) sin convertirla en un nodo propio — nunca como fondo de nodo/panel completo. |
| Error | `#dc2626` (rojo — token `danger` ya existente en `tailwind.config.js`) | Reservado para un futuro recurso visual que necesite señalar un error real (p. ej. un diagrama de depuración) — ninguna de las 8 infografías actuales lo usa, porque ninguna representa un error; no inventar su uso donde no corresponde. |
| Texto principal | `#f8fafc` (blanco hueso) | Todo el texto dentro de nodos/paneles. |
| Texto secundario | `#94a3b8` (gris azulado) | Subtítulos, leyenda de cierre, texto de apoyo fuera de los nodos. |
| Bordes (genérico) | `rgba(255,255,255,0.1)` | Borde de panel/contenedor genérico (no un nodo con rol semántico) — mismo valor que usa la UI real de la plataforma. |
| Conectores | `rgba(255,255,255,0.15)` | Líneas entre nodos. Siempre translúcidas, nunca sólidas ni con flecha decorada de más. |
| Rellenos | 8% de opacidad del color de rol correspondiente | Aplica a ambar/esmeralda/cian por igual — nunca un relleno sólido u opaco. |

**Regla fija de significado (repetida de los prompts existentes, porque es la más importante de todo el documento):** punteado + ámbar = ambiguo/no ejecutable; sólido + esmeralda = preciso/ejecutable; cian = pregunta evaluable. Ningún recurso nuevo debe reasignar estos significados a otro color.

**Nota de honestidad ya documentada en `infografias-prompts.md`, repetida aquí porque este documento es la fuente normativa:** el código tiene un segundo set de tokens ("neural-*": fondo `#10131a`, cian `#00dbe7`, violeta `#ce5dff`) usado en otros componentes de la plataforma, no en estas infografías. Esta paleta oficial usa deliberadamente la primera familia (la de `CLAUDE.md`) para toda pieza ilustrativa — no mezclar ambas familias dentro de un mismo recurso.

---

## 6. Tipografía

La UI real usa `Outfit` (sans) y `JetBrains Mono` (mono) — definidos en `tailwind.config.js`. Ningún generador de imágenes reproduce una fuente con exactitud por nombre, así que un `imagePrompt` nunca debe pedirla por nombre; en su lugar describe su forma. Este documento sí nombra las fuentes reales, porque también sirve como referencia para un diseñador humano que trabaje directamente en una herramienta vectorial.

| Uso | Escala real observada en la UI | Equivalente para un prompt de imagen |
|---|---|---|
| Etiqueta/eyebrow (mono, mayúsculas, tracking amplio — p. ej. "INFOGRAFÍA", "CICLO 1 DE 3") | 10–11px, tracking `0.15em` | Monoespaciada, mayúsculas, espaciado entre letras notablemente amplio, peso regular |
| Leyenda / caption | 12px (`text-xs`) | Sans, peso regular, la más pequeña del conjunto |
| Cuerpo / texto de apoyo | 14–16px (`text-sm`/`text-base`) | Sans, peso regular, muy legible |
| Título de nodo/panel | 16–18px | Sans geométrica, peso medium/semibold |
| Encabezado de pantalla | 20–24px (`text-xl`/`text-2xl`) | No aplica dentro de una infografía — es un nivel que vive en la UI, no en la imagen generada |

**Jerarquías:** el título del nodo/panel siempre pesa más (semibold) que sus preguntas/partes asociadas (regular); la leyenda de cierre siempre es la más liviana de toda la pieza (regular, color secundario).

**Alineaciones:** texto de nodo centrado u alineado a la izquierda según el ancho del nodo — nunca justificado, nunca alineado a la derecha (rompería el orden de lectura izquierda→derecha que sigue el resto de la UI).

**Uso de mayúsculas:** reservado a etiquetas/eyebrows cortas (título del nodo, "SÍ"/"NO") — nunca un párrafo completo en mayúsculas.

**Uso de monoespaciado:** reservado a fragmentos de código real dentro de un panel (p. ej. `edad = 20`, `nombre = input(...)`) y a las etiquetas tipo eyebrow — nunca al cuerpo explicativo.

**Espaciado:** interlineado cómodo (equivalente a `leading-relaxed` de la UI real) en cualquier bloque de más de una línea; nunca texto apretado.

---

## 7. Iconografía

- **Estilo:** outline/vectorial — coherente con el set de íconos que ya usa la UI real (`lucide-react`), nunca relleno sólido, nunca fotorrealista.
- **Grosor:** trazo fino y uniforme (equivalente al stroke por defecto de Lucide, ~1.5–2px a escala de ícono pequeño) — el mismo grosor en todos los íconos de una misma pieza y entre piezas distintas.
- **Tamaño:** pequeño, siempre subordinado al nodo que acompaña — nunca un ícono a escala de protagonista. El ancla temática del ciclo (batería, caja, robot con pantalla, sensor) aparece una sola vez por pieza, cerca del nodo superior, a escala reducida.
- **Separación:** espacio propio respecto al texto que acompaña (nunca pegado ni superpuesto).
- **Consistencia:** un mismo símbolo para un mismo significado en toda la colección — `?` = ambigüedad, `✓` = ejecutable/resuelto, sensor/medidor = evaluación booleana. No introducir un ícono nuevo para un significado que ya tiene uno asignado.
- **Cuándo usar íconos:** para reforzar semánticamente un nodo (ambigüedad, resolución, evaluación) o para anclar el tema del ciclo una sola vez.
- **Cuándo NO usarlos:** como relleno decorativo de espacio vacío, como viñeta de lista, o repetido más de una vez por el mismo motivo dentro de la misma pieza.

---

## 8. Diagramación

- **Grid:** vertical, de arriba hacia abajo — el orden de los bloques en el lienzo replica el orden en que el `body` de texto explica el concepto (ver §3, "la jerarquía visual dirige la atención").
- **Márgenes:** mínimo ~8% del lienzo en los cuatro bordes — ninguna pieza toca su propio marco.
- **Padding interno de nodo/panel:** suficiente para que el texto nunca toque el borde del nodo — equivalente visual al `p-4`/`p-5` que ya usa la UI real en sus paneles.
- **Separación entre bloques hermanos:** amplia, nunca nodos que se toquen o se superpongan.
- **Alineaciones:** todo centrado en el eje vertical del lienzo — ninguna pieza descentra su composición principal.
- **Proporciones:** ver §4 y §9 — 4:5, con la distribución de altura que fija cada plantilla.
- **Espacio negativo:** deliberado, no accidental — el espacio vacío alrededor de un nodo es parte de cómo se lee la jerarquía, no un sobrante a rellenar con decoración.

---

## 9. Plantillas de composición

Existen **únicamente dos plantillas oficiales**. Una condición booleana no es una tercera familia de composición: es una variante que cualquiera de las dos plantillas puede incorporar cuando el concepto lo requiere.

### Plantilla A — Jerarquía (Árbol)

Se usa cuando el concepto se explica como una **descomposición**: una meta se separa en los pasos que la hacen posible.

```
        META

    ├── Paso 1
    └── Paso 2
```

**Cuándo usarla:** el concepto es un procedimiento o una secuencia — "esto no es un paso, es la meta; estos sí son pasos".

**Qué comunica:** que una instrucción de alto nivel no es ejecutable por sí sola hasta que se descompone en acciones concretas.

**Ejemplos reales:** las 4 piezas de remediación Nivel 2 (`m1-c1-l2-recarga-bateria`, `m1-c2-l2-caja-vacia`, `m1-c3-l2-cartel-robot`, `m2-c1-l2-aire-mal`).

#### Variante A.1 — Decisión

Cuando el concepto exige una condición booleana, el nodo inferior deja de ser dos pasos hermanos y se convierte en un **rombo de decisión** con dos ramas.

```
        META

         ↓

     ¿Condición?

     /         \
   SÍ           NO
```

**Cuándo corresponde:** cuando "el paso siguiente" en realidad depende de evaluar algo — no son dos pasos fijos, son dos resultados posibles según una pregunta SÍ/NO.

**Ejemplo real:** `m2-c1-l2-aire-mal` (remediación de Módulo 2 · Ciclo 1 — el aire está mal → ¿CO2 > 800 ppm? → enciende/no enciende el ventilador).

### Plantilla B — Comparación

Se usa cuando el objetivo es **contrastar** una idea vaga contra su versión precisa/correcta — el mismo concepto, dos estados.

```
   VAGO

     ↓

  PRECISO
```

**Cuándo usarla:** el concepto es un cambio de estado conceptual — de una idea que deja huecos a una que no deja ninguno.

**Qué comunica:** qué información específica faltaba en la versión vaga, y cómo la versión precisa la provee explícitamente.

**Ejemplos reales:** las 4 piezas de teoría/VARK Visual (`m1-c1-teoria-cruza-habitacion`, `m1-c2-teoria-variable-nombre`, `m1-c3-teoria-pregunta-input`, `m2-c1-teoria-condicion-paraguas`).

#### Variante B.1 — Comparación con decisión

Cuando el panel "preciso" representa una condición evaluable en vez de una instrucción fija, ese panel incorpora el mismo rombo de decisión de la Variante A.1.

```
   VAGO

     ↓

 ¿Condición?

  SÍ / NO
```

**Cuándo corresponde:** el mismo criterio que A.1, aplicado dentro de la Plantilla B en vez de la A — el concepto es de comparación (no de descomposición en pasos) pero su lado "preciso" es booleano.

**Ejemplo real:** `m2-c1-teoria-condicion-paraguas` (teoría de Módulo 2 · Ciclo 1 — "si hace mal tiempo" vago vs. "¿el sensor detecta gotas? SÍ/NO" preciso).

---

## 10. Criterios para elegir una plantilla

| Concepto pedagógico | Plantilla recomendada | Justificación |
|---|---|---|
| Procedimiento / secuencia de pasos | A | El estudiante necesita ver que una meta se descompone en acciones concretas y ordenadas — la estructura de árbol replica esa descomposición. |
| Comparación conceptual (vago vs. correcto) | B | El estudiante necesita contrastar dos versiones del mismo enunciado, no una secuencia — la estructura apilada con flecha replica "de esto, a esto". |
| Condición / lógica booleana | Variante A.1 (si el resto de la pieza es un árbol de pasos) o B.1 (si el resto es una comparación vago/preciso) | Una condición no es un paso más ni una versión "más precisa" simple: es una pregunta con dos resultados posibles — el rombo es el único elemento que representa eso sin ambigüedad. |
| Entrada de datos (`input()`) | B | El "antes" (el programa asume o adivina un valor) y el "después" (el programa pregunta y espera) son dos estados del mismo problema — comparación, no secuencia de pasos física. |
| Variables | A o B según el énfasis del ciclo | Si el ciclo enfatiza el proceso de crear la variable (nombrar → asignar), usar A; si enfatiza el contraste entre un valor suelto y uno con nombre, usar B. Ambos casos ya conviven en Módulo 1 · Ciclo 2: A en su remediación, B en su teoría. |

Regla general cuando un concepto nuevo no calza claramente en la tabla: preguntar primero "¿esto es una secuencia de pasos (A) o una comparación de dos estados (B)?" antes de preguntar "¿necesita un rombo?" — el rombo es siempre una variante, nunca el punto de partida de la decisión.

---

## 11. Reglas para GPT Image

Bloque único, reutilizable, que debe anteponerse a **todo** `imagePrompt` nuevo antes de su contenido específico — así cada prompt individual solo añade composición, textos e íconos propios sobre esta base ya fijada:

> Toda imagen debe pertenecer al mismo sistema educativo de diagramas: modo oscuro, fondo casi negro (#0a0a0f), estilo "glassmorphism" con paneles/nodos de relleno translúcido (8% de opacidad del color de rol) y bordes finos luminosos — nunca opacos, nunca con sombra dura proyectada. Iluminación plana, sin foco de luz direccional ni brillos falsos de vidrio. Perspectiva frontal en 2D puro, sin profundidad simulada ni 3D. Paleta cerrada: ámbar #f59e0b (ambiguo, borde punteado), esmeralda #10b981 (preciso, borde sólido), cian #06b6d4 (condición/rombo de decisión), violeta #7c3aed (resaltados puntuales como SÍ/NO), texto blanco hueso #f8fafc y gris azulado #94a3b8, conectores blanco translúcido rgba(255,255,255,0.15) — ningún color fuera de esta lista. Tipografía geométrica sans-serif sin serifas ni cursivas, monoespaciada solo para fragmentos de código real. Iconografía outline minimalista, trazo fino y uniforme, sin relleno sólido, sin fotorrealismo, sin íconos de personas. Composición limpia y con espacio en blanco generoso — nunca abarrotada, sin elementos decorativos que no cumplan una función semántica. Formato vertical 4:5, resolución mínima 1600×2000 px.

Cada prompt individual añade, después de este bloque, únicamente: qué plantilla usa (§9), qué representa cada nodo/panel, y los textos literales a incluir.

---

## 12. Elementos prohibidos

| Prohibido | Por qué |
|---|---|
| Fotografías | Rompe el nivel de abstracción del diagrama — introduce detalle irrelevante que compite con la información pedagógica. |
| Personas realistas o estilizadas | El foco es la estructura del concepto, no un personaje; además abre la puerta a inconsistencia de estilo entre piezas generadas en momentos distintos. |
| Cliparts | Contradicen el estilo flat/glassmorphism minimalista — se leen como un recurso de PowerPoint genérico, no como parte de un sistema de producto. |
| Emojis renderizados como imagen final | Los emoji que aparecen en el `body` de texto de la app (🔋 📦 🤖 📊) son solo para la interfaz de texto — copiarlos literalmente al lienzo generado rompe la iconografía outline consistente de §7. |
| Sombras exageradas | Simulan una profundidad física que el resto de la UI no tiene — rompe la sensación de "panel de vidrio plano" del glassmorphism real del producto. |
| Degradados saturados | La paleta oficial (§5) es de colores planos con relleno translúcido al 8% — un degradado saturado introduce un color fuera de la lista cerrada. |
| Colores fuera de la paleta | Cada color de §5 tiene un significado fijo; un color nuevo sin significado asignado confunde al estudiante que ya aprendió a leer la paleta en piezas anteriores. |
| Texto pequeño ilegible | Si el texto no se lee a tamaño normal de visualización, la pieza falló en su función más básica — mejor menos texto que texto ilegible. |
| Iconografía de distintos estilos mezclados | Un ícono outline junto a uno con relleno sólido se lee como un error de producción, no como una elección — rompe la consistencia de §7 dentro de la misma pieza. |
| Perspectiva isométrica si el resto es plano | Mezclar 2D plano con un elemento isométrico crea una inconsistencia de profundidad dentro de la misma imagen — todo el sistema es 2D puro (§4), sin excepciones parciales. |

---

## 13. Flujo oficial de producción

```
Idea pedagógica
      ↓
imagePrompt (redactado siguiendo §9–§12, con el bloque de §11 como prefijo)
      ↓
Generación en GPT Image (o generador equivalente)
      ↓
Revisión humana (contra §4–§8 y §12 de este documento)
      ↓
Exportación PNG/SVG/WebP (SVG cuando el diagrama es puramente geométrico; PNG/WebP en la generación inicial si el generador no produce SVG nativo)
      ↓
Registro en illustrationAssets.ts (import + entrada en ILLUSTRATION_ASSETS, misma clave que el imageAsset ya declarado en el contenido)
      ↓
Visualización en la aplicación (IllustrationVisual la muestra automáticamente en cuanto la clave resuelve — sin tocar ningún componente)
```

Cada flecha de este pipeline ya está resuelta en código o en documentación existente salvo "Generación" y "Revisión humana", que son manuales por restricción explícita del proyecto (sin IA generativa en código, sin llamadas a API de generación).

---

## 14. Gobernanza

Reglas para incorporar una ilustración nueva sin degradar la consistencia de la colección:

- **Revisión:** antes de generar, el `imagePrompt` propuesto se valida contra §9 (¿qué plantilla y por qué, usando §10?), §11 (¿incluye el bloque prefijo completo?) y §12 (¿evita todos los elementos prohibidos?). Antes de registrar la imagen ya generada, se valida visualmente contra §4–§8 (paleta, tipografía, iconografía, diagramación).
- **Aprobación:** una imagen generada no se registra en `illustrationAssets.ts` hasta pasar la revisión anterior — una pieza que no calza con el sistema es peor que no tener imagen (el fallback textual ya funciona bien; una imagen inconsistente rompe más de lo que arregla).
- **Versionado:** si el `imagePrompt` de una pieza cambia después de que ya existe una imagen real para ella, la imagen nueva se guarda con un sufijo de versión (`-v2`) en vez de sobrescribir el archivo — permite comparar antes/después y revertir si la nueva versión no mejora la pieza. La clave en `ILLUSTRATION_ASSETS` se actualiza para apuntar a la versión vigente.
- **Compatibilidad:** nunca se elimina o renombra un `imageAsset` sin actualizar, en el mismo cambio, el contenido del ciclo que lo declara — la clave es el contrato entre contenido y recurso visual; romperlo en un lado sin el otro dejaría una referencia huérfana o una imagen sin usar.
- **Extensión del sistema:** si una categoría de contenido nueva (fuera de teoría/remediación) alguna vez necesita ilustración real, el primer paso es extender el tipo correspondiente con `VisualAsset` (el mismo patrón que ya usan `ConceptVariant` y `RemediationIllustration`) — nunca inventar un mecanismo de imagen paralelo. Este documento sigue aplicando sin cambios; solo cambia qué tipo de contenido lo consume.

---

## Validación de este documento

- No contradice `infografias-prompts.md`: la paleta, plantillas y formato (4:5) descritos aquí son exactamente los que los 8 prompts ya usan; §9 formaliza las mismas dos plantillas que ese documento ya distinguía como "Plantilla A/B", con las variantes de decisión (A.1/B.1) reemplazando lo que una versión anterior de la conversación había llamado, incorrectamente, "Plantilla C" — corregido antes de escribir este documento, nunca llegó a publicarse como tal.
- No contradice `infografias-auditoria.md`: el inventario de 8 piezas, su clasificación LISTA PARA GENERAR y las categorías excluidas (remediación N1, reforzamientos sin medio visual) siguen vigentes; este documento no cambia ese estado.
- Mantiene únicamente dos plantillas oficiales (A y B) y sus variantes (A.1 y B.1) — ninguna tercera familia de composición.
- Es autosuficiente: un diseñador, un ingeniero frontend o un modelo generador de imágenes puede producir un recurso visual consistente leyendo únicamente este documento, sin necesitar abrir `infografias-prompts.md` como referencia adicional (aunque sí lo hará para copiar el contenido específico de cada pieza ya redactada).
