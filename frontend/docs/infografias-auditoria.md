# Auditoría de infografías — estado completo

Auditoría de **todas** las infografías/ilustraciones de la plataforma (teoría, remediación, ejemplos, VARK Visual), hecha leyendo el código de contenido (`frontend/src/lib/experiences/*.ts`) y el de renderizado (`ConceptStep.tsx`, `ModuleExperienceView.tsx`, `IllustrationVisual.tsx`, `illustrationAssets.ts`). No genera ninguna imagen — es un inventario y una clasificación de estado.

Para los prompts completos de cada pieza, ver `frontend/docs/infografias-prompts.md`. Este documento responde una pregunta distinta: **qué existe, qué falta, y qué falta para cada una específicamente** — no cómo generarla.

---

## Resumen ejecutivo

| Métrica | Cantidad |
|---|---|
| Infografías/ilustraciones con medio genuinamente visual (diagrama/infografía) — el universo que esta auditoría clasifica | **8** |
| Categorías adicionales revisadas y excluidas del inventario "pendiente" (justificado, ver más abajo): Remediación N1 (4 ciclos, secuencia textual) + reforzamientos "ejemplo"/"reto" (sin medio visual definido) | 2 categorías |
| Con `imagePrompt` redactado | **8 / 8** (100% de las que corresponden) |
| Con `imageAsset` (clave) ya declarada en el contenido | **8 / 8** |
| Con integración de componente lista (imagen real reemplaza el fallback cuando exista) | **8 / 8** (validado en build + en vivo) |
| Con imagen real ya generada y mostrándose | **0 / 8** — ninguna todavía (por diseño de este sprint: no se generó ninguna) |
| Clasificadas **LISTA PARA GENERAR** | **8** |
| Clasificadas **PENDIENTE** (sin prompt, sin imagen) | **0** entre las que corresponden a un medio visual |
| Clasificadas **COMPLETA** | **0** — ninguna pieza tiene imagen real todavía; ese es el trabajo que sigue, fuera de este sprint por instrucción explícita ("no generar imágenes") |

---

## Tabla de estado

| Pantalla | Prompt disponible | Imagen disponible | Estado |
|---|---|---|---|
| M1·C1 — Remediación N2 (Analogía visual: título vs. pasos) | Sí | No | LISTA PARA GENERAR |
| M1·C2 — Remediación N2 (Analogía visual: caja vacía → nombre → valor) | Sí | No | LISTA PARA GENERAR |
| M1·C3 — Remediación N2 (Analogía visual: pregunta impresa → respuesta → dato) | Sí | No | LISTA PARA GENERAR |
| M2·C1 — Remediación N2 (Analogía visual: idea vs. condición) | Sí | No | LISTA PARA GENERAR |
| M1·C1 — Teoría principal / VARK Visual (Infografía) | Sí | No | LISTA PARA GENERAR |
| M1·C2 — Teoría principal / VARK Visual (Infografía) | Sí | No | LISTA PARA GENERAR |
| M1·C3 — Teoría principal / VARK Visual (Infografía) | Sí | No | LISTA PARA GENERAR |
| M2·C1 — Teoría principal / VARK Visual (Infografía) | Sí | No | LISTA PARA GENERAR |
| M1/M2 — Remediación N1, los 4 ciclos (Ejemplo resuelto paso a paso) | No (no aplica — ver nota) | No | N/A — no es una infografía |
| M1/M2 — Reforzamientos "ejemplo"/"reto" del menú de decisión | No (no aplica — ver nota) | No | N/A — sin medio visual definido |

*(Las últimas dos filas se listan por completitud del inventario que pide la auditoría — "teoría, remediación, ejemplos, VARK visual" — pero no se clasifican con la escala COMPLETA/LISTA PARA GENERAR/PENDIENTE porque no representan un diagrama pendiente de generar; ver justificación abajo.)*

---

## Auditoría detallada por pieza

Para cada una de las 8 piezas que sí son un diagrama/infografía real, los 5 chequeos pedidos:

| Pantalla | Existe imagen | Existe prompt | Falta prompt | Falta imagen | Falta integración |
|---|---|---|---|---|---|
| M1·C1 Remediación N2 | No | Sí (desde 2ª vuelta) | No | **Sí** | No — componente listo |
| M1·C2 Remediación N2 | No | Sí (desde 2ª vuelta) | No | **Sí** | No — componente listo |
| M1·C3 Remediación N2 | No | Sí (desde 2ª vuelta) | No | **Sí** | No — componente listo |
| M2·C1 Remediación N2 | No | Sí (desde 2ª vuelta) | No | **Sí** | No — componente listo |
| M1·C1 Teoría/Visual | No | Sí (**nuevo**, esta vuelta) | No | **Sí** | No — componente listo |
| M1·C2 Teoría/Visual | No | Sí (**nuevo**, esta vuelta) | No | **Sí** | No — componente listo |
| M1·C3 Teoría/Visual | No | Sí (**nuevo**, esta vuelta) | No | **Sí** | No — componente listo |
| M2·C1 Teoría/Visual | No | Sí (**nuevo**, esta vuelta) | No | **Sí** | No — componente listo |

"Falta integración" = No en las 8 significa: el componente ya sabe mostrar la imagen real en cuanto exista (`imageUrl`/`imageAsset` → `IllustrationVisual`) y cae al contenido estructurado/textual existente mientras no exista — verificado con build limpio, TypeScript limpio, y una prueba en vivo con un archivo de imagen temporal (revertida) que confirmó ambos caminos: con imagen se muestra la imagen, sin imagen se muestra el diagrama/comparación de siempre.

---

## Categorías excluidas del inventario de "pendientes" — y por qué

Objetivo de esta auditoría incluía explícitamente "ejemplos" y todas las variantes VARK; estas dos categorías SÍ se revisaron, y la conclusión es que **no tienen contenido visual estructurado que una imagen deba reemplazar** — lo cual es distinto de "está pendiente":

- **Remediación Nivel 1** (`medium: 'ejemplo_comentado'`, mediumLabel "Ejemplo resuelto paso a paso") en los 4 ciclos: es un walkthrough numerado (1. 2. 3. …), no una comparación de dos estados. El tipo `RemediationIllustration` ya extiende `VisualAsset` (soporta `imageUrl`/`imageAsset` si algún día se decide ilustrarlo), pero convertir una secuencia de pasos en una sola imagen estática perdería exactamente lo que la hace útil — no se redactó prompt por esa razón pedagógica, no por omisión.
- **Remediación Nivel 3**: no tiene campo de ilustración en ningún ciclo — por diseño, solo explica la solución y deja avanzar (`RemediationStep.illustration` es opcional y el Nivel 3 nunca lo define).
- **Reforzamientos "ejemplo"/"reto"** del menú de decisión (`Reinforcement`): el tipo no declara ningún medio visual/diagrama hoy — ninguno de los reforzamientos existentes usa `medium: 'infografia'` o `'diagrama'` (verificado por búsqueda exhaustiva). Son párrafos de texto, opcionalmente con su propio `pythonBridge`. Extender el tipo `Reinforcement` con `VisualAsset` sin que ningún contenido real lo use todavía sería introducir una capacidad vacía — se dejó fuera de este sprint deliberadamente, no por descuido.

Si en una iteración futura se decide que alguna de estas categorías sí necesita una infografía real, el patrón a seguir es el mismo que ya existe: declarar `imageAsset`/`imagePrompt` en el contenido (extendiendo el tipo con `VisualAsset` donde falte) y registrar la clave en `illustrationAssets.ts` — la arquitectura ya es genérica, no haría falta un mecanismo nuevo.

---

## Preparación del componente (objetivo 3) — estado

Ya estaba completamente implementada desde el sprint anterior para remediación, y se confirmó en este sprint que cubre teoría/VARK Visual sin cambios adicionales de código (el tipo `ConceptVariant` ya extendía `VisualAsset` desde la segunda vuelta):

- `hasIllustrationImage(asset)` — helper único en `illustrationAssets.ts`: `true` si `imageUrl` o `imageAsset` (resuelto contra `ILLUSTRATION_ASSETS`) existen.
- `ConceptStep.tsx` (teoría): `hasIllustrationImage(variant) ? <IllustrationVisual .../> : variant.infographic && (<comparación de nodos>)`.
- `ModuleExperienceView.tsx` → `RemediationStepView` (remediación): `hasIllustrationImage(step.illustration) ? <IllustrationVisual .../> : body.map(...)`.
- `IllustrationVisual.tsx`: `<img src={imageUrl || resolveIllustrationAsset(imageAsset)} />` — acepta PNG/SVG/WebP indistintamente (el navegador resuelve el formato, el componente no distingue).

Sin código disperso: **un solo archivo** (`illustrationAssets.ts`) concentra el registro `ILLUSTRATION_ASSETS: Record<string, string>` para las 8 claves — ningún ciclo ni componente importa una ruta de imagen directamente.

Se eliminó además `lib/experiences/imagePrompts.ts`, un mecanismo de recolección de prompts alternativo y no utilizado (0 imports en todo el proyecto, verificado) que había quedado de un intento anterior — exactamente la clase de "ruta dispersa" que el objetivo 4 pide evitar.

---

## Validación de este sprint

- `npx tsc --noEmit` — limpio.
- `npx eslint` sobre los 5 archivos tocados — sin hallazgos.
- `npm run build` — exitoso, sin warnings nuevos.
- En vivo (navegador real, servidor de desarrollo): confirmado que una infografía de teoría (M1·C1) sin imagen registrada sigue mostrando la comparación vago/preciso de siempre; confirmado que, con una entrada temporal de prueba en `ILLUSTRATION_ASSETS` (revertida de inmediato), la misma pantalla muestra la imagen real en su lugar. Confirmado también que una infografía de teoría de un ciclo distinto (M2·C1), sin ninguna entrada de prueba, sigue mostrando su comparación estructurada intacta — cero regresión de compatibilidad.
