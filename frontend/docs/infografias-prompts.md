# Infografías pendientes — prompts listos para generar

Documento de solo lectura para producción de recursos visuales. No genera ninguna imagen por sí mismo: recopila los `imagePrompt` ya redactados en el código (`lib/experiences/*.ts`), les asigna una guía de estilo única, y deja cada uno listo para copiar y pegar en ChatGPT (GPT Image) o un generador compatible.

Cobertura (jul 2026, tercera vuelta — cobertura completa): **8 piezas en total** — las 4 de remediación Nivel 2 (secciones 1–4, prompt desde la segunda vuelta) y las 4 de la infografía **principal de teoría / VARK Visual** (secciones 5–8, nuevas en esta vuelta — antes era el hueco explícito que dejaba la vuelta anterior). Para el estado de cada una (imagen/prompt/integración) y su clasificación COMPLETA/LISTA PARA GENERAR/PENDIENTE, ver `frontend/docs/infografias-auditoria.md`.

**No modifica código.** La integración de la imagen resultante al `imageAsset` correspondiente (registro en `lib/experiences/illustrationAssets.ts`) es un paso posterior, fuera de este documento.

**Regla normativa:** todo prompt de este documento sigue `frontend/docs/design-system-ilustraciones.md` — paleta, tipografía, iconografía, plantillas y el bloque prefijo de §11 son ese documento, no una copia local. Si algo aquí llegara a contradecirlo, el Design System gana.

---

## Cómo usar este documento

1. Copia el **prompt completo** de una sección (todo el bloque dentro de la cita, tal cual — ya incluye estilo, colores, iconografía y textos literales).
2. Pégalo en ChatGPT (GPT Image) o un generador de imágenes compatible con prompts largos en español.
3. Pide explícitamente la **resolución recomendada** de la sección si el generador lo permite; si no, genera al máximo tamaño disponible y re-escala/upscale después.
4. Exporta en el **formato recomendado** de la sección.
5. Guarda el archivo en `frontend/src/assets/illustrations/` con un nombre basado en el **recurso (`imageAsset`)** de la sección.
6. Regístralo en `frontend/src/lib/experiences/illustrationAssets.ts` (import + entrada en `ILLUSTRATION_ASSETS`, misma clave que `imageAsset`) — esto ya está preparado en el código, solo falta la imagen real.

Ninguna imagen se genera automáticamente como parte de este documento ni de ningún proceso automatizado — cada una requiere una acción manual deliberada en el generador elegido.

---

## Guía de estilo única — todas las infografías

Esta guía existe para que las 8 piezas (y cualquier futura) se vean como una sola colección, no como ocho experimentos sueltos. Está derivada de dos fuentes que ya coinciden entre sí: la paleta documentada en `CLAUDE.md` (sección "Estética y diseño") y la paleta que los `imagePrompt` ya existentes usan literalmente — es decir, no es una paleta nueva, es la que el equipo ya venía usando, formalizada.

### Dos plantillas de composición, una sola guía de estilo

Las 8 piezas comparten paleta, iconografía, tipografía, espaciado y glassmorphism, pero se agrupan en **dos plantillas de composición** distintas según lo que representan — mezclarlas sería forzar una forma sobre un contenido que no le corresponde:

- **Plantilla A — árbol (1 nodo → 2 nodos):** usada por las 4 piezas de remediación (secciones 1–4). Representa "una meta ambigua se descompone en pasos ejecutables" — coherente con el `RemediationIllustration` que ilustra, que ya muestra esa misma jerarquía como texto (`├──`/`└──`).
- **Plantilla B — dos paneles apilados (vago → flecha → preciso):** usada por las 4 piezas de teoría/VARK Visual (secciones 5–8). Representa la comparación `ConceptInfographic.vague` vs. `ConceptInfographic.precise` que la UI ya renderiza como dos cajas apiladas con una flecha entre ellas (`ConceptStep.tsx`) — el prompt reproduce esa misma estructura, no inventa una nueva.

Una excepción dentro de cada plantilla: cuando el concepto es una condición booleana real (Módulo 2 · Ciclo 1, en ambas piezas), el nodo/panel "preciso" incorpora un **rombo de decisión** con dos ramas SÍ/NO en vez de dos nodos hermanos — es la única variación estructural permitida, y ya está anticipada en el propio código con una nota explicando por qué.

### Paleta de colores

| Rol | Color | Hex | Uso en la infografía |
|---|---|---|---|
| Fondo | Negro casi puro | `#0a0a0f` | Fondo de lienzo completo, sin degradados fuertes |
| Idea / meta ambigua | Ámbar | `#f59e0b` | Borde **punteado**, relleno al 8% — siempre marca lo "todavía no ejecutable" |
| Paso / resultado preciso | Verde esmeralda | `#10b981` | Borde **sólido**, relleno al 8% — siempre marca lo "ya ejecutable" |
| Condición / decisión | Cian | `#06b6d4` | Solo en nodos tipo rombo (evaluación booleana), borde sólido, relleno al 8% |
| Etiquetas de rama / énfasis puntual | Violeta | `#7c3aed` | Texto de "SÍ"/"NO", acentos de nombre de variable — nunca como fondo de nodo |
| Texto principal | Blanco hueso | `#f8fafc` | Todo el texto dentro de los nodos |
| Texto secundario / leyendas | Gris azulado | `#94a3b8` | Subtítulos pequeños, leyenda inferior |
| Conectores | Blanco translúcido | `rgba(255,255,255,0.15)` | Líneas entre nodos, nunca sólidas |

Regla fija de significado (no solo estética): **punteado + ámbar = ambiguo/no ejecutable**; **sólido + esmeralda = preciso/ejecutable**; **cian = pregunta evaluable**. Esta correspondencia color→significado debe repetirse en toda pieza nueva — es lo que hace que un estudiante reconozca el patrón entre infografías de ciclos distintos sin tener que releer la leyenda cada vez.

### Iconografía

- Outline/vectorial, nunca relleno sólido ni fotorrealista.
- Un ícono pequeño por nodo, como refuerzo semántico, nunca como protagonista: `?` junto a lo ambiguo, `✓` junto a lo ejecutable, ícono de sensor/medidor junto a una condición evaluable.
- El ancla temática del ciclo (batería, caja/contenedor, robot con pantalla, sensor de aire) aparece **una sola vez**, cerca del nodo superior, a escala reducida — nunca como ilustración central grande. La infografía es un diagrama, no una escena.
- Ningún ícono de persona, ningún emoji renderizado como imagen final (los emoji que aparecen en el `body` de texto de la app — 🔋 📦 🤖 📊 — son solo para la interfaz de texto, no deben copiarse literalmente al lienzo generado).

### Tipografía

La UI de la plataforma usa `Outfit` (sans, texto general) y `JetBrains Mono` (etiquetas cortas en mayúsculas con tracking amplio, como `INFOGRAFÍA` o `CICLO 1 DE 3`). Ningún generador de imágenes reproduce fuentes con exactitud, así que el prompt no debe pedir una tipografía por nombre — en su lugar:

- Texto de nodos: geométrica sans-serif, peso medium/semibold, muy legible a tamaño pequeño (los nodos son compactos).
- Subtítulos y leyenda: la misma familia, peso regular, un escalón más chica y en el gris secundario `#94a3b8`.
- Nada de cursiva, nada de serif, nada de letras decorativas — coherente con el resto de la interfaz, que es enteramente sans/mono.

### Espaciado

- Formato vertical, relación de aspecto **4:5** en las 4 piezas (ver nota de normalización más abajo).
- Nodo(s) superior(es): ~15–20% de la altura total.
- Zona de resultados/pasos: mitad inferior, con separación amplia entre nodos hermanos — nunca deben tocarse ni superponerse.
- Margen exterior generoso (mínimo ~8% del lienzo) en los cuatro bordes; la pieza no debe sentirse apretada contra el marco.
- La leyenda final va **fuera** de los nodos, centrada, como cierre — nunca dentro de una caja.

### Jerarquía visual

1. Nodo(s) de idea/meta (ámbar, punteado) — primera lectura, arriba.
2. Nodo de condición si existe (cian, rombo) — segunda lectura, centro.
3. Nodo(s) de paso/resultado (esmeralda, sólido) — tercera lectura, abajo.
4. Leyenda de cierre (gris, texto pequeño) — última lectura, resume la regla en una frase.

Esta jerarquía top-down replica exactamente el orden en que el `body` de texto de cada `illustration` explica el concepto — la imagen no debe reordenar la lógica que el texto ya estableció.

### Apariencia glassmorphism

- Paneles/nodos con relleno translúcido (8% de opacidad del color de rol) sobre el fondo casi negro, nunca opacos.
- Bordes finos y luminosos (1–1.5px aparente), nunca gruesos ni con sombra dura.
- Sin blur de fondo pesado ni reflejos de vidrio literales — el efecto "glass" se logra con la traslucidez del relleno y el brillo sutil del borde, no con brillos falsos ni destellos.
- Cero textura, cero ruido, cero grano — superficies limpias, como un panel de producto SaaS, no como una superficie física de vidrio.

### Consistencia con la UI actual

La UI ya usa esta misma paleta en producción — el fondo de página (`#0a0a0f`/`#10131a` según la superficie), los paneles translúcidos con borde `rgba(255,255,255,0.1)`, y acentos cian/violeta para estados activos y etiquetas. Generar las infografías con esta guía significa que, insertadas en `ConceptStep`/`RemediationStepView`, no van a "flotar" como un elemento ajeno pegado sobre la interfaz — van a leerse como parte nativa de la misma pantalla.

Nota de honestidad para quien genere las imágenes: el código tiene, además de esta paleta, un segundo set de tokens ("neural-*": fondo `#10131a`, cian `#00dbe7`, violeta `#ce5dff`) usado en otros componentes de la plataforma (no en estas infografías). Los 4 prompts de este documento usan consistentemente la primera paleta (la de `CLAUDE.md` y la ya redactada en el código de los ciclos) — se mantiene así deliberadamente para no introducir una quinta variante de color en la colección. Si en el futuro se decide unificar todo el producto a un solo set de tokens, este documento debe revisarse junto con ese cambio, no antes.

### Normalización de formato (decisión de este documento)

El prompt de remediación de Módulo 2 · Ciclo 1 (sección 4) permite en su redacción original "formato vertical 4:5 o 3:4". Para que las 8 piezas formen una colección visualmente uniforme (mismo marco, mismo recorte, intercambiables en la misma grilla de UI), este documento fija **las 8 piezas a 4:5**. Al copiar el prompt de esa sección, usa la resolución indicada (4:5) y no la alternativa 3:4 mencionada dentro del texto del prompt.

---

## 1. Módulo 1 · Ciclo 1 — Instrucciones precisas

- **Misión:** Misión 1 · El idioma de las máquinas
- **Territorio:** Explorador
- **Nivel de apoyo:** Remediación, Nivel 2 ("Probemos con otra representación, y más despacio")
- **Recurso (`imageAsset`):** `m1-c1-l2-recarga-bateria`
- **Resolución recomendada:** 1600×2000 px (4:5)
- **Formato recomendado:** PNG en la generación inicial (GPT Image no produce SVG nativo); candidato fuerte a re-trazado posterior a **SVG** por ser un diagrama 100% geométrico (2 formas, sin detalle fino) — recomendado una vez validado en la UI, para nitidez perfecta en cualquier zoom.
- **Estilo visual:** el de la guía única de arriba, sin variación.

**Prompt completo:**

> Diagrama jerárquico minimalista para una app educativa de programación, modo oscuro.
>
> COMPOSICIÓN: un único nodo superior centrado (la META, ambigua) del que bajan dos líneas conectoras en forma de "Y" invertida hacia dos nodos inferiores (los PASOS, ejecutables), distribuidos simétricamente izquierda/derecha.
>
> ESTILO: interfaz "glassmorphism" oscura, paneles translúcidos con bordes finos luminosos, sin fotorrealismo ni ilustración de personas — solo formas geométricas, texto e iconos vectoriales simples, como un diagrama de flujo de producto SaaS.
>
> COLORES: fondo casi negro #0a0a0f. Nodo superior: borde PUNTEADO ámbar #f59e0b, relleno ámbar al 8% de opacidad. Nodos inferiores: borde SÓLIDO verde esmeralda #10b981, relleno esmeralda al 8% de opacidad. Líneas conectoras gris translúcido rgba(255,255,255,0.15). Texto principal blanco hueso #f8fafc, texto secundario gris azulado #94a3b8.
>
> ICONOS: un signo de interrogación (?) pequeño junto al nodo superior (ambigüedad). Un check (✓) pequeño junto a cada nodo inferior (ejecutable). Un ícono outline minimalista de batería junto al robot, cerca del nodo superior, solo como ancla temática, sin volverse realista.
>
> DISTRIBUCIÓN: formato vertical 4:5. Nodo meta ocupa ~20% de la altura, centrado arriba. Los dos nodos de pasos ocupan la mitad inferior, con amplio espacio en blanco entre ellos y respecto a los bordes.
>
> ELEMENTOS DE TEXTO (incluir literalmente):
> — Nodo superior: "RECARGA LA BATERÍA" + subtítulo pequeño "la meta — el robot no sabe ejecutarlo"
> — Nodo inferior izquierdo: "Conecta el cable al puerto de carga"
> — Nodo inferior derecho: "Espera hasta que la luz indicadora se ponga verde"
> — Leyenda inferior centrada, fuera de los nodos: "Todo lo de arriba es una meta. Todo lo que cuelga de ella es una instrucción ejecutable."

---

## 2. Módulo 1 · Ciclo 2 — Variables

- **Misión:** Misión 1 · El idioma de las máquinas
- **Territorio:** Explorador
- **Nivel de apoyo:** Remediación, Nivel 2 ("Otra forma de verlo, con más calma")
- **Recurso (`imageAsset`):** `m1-c2-l2-caja-vacia`
- **Resolución recomendada:** 1600×2000 px (4:5)
- **Formato recomendado:** PNG en la generación inicial; candidato a **SVG** en re-trazado posterior (mismo criterio que la pieza 1).
- **Estilo visual:** el de la guía única de arriba, sin variación.

**Prompt completo:**

> Diagrama jerárquico minimalista para una app educativa de programación, modo oscuro.
>
> COMPOSICIÓN: un nodo superior centrado con forma de CAJA/CONTENEDOR abierto y vacío (la variable sin inicializar), del que bajan dos líneas conectoras en "Y" invertida hacia dos nodos inferiores: uno muestra la misma caja con una ETIQUETA/nombre pegada, el otro muestra la caja con un VALOR numérico dentro.
>
> ESTILO: interfaz "glassmorphism" oscura, paneles translúcidos con bordes finos luminosos, sin fotorrealismo — formas geométricas simples (la caja es un icono de contenedor/cubo en outline, no una ilustración realista), coherente con un diagrama de flujo de producto SaaS.
>
> COLORES: fondo casi negro #0a0a0f. Nodo superior (caja vacía): borde PUNTEADO ámbar #f59e0b, relleno ámbar al 8% de opacidad. Nodos inferiores (caja con nombre / caja con valor): borde SÓLIDO verde esmeralda #10b981, relleno esmeralda al 8%. Líneas conectoras gris translúcido rgba(255,255,255,0.15). Texto principal blanco hueso #f8fafc, texto secundario gris azulado #94a3b8. Acento cian #06b6d4 en la etiqueta de nombre del nodo izquierdo.
>
> ICONOS: la caja vacía es un icono de contenedor/cubo abierto en outline. En el nodo izquierdo, un pequeño icono de etiqueta/tag junto a la caja. En el nodo derecho, un pequeño icono de "+" o número dentro de la caja para indicar contenido.
>
> DISTRIBUCIÓN: formato vertical 4:5. Caja vacía ocupa ~20% de la altura, centrada arriba. Los dos nodos inferiores ocupan la mitad inferior, con amplio espacio en blanco entre ellos y respecto a los bordes.
>
> ELEMENTOS DE TEXTO (incluir literalmente):
> — Nodo superior: "CAJA VACÍA" + subtítulo pequeño "todavía no es una variable, no tiene nombre ni valor"
> — Nodo inferior izquierdo: "Crea una caja llamada temperatura" + etiqueta pequeña "ahora tiene nombre"
> — Nodo inferior derecho: "Guarda el número 18 dentro" + etiqueta pequeña "ahora tiene valor"
> — Leyenda inferior centrada, fuera de los nodos: "Sin el nombre, no hay dónde guardar nada. Sin el valor, no hay nada que leer."

---

## 3. Módulo 1 · Ciclo 3 — Entrada de datos (input)

- **Misión:** Misión 1 · El idioma de las máquinas
- **Territorio:** Explorador
- **Nivel de apoyo:** Remediación, Nivel 2 ("Vamos más despacio, con otra imagen")
- **Recurso (`imageAsset`):** `m1-c3-l2-cartel-robot`
- **Resolución recomendada:** 1600×2000 px (4:5)
- **Formato recomendado:** PNG en la generación inicial; candidato a **SVG** en re-trazado posterior (mismo criterio que las piezas 1–2). El ícono de robot con pantalla tiene algo más de detalle que las otras tres piezas — validar que el trazo se mantenga simple antes de vectorizar.
- **Estilo visual:** el de la guía única de arriba, sin variación.

**Prompt completo:**

> Diagrama jerárquico minimalista para una app educativa de programación, modo oscuro.
>
> COMPOSICIÓN: un nodo superior centrado con forma de PANTALLA/CARTEL de un robot (un rectángulo con una línea de pregunta mostrada y un espacio en blanco debajo, todavía sin respuesta), del que bajan dos líneas conectoras en "Y" invertida hacia dos nodos inferiores: uno muestra al robot MOSTRANDO la pregunta en su pantalla, el otro muestra una CAJA/contenedor guardando la respuesta.
>
> ESTILO: interfaz "glassmorphism" oscura, paneles translúcidos con bordes finos luminosos, sin fotorrealismo — iconografía plana tipo robot/pantalla y contenedor, coherente con un diagrama de flujo de producto SaaS.
>
> COLORES: fondo casi negro #0a0a0f. Nodo superior (cartel sin responder): borde PUNTEADO ámbar #f59e0b, relleno ámbar al 8%. Nodos inferiores: borde SÓLIDO verde esmeralda #10b981, relleno esmeralda al 8%. Líneas conectoras gris translúcido rgba(255,255,255,0.15). Texto principal blanco hueso #f8fafc, texto secundario gris azulado #94a3b8.
>
> ICONOS: icono outline de un robot con una pantalla mostrando una línea punteada donde iría la respuesta, en el nodo superior. En el nodo inferior izquierdo, un icono de globo de diálogo (la pregunta se muestra). En el nodo inferior derecho, un icono de caja/contenedor con un check dentro (el dato quedó guardado).
>
> DISTRIBUCIÓN: formato vertical 4:5. Cartel del robot ocupa ~20% de la altura, centrado arriba. Los dos nodos inferiores ocupan la mitad inferior, con amplio espacio en blanco entre ellos y respecto a los bordes.
>
> ELEMENTOS DE TEXTO (incluir literalmente):
> — Nodo superior: "CARTEL DEL ROBOT" + subtítulo pequeño "la pregunta impresa, todavía sin respuesta"
> — Nodo inferior izquierdo: "Muestra la pregunta ¿Cuántos años tienes?" + etiqueta pequeña "el robot pregunta"
> — Nodo inferior derecho: "Guarda la respuesta en la caja edad" + etiqueta pequeña "recién aquí hay un dato"
> — Leyenda inferior centrada, fuera de los nodos: "Sin la pregunta, nadie sabe qué escribir. Sin guardar la respuesta, se pierde apenas el programa sigue."

---

## 4. Módulo 2 · Ciclo 1 — Condiciones evaluables

- **Misión:** Misión 2 · Decisiones que la máquina entiende
- **Territorio:** Estratega
- **Nivel de apoyo:** Remediación, Nivel 2 ("Probemos con otra representación, y más despacio")
- **Recurso (`imageAsset`):** `m2-c1-l2-aire-mal`
- **Resolución recomendada:** 1600×2000 px (4:5) — **normalizado**: el prompt original ofrece "4:5 o 3:4"; usar 4:5 para mantener la colección uniforme (ver nota de normalización en la guía de estilo).
- **Formato recomendado:** PNG en la generación inicial; candidato a **SVG** en re-trazado posterior. Es la única de las 4 piezas con un nodo de **rombo de decisión** además de rectángulos — mantener el mismo criterio geométrico simple facilita igual el vectorizado.
- **Estilo visual:** el de la guía única de arriba, sin variación. Nota ya presente en el código: a diferencia de las otras tres (siempre 2 ramas rectangulares), esta pieza sí representa una condición booleana real — de ahí el rombo de decisión estándar de diagramas de flujo, coherente con el concepto `if`/`else`.

**Prompt completo:**

> Mini diagrama de flujo para una app educativa de programación, modo oscuro.
>
> COMPOSICIÓN: un nodo superior centrado (rectángulo, la IDEA vaga "el aire está mal"), que baja a un ROMBO de decisión (la condición evaluable "¿el CO2 supera 800 ppm?"), del que salen dos ramas etiquetadas SÍ / NO hacia dos nodos rectangulares finales (los resultados "enciende el ventilador" / "lo mantiene apagado"). Es un flujo vertical de arriba hacia abajo: idea → condición → dos resultados posibles.
>
> ESTILO: interfaz "glassmorphism" oscura, iconografía plana de diagrama de flujo real (rombo = decisión, rectángulo = proceso/resultado), sin fotorrealismo, coherente con un producto SaaS educativo.
>
> COLORES: fondo casi negro #0a0a0f. Nodo superior (idea vaga): borde PUNTEADO ámbar #f59e0b, relleno ámbar al 8%. Rombo de decisión: borde SÓLIDO cian #06b6d4, relleno cian al 8%. Los dos nodos de resultado: borde SÓLIDO verde esmeralda #10b981, relleno esmeralda al 8%. Líneas conectoras gris translúcido rgba(255,255,255,0.15), con las etiquetas "SÍ" y "NO" en violeta #7c3aed junto a cada rama. Texto principal blanco hueso #f8fafc, texto secundario gris azulado #94a3b8.
>
> ICONOS: signo de interrogación pequeño junto al nodo superior (idea, ambigua). Un pequeño ícono de sensor/medidor dentro del rombo (evaluación). Un ícono de ventilador junto al resultado "enciende el ventilador" y un ícono de ventilador apagado (sutil, mismo tamaño) junto a "lo mantiene apagado" — ambos igual de neutrales en tamaño, ningún resultado debe verse "más importante" que el otro.
>
> DISTRIBUCIÓN: formato vertical 4:5 (normalizado — ver nota arriba). Nodo idea arriba (~15% de la altura), rombo de decisión al centro (~25%), los dos resultados abajo distribuidos simétricamente izquierda/derecha (~30%), con espacio en blanco generoso entre cada nivel.
>
> ELEMENTOS DE TEXTO (incluir literalmente):
> — Nodo superior: "EL AIRE ESTÁ MAL" + subtítulo pequeño "la idea — la máquina no sabe evaluarla"
> — Rombo: "¿El CO2 supera 800 ppm?"
> — Resultado izquierdo (rama SÍ): "Enciende el ventilador"
> — Resultado derecho (rama NO): "Lo mantiene apagado"
> — Leyenda inferior centrada, fuera de los nodos: "Todo lo de arriba es una idea. Todo lo que cuelga de ella es una condición evaluable."

---

## 5. Módulo 1 · Ciclo 1 — Instrucciones precisas (Teoría · VARK Visual)

- **Misión:** Misión 1 · El idioma de las máquinas
- **Territorio:** Explorador
- **Ubicación:** Teoría principal del ciclo, variante Visual (`ConceptVariant.infographic`) — la primera pantalla que ve un estudiante de perfil visual, no un peldaño de remediación.
- **Recurso (`imageAsset`):** `m1-c1-teoria-cruza-habitacion`
- **Resolución recomendada:** 1600×2000 px (4:5)
- **Formato recomendado:** PNG en la generación inicial; candidato a **SVG** en re-trazado posterior (mismo criterio que las piezas de remediación — 2 paneles simples, sin detalle fino).
- **Estilo visual:** el de la guía única de arriba, Plantilla B (dos paneles apilados).

**Prompt completo:**

> Infografía comparativa de dos paneles para una app educativa de programación, modo oscuro.
>
> COMPOSICIÓN: dos paneles rectangulares del mismo ancho, apilados verticalmente. Panel superior = INSTRUCCIÓN VAGA. Panel inferior = INSTRUCCIÓN PRECISA. Entre ambos, una flecha corta apuntando hacia abajo con una etiqueta pequeña "hazla precisa".
>
> ESTILO: interfaz "glassmorphism" oscura, paneles translúcidos con bordes finos luminosos, sin fotorrealismo ni ilustración de personas — solo formas geométricas, texto e iconos vectoriales simples, como un diagrama de producto SaaS.
>
> COLORES: fondo casi negro #0a0a0f. Panel vago (superior): borde PUNTEADO ámbar #f59e0b, relleno ámbar al 8% de opacidad. Panel preciso (inferior): borde SÓLIDO verde esmeralda #10b981, relleno esmeralda al 8%. Flecha central y su etiqueta en gris azulado #94a3b8. Texto principal blanco hueso #f8fafc, texto secundario gris azulado #94a3b8.
>
> ICONOS: tres signos de interrogación (?) pequeños distribuidos junto a las preguntas del panel vago. Tres checks (✓) pequeños junto a las tres partes del panel preciso. Un ícono outline minimalista de robot, pequeño, como ancla temática, en la esquina superior del panel vago (sin volverse realista).
>
> DISTRIBUCIÓN: formato vertical 4:5. Panel vago ocupa el 40% superior, panel preciso el 40% inferior, con la flecha y su etiqueta en el 10% central, y una leyenda final en el 10% inferior, fuera de ambos paneles.
>
> ELEMENTOS DE TEXTO (incluir literalmente):
> — Panel vago, título: "CRUZA LA HABITACIÓN" — debajo, en lista: "¿cuántos pasos?", "¿hacia qué lado gira?", "¿qué hace al llegar?"
> — Panel preciso, título: "GIRA 90° A LA IZQUIERDA. AVANZA 4 PASOS. DETENTE FRENTE A LA PUERTA." — debajo, en lista: "qué hacer", "cuánto", "hacia dónde"
> — Leyenda inferior centrada, fuera de los paneles: "La diferencia no es el detalle decorativo: la instrucción precisa no deja ninguna decisión en manos del robot."

---

## 6. Módulo 1 · Ciclo 2 — Variables (Teoría · VARK Visual)

- **Misión:** Misión 1 · El idioma de las máquinas
- **Territorio:** Explorador
- **Ubicación:** Teoría principal del ciclo, variante Visual.
- **Recurso (`imageAsset`):** `m1-c2-teoria-variable-nombre`
- **Resolución recomendada:** 1600×2000 px (4:5)
- **Formato recomendado:** PNG en la generación inicial; candidato a **SVG** en re-trazado posterior.
- **Estilo visual:** el de la guía única de arriba, Plantilla B (dos paneles apilados).

**Prompt completo:**

> Infografía comparativa de dos paneles para una app educativa de programación, modo oscuro.
>
> COMPOSICIÓN: dos paneles rectangulares del mismo ancho, apilados verticalmente. Panel superior = VALOR SUELTO (vago). Panel inferior = VALOR CON NOMBRE (preciso). Entre ambos, una flecha corta apuntando hacia abajo con una etiqueta pequeña "dale un nombre".
>
> ESTILO: interfaz "glassmorphism" oscura, paneles translúcidos con bordes finos luminosos, sin fotorrealismo — formas geométricas simples, coherente con un diagrama de producto SaaS.
>
> COLORES: fondo casi negro #0a0a0f. Panel vago (superior): borde PUNTEADO ámbar #f59e0b, relleno ámbar al 8%. Panel preciso (inferior): borde SÓLIDO verde esmeralda #10b981, relleno esmeralda al 8%. Acento cian #06b6d4 en la palabra "edad" dentro del panel preciso. Flecha central y su etiqueta en gris azulado #94a3b8. Texto principal blanco hueso #f8fafc, texto secundario gris azulado #94a3b8.
>
> ICONOS: tres signos de interrogación (?) pequeños junto a las preguntas del panel vago. Un pequeño icono de etiqueta/tag junto al nombre "edad" en el panel preciso. Un icono outline minimalista de contenedor/caja, pequeño, como ancla temática, en la esquina superior del panel vago.
>
> DISTRIBUCIÓN: formato vertical 4:5. Panel vago ocupa el 40% superior, panel preciso el 40% inferior, con la flecha y su etiqueta en el 10% central, y una leyenda final en el 10% inferior, fuera de ambos paneles.
>
> ELEMENTOS DE TEXTO (incluir literalmente):
> — Panel vago, título: "20" — debajo, en lista: "¿20 qué cosa?", "¿por qué aparece varias veces en el programa?", "¿qué pasa si cambia?"
> — Panel preciso, título: "EDAD = 20" — debajo, en lista: "nombre: edad", "valor: 20", "se puede leer y actualizar donde haga falta"
> — Leyenda inferior centrada, fuera de los paneles: "Un número suelto no dice nada de sí mismo. El mismo número con nombre se puede leer, reutilizar y cambiar sin reescribir el programa entero."

---

## 7. Módulo 1 · Ciclo 3 — Entrada de datos (input) (Teoría · VARK Visual)

- **Misión:** Misión 1 · El idioma de las máquinas
- **Territorio:** Explorador
- **Ubicación:** Teoría principal del ciclo, variante Visual.
- **Recurso (`imageAsset`):** `m1-c3-teoria-pregunta-input`
- **Resolución recomendada:** 1600×2000 px (4:5)
- **Formato recomendado:** PNG en la generación inicial; candidato a **SVG** en re-trazado posterior.
- **Estilo visual:** el de la guía única de arriba, Plantilla B (dos paneles apilados).

**Prompt completo:**

> Infografía comparativa de dos paneles para una app educativa de programación, modo oscuro.
>
> COMPOSICIÓN: dos paneles rectangulares del mismo ancho, apilados verticalmente. Panel superior = LLAMADA SIN PREGUNTAR (vago). Panel inferior = PREGUNTA, ESPERA Y GUARDA (preciso, dos líneas de código). Entre ambos, una flecha corta apuntando hacia abajo con una etiqueta pequeña "pregúntale al usuario".
>
> ESTILO: interfaz "glassmorphism" oscura, paneles translúcidos con bordes finos luminosos, sin fotorrealismo — iconografía plana tipo robot/pantalla, coherente con un diagrama de producto SaaS.
>
> COLORES: fondo casi negro #0a0a0f. Panel vago (superior): borde PUNTEADO ámbar #f59e0b, relleno ámbar al 8%. Panel preciso (inferior): borde SÓLIDO verde esmeralda #10b981, relleno esmeralda al 8%. Flecha central y su etiqueta en gris azulado #94a3b8. Texto principal blanco hueso #f8fafc, texto secundario gris azulado #94a3b8.
>
> ICONOS: tres signos de interrogación (?) pequeños junto a las preguntas del panel vago. En el panel preciso, tres iconos pequeños en línea junto a cada parte: un globo de diálogo (pregunta), un reloj/pausa (espera), una caja con check (guarda).
>
> DISTRIBUCIÓN: formato vertical 4:5. Panel vago ocupa el 40% superior, panel preciso el 40% inferior (con las dos líneas de código en fuente monoespaciada), con la flecha y su etiqueta en el 10% central, y una leyenda final en el 10% inferior, fuera de ambos paneles.
>
> ELEMENTOS DE TEXTO (incluir literalmente):
> — Panel vago, título: "SALUDAR()" — debajo, en lista: "¿a quién saluda?", "¿de dónde saca el nombre?", "¿qué hace si no lo sabe?"
> — Panel preciso, título (dos líneas, monoespaciado): "NOMBRE = INPUT(\"¿CÓMO TE LLAMAS?\")" y "SALUDAR(NOMBRE)" — debajo, en lista: "pregunta: qué muestra en pantalla", "espera: se detiene hasta que respondes", "guarda: la respuesta queda en la variable"
> — Leyenda inferior centrada, fuera de los paneles: "Sin preguntar, el programa tendría que adivinar quién eres. input() reemplaza esa adivinanza por una pregunta real, y una espera real."

---

## 8. Módulo 2 · Ciclo 1 — Condiciones evaluables (Teoría · VARK Visual)

- **Misión:** Misión 2 · Decisiones que la máquina entiende
- **Territorio:** Estratega
- **Ubicación:** Teoría principal del ciclo, variante Visual.
- **Recurso (`imageAsset`):** `m2-c1-teoria-condicion-paraguas`
- **Resolución recomendada:** 1600×2000 px (4:5)
- **Formato recomendado:** PNG en la generación inicial; candidato a **SVG** en re-trazado posterior. Como la pieza 4, incorpora un **rombo de decisión** — es la excepción de Plantilla B descrita en la guía de estilo.
- **Estilo visual:** el de la guía única de arriba, Plantilla B (dos paneles apilados) con rombo de decisión en el panel preciso.

**Prompt completo:**

> Infografía comparativa de dos paneles para una app educativa de programación, modo oscuro.
>
> COMPOSICIÓN: dos paneles rectangulares del mismo ancho, apilados verticalmente. Panel superior = IDEA VAGA (rectángulo simple). Panel inferior = CONDICIÓN EVALUABLE (contiene un ROMBO de decisión con dos ramas etiquetadas SÍ / NO hacia dos resultados). Entre ambos, una flecha corta apuntando hacia abajo con una etiqueta pequeña "hazla evaluable".
>
> ESTILO: interfaz "glassmorphism" oscura, iconografía plana de diagrama de flujo real (rombo = decisión, rectángulo = proceso/resultado), sin fotorrealismo, coherente con un producto SaaS educativo.
>
> COLORES: fondo casi negro #0a0a0f. Panel vago (superior): borde PUNTEADO ámbar #f59e0b, relleno ámbar al 8%. Rombo de decisión (panel inferior): borde SÓLIDO cian #06b6d4, relleno cian al 8%. Los dos nodos de resultado dentro del panel inferior: borde SÓLIDO verde esmeralda #10b981, relleno esmeralda al 8%. Etiquetas "SÍ"/"NO" en violeta #7c3aed. Flecha central y su etiqueta en gris azulado #94a3b8. Texto principal blanco hueso #f8fafc, texto secundario gris azulado #94a3b8.
>
> ICONOS: tres signos de interrogación (?) pequeños junto a las preguntas del panel vago. Un pequeño ícono de sensor/gota de lluvia dentro del rombo. Un ícono de paraguas abierto junto al resultado SÍ y uno de paraguas cerrado junto al resultado NO, ambos del mismo tamaño (ningún resultado más importante que el otro).
>
> DISTRIBUCIÓN: formato vertical 4:5. Panel vago ocupa el 35% superior, panel preciso (con su rombo y dos resultados) el 45% inferior, con la flecha y su etiqueta en el 10% central, y una leyenda final en el 10% restante, fuera de ambos paneles.
>
> ELEMENTOS DE TEXTO (incluir literalmente):
> — Panel vago, título: "SI HACE MAL TIEMPO, ABRE EL PARAGUAS" — debajo, en lista: "¿qué cuenta como mal tiempo?", "¿lluvia? ¿viento? ¿nublado?", "¿quién decide?"
> — Panel preciso, rombo: "¿EL SENSOR DE LLUVIA DETECTA GOTAS?" — resultado SÍ: "Abre el paraguas" — resultado NO: "Mantenlo cerrado"
> — Leyenda inferior centrada, fuera de los paneles: "La diferencia no es el detalle: una condición evaluable siempre puede responderse con SÍ o NO — nunca depende."

---

## Cobertura y alcance de este documento

Estas son las **8 únicas** ilustraciones que actualmente tienen un `imagePrompt` redactado en el código (`ciclo1-instrucciones-precisas.ts`, `ciclo2-variables.ts`, `ciclo3-input.ts`, `module2.ts` — verificado por búsqueda exhaustiva en `frontend/src`), en dos grupos: remediación Nivel 2 (secciones 1–4) y teoría principal/VARK Visual (secciones 5–8, agregadas en esta vuelta — cerraban el hueco que dejaba la vuelta anterior).

No incluidas, y por qué — cada una es una decisión deliberada, no un olvido:
- **Remediación Nivel 1** ("ejemplo resuelto paso a paso", `medium: 'ejemplo_comentado'`) de cada ciclo: es un walkthrough numerado y secuencial (1., 2., 3. …), no una comparación estática de dos estados — forzarlo a una sola imagen perdería la secuencia que es justamente su valor pedagógico. El tipo (`RemediationIllustration extends VisualAsset`) ya soporta `imageAsset`/`imageUrl` si en el futuro se decide ilustrarlo de otra forma, pero no se redactó prompt porque el medio actual no lo pide.
- **Remediación Nivel 3**: no tiene campo de ilustración en ningún ciclo — solo explica la solución y deja continuar (por diseño, ver `RemediationStep` en `moduleExperience.ts`).
- **Reforzamientos "ejemplo"/"reto" del menú de decisión** (`Reinforcement`, kind `ejemplo`/`reto`): el tipo no tiene ningún campo de medio visual/diagrama hoy (ni `medium: 'infografia'` ni `VisualAsset`) — son párrafos de texto con, opcionalmente, su propio `pythonBridge`. No hay contenido estructurado que una imagen deba reemplazar, así que no se extendió el tipo para esto en este sprint (evita introducir una capacidad sin contenido real detrás).

Cuando exista Módulo 2 en adelante con más ciclos, o se decida ilustrar alguno de los casos listados arriba, este documento se amplía con la misma estructura por sección y la misma guía de estilo — no se crea una guía nueva por lote.
