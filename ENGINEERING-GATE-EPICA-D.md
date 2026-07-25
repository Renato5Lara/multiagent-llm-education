# Engineering Gate — Épica D: Modernización de la experiencia visual

> Modernización visual pura (UI/UX) sobre una base ya estabilizada
> (`epic-c-complete`). No introduce comportamiento nuevo, no toca el
> Runtime ni ningún contrato Boundary/HTTP — solo presentación. Sigue
> la misma disciplina de "cambios pequeños" que Épicas B/C: un
> commit por superficie, sin reescribir tokens ya usados en cientos
> de lugares.

- **Fecha de inicio:** 2026-07-25
- **Punto de partida:** tag `epic-c-complete` (`4db318e`).
- **Objetivo de la Épica D:** elevar la calidad visual y la
  experiencia de uso sin modificar la lógica de negocio, el runtime
  multiagente ni los contratos existentes. Ningún commit de esta
  épica mezcla cambio funcional con cambio visual — si un commit
  necesita ambos, se divide en dos.

## Fase 1 — Fundamentos de diseño

### Decisión: regla híbrida de color

Referencia visual aportada por el tesista (CodeMorph): estética
violeta/índigo dominante. El proyecto ya documenta en `CLAUDE.md` una
paleta cian-primaria/violeta-secundaria, usada en cientos de lugares
(`neural-glow` cian, `neural-violet` #ce5dff). Revertir ese balance
globalmente reescribiría el token compartido `bg-primary` que usan
`Ejecutar`, `Continuar`, `Comprobar`, `Enviar` en toda la plataforma —
alto riesgo, sin beneficio real.

**Decisión del tesista: regla híbrida, no reemplazo total.**

- 🟣 **Violeta/índigo** (`neural-brand` #7c3aed, nuevo token) — marca,
  hero, CTA que **inicia** una acción nueva (ej. "Comenzar
  diagnóstico", "Continuar misión", "Ver ruta adaptativa", titulares
  de bienvenida).
- 🔵 **Cian** (`neural-glow` #00dbe7, existente, sin tocar) — todo lo
  que representa **estado en vivo**: activo, progreso, ejecución,
  streaming, indicadores del sistema multiagente (`Ejecutar →`,
  `Comprobar`, nodo "ACTIVO" del mapa de aprendizaje, stat tiles,
  badge de porcentaje).

**Por qué es aditivo, no una migración:** `neural.brand` /
`neural.brand-bright` son tokens NUEVOS en `tailwind.config.js`,
distintos de `neural.violet` (#ce5dff, ya usado en el anillo de
dominio y acentos del tutor — se deja intacto). Ningún uso existente
de `bg-primary`/`text-neural-glow` cambia de significado.

### Tokens nuevos (`tailwind.config.js`, `index.css`)

```
neural.brand         #7c3aed   — CTA principal, marca, hero
neural.brand-bright  #a78bfa   — texto/glow claro sobre fondo oscuro

.gradient-text-brand  — degradado de marca para titulares hero (NO usar en texto de cuerpo ni etiquetas chicas — pierde legibilidad)
.glow-brand / .glow-brand-lg — sombra de marca, distinta de .glow-violet existente
```

### Tipografía / espaciado / radios / duraciones

No se introduce una escala nueva — la escala de Tailwind (`text-xs`
… `text-3xl`, espaciado `4`/`8`/etc., `rounded-2xl` ya convención de
`glass-panel`) ya cubre lo necesario. Se amplía tamaño/línea de los
titulares hero puntualmente donde corresponde (ver Dashboard abajo),
no se inventa un token de tamaño nuevo sin un consumidor real
(regla de derivación, `CLAUDE.md`).

## Superficies migradas

### Dashboard del estudiante (`Dashboard.tsx`) — ✅ primer commit

- `Greeting`: nombre en `gradient-text-brand`, `text-3xl` (antes
  `text-2xl` plano).
- `NextMissionCard` ("Siguiente paso recomendado"): badge, glow
  ambiental y los 4 botones de acción (`Comenzar diagnóstico`,
  `Rendir Post-Test`, `Continuar misión`, `Ver ruta adaptativa`) pasan
  a `neural-brand`.
- **Sin tocar** (correctamente cian, por la regla híbrida):
  `StatTile` (avance/misiones/competencias/dificultad),
  `DifficultyLevelCard` (anillo, ya violeta claro existente — no se
  toca), nodo "ACTIVO" y badge "% completado" del mapa de
  aprendizaje, panel del Tutor.

**Hallazgo real de esta sesión (no un bug del código, un artefacto del
entorno dev):** el servidor de Vite no regeneró las utilidades
Tailwind derivadas del nuevo token `neural.brand` hasta reiniciarlo —
`bg-neural-brand` no existía en absoluto en el CSS servido pese a
estar en `tailwind.config.js` (confirmado via
`getComputedStyle().backgroundColor` = `rgba(0,0,0,0)` antes del
reinicio, `rgb(124,58,237)` después). Si una futura sesión agrega un
token de color nuevo y no lo ve reflejado en el navegador, reiniciar
el dev server antes de asumir un error de implementación.

### Laboratorio de Python (`PythonBridge.tsx`) — ✅ segundo commit

**Hallazgo de jerarquía real** (no solo estético): antes de este
commit, `Ejecutar →` y `Continuar →` eran ambos del mismo cian
(`bg-primary` por defecto del `Button`) — dos acciones con
significado muy distinto (ejecutar de nuevo vs. avanzar de etapa) se
veían idénticas, generando ambigüedad momentánea real.

- `Continuar →` (las 2 instancias: tras solución revelada y tras
  acierto) → `neural-brand`, mismo patrón visual que el CTA del
  Dashboard (`bg-neural-brand text-white hover:bg-neural-brand/90`,
  constante `CONTINUE_BRAND_BTN`).
- **Sin tocar** (correctamente cian/ghost, por la regla híbrida):
  `Ejecutar`/`Cargando Python…`, `Enviar` (panel de `input()` real),
  `Comprobar`/`Comprobar secuencia`, `Cancelar`, `Ver solución`,
  el chip `OBSÉRVALO`/modo (ya usa `neural-violet` existente, sin
  cambios), el encabezado `ESTO YA ES PYTHON` (ya usa `neural-glow`).
- Alcance deliberadamente acotado a `PythonBridge.tsx` — los botones
  "Continuar" de `ModuleExperienceView.tsx` (curiosidad, concepto,
  remediación) NO se tocan en este commit; quedan para la fase de
  Navegación.

Validado en navegador real (Módulo 2, Ciclo "Decisiones que la
máquina entiende"): `Ejecutar →` corre el código (cian), tras acierto
aparece `Continuar →` (violeta) junto a él, distinción visual clara.
Capturas en `docs/qa/epica-d-lab/`.

**Revisión de equilibrio visual (pausa pedida por el tesista antes de
avanzar a Navegación) — 4 preguntas, respondidas contra la captura
real:**

1. *¿El botón violeta compite con el editor?* No — `size="sm"`, va
   junto a Ejecutar, debajo del editor/consola; el editor sigue
   siendo el elemento de mayor contraste y espacio de la pantalla.
2. *¿Se percibe el cambio de contexto?* Sí — color y texto distintos
   (doble señal), lado a lado con Ejecutar, comparación inmediata.
3. *¿La transición es natural?* Sí — cian (Ejecutar) → verde
   ("✓ Exacto") → violeta (Continuar) ya se lee como una progresión
   tipo semáforo, sin inventar un patrón nuevo.
4. *¿Rompe el equilibrio del Lab?* No — el violeta ya aparecía en la
   misma pantalla (chip `OBSÉRVALO`, `neural-violet` existente) antes
   de este commit; gana un segundo uso coherente, no un color nuevo
   irrumpiendo.

Con esto, la Fase 1 (Foundation: Dashboard + Lab) queda validada
visualmente. Continúa Fase 2 (Navegación) con el mismo alcance
acotado.

## Sistema semántico de color (formalizado tras revisión del Lab)

No es una paleta nueva — es la semántica que ya emergió en los
Commits 1–2, documentada explícitamente para que cualquier
componente nuevo de esta épica sepa qué token usar sin adivinar.
Auditado contra el código real, no supuesto:

| Semántica | Token | Dónde vive hoy |
|---|---|---|
| **Marca / CTA principal / avanzar** | `neural-brand` (#7c3aed, nuevo) | `NextMissionCard` (Dashboard), `Continuar →` (`PythonBridge.tsx`) |
| **En vivo / ejecución / activo** | `neural-glow` (#00dbe7, existente) | `Ejecutar`, `Enviar`, `Comprobar`, stat tiles, nodo "ACTIVO", badge de progreso |
| **Éxito / completado** | `emerald-400`/`neural-pulse` (#00fb83, existentes, ya coherentes entre sí) | "✓ Exacto", nodo completado del mapa de aprendizaje, logros |
| **Diagnóstico recuperable** (el estudiante puede reintentar) | `amber-400`/`amber-500` (existente) | `PythonErrorCard` — un error de Python NUNCA es rojo aquí a propósito: es material de aprendizaje, no una falla del sistema |
| **Falla crítica** (el sistema, no el estudiante, falló) | `red-400`/`destructive` (existente) | `loadError` (Pyodide no cargó), errores de red/servidor |
| **Acento secundario existente** (sin rol nuevo) | `neural-violet` (#ce5dff, existente) | Anillo de dominio, chip de modo (`OBSÉRVALO`, etc.), acentos del tutor — no se reasigna a "marca" para no romper significado ya aprendido por el usuario |

**Regla de aplicación:** ante un componente nuevo, la pregunta no es
"qué color se ve mejor" sino "¿qué representa esta acción?" — si
mueve al estudiante a lo siguiente, `neural-brand`; si es el sistema
trabajando/ejecutando ahora mismo, `neural-glow`; el resto ya tiene
dueño en la tabla de arriba.

### Navegación (`Sidebar.tsx` + CTAs de avance) — ✅ tercer commit

- `Sidebar.tsx`: logo/marca de cabecera y estado activo del link
  (fondo, borde, ícono, punto indicador) pasan de `neural-glow` a
  `neural-brand` — "dónde estás parado" es navegación/marca, no un
  estado en vivo del sistema. Se retiró `glow-active` del punto
  indicador (esa animación estaba afinada para el cian; no se mezcla
  con animaciones en este commit, ver alcance del gate).
- `ModuleExperienceView.tsx`: las 6 instancias de CTA de avance
  (`Comenzar →`, 5× `Continuar →`) pasan a `neural-brand` vía la
  constante compartida `CONTINUE_BRAND_BTN`.

**Hallazgo real durante la validación en navegador (no en el plan
original):** el barrido inicial, acotado a `Sidebar.tsx` +
`ModuleExperienceView.tsx` como se había acordado, dejó una
inconsistencia visible de inmediato — el botón "Continuar →" de
`CuriosityFactCard.tsx` (pantalla "¿Sabías que...?", la primera de
cada ciclo) seguía en cian, porque vive en un archivo hermano, no en
`ModuleExperienceView.tsx`. Se amplió el barrido —misma regla ya
aprobada, ningún criterio nuevo— a los demás CTAs de avance de
`components/experience/`: `CuriosityFactCard.tsx` ("Continuar →"),
`CuriosityOpening.tsx` ("Ver la respuesta →"), `ConceptStep.tsx`
("Ponerlo a prueba →"), `ConceptPrimerCard.tsx` ("Ahora úsalo →"), y
el CTA de cierre de misión en `ModuleExperienceView.tsx` ("Seguir con
la siguiente misión →" / "Finalizar misión →"). Verificado con
`grep` que no queda ningún CTA de avance (`→`) sin el token de marca
en `components/experience/`.

**Deliberadamente fuera de este commit:** `LearningPath.tsx`
("Comenzar misión →") — mismo criterio, pero es una página distinta
(`pages/estudiante/`), no un componente de experiencia; candidato
natural para el próximo commit de Navegación/Rutas si se decide
extender la regla a esa capa.

Build limpio. Validado en navegador real: Sidebar con marca/estado
activo violeta en ambas rutas del menú, recorrido completo del ciclo
(curiosidad → concepto → práctica → Python) con "Continuar" violeta
consistente en cada paso. Capturas en `docs/qa/epica-d-navigation/`.

### Animaciones (`Commit 4`) — ✅ cuarto commit

**Hallazgo principal, no en el plan original:** las clases
`animate-in`/`fade-in`/`slide-in-from-*` ya usadas en 99 lugares de
54 archivos de toda la plataforma (no solo en las superficies de esta
épica) **nunca generaban CSS** — el plugin `tailwindcss-animate` (del
que dependen esas clases, estándar en proyectos shadcn/ui) nunca se
instaló. Confirmado programáticamente: `document.styleSheets` no
contenía ninguna regla `.animate-in`/`.fade-in` antes de este commit.
No eran animaciones sutiles — eran clases sin efecto alguno, en
producción, desde que se escribieron. Instalar y registrar el plugin
(`npm install -D tailwindcss-animate` + `plugins: [tailwindcssAnimate]`
en `tailwind.config.js`) reactiva las 99 de un solo cambio aditivo,
sin tocar un solo componente.

**Sistema semántico de movimiento** (mismo espíritu que la tabla de
color — mapeado a los valores reales que Tailwind puede generar sin
config nueva, no a milisegundos exactos inalcanzables):

| Tier | Clase Tailwind | Uso |
|---|---|---|
| Feedback inmediato (hover/focus) | `duration-150` | Hover de botones, estado activo del Sidebar |
| Aparición/desaparición de elemento | `duration-200`–`duration-300` | Tarjetas, paneles, notas del tutor |
| Transición entre pantallas | `duration-300` (techo) | Curiosidad→Concepto→Práctica, entrada de cada fase |

**Excepción documentada, no un descuido:** las barras/anillos que
rellenan un VALOR real (`DifficultyLevelCard` en Dashboard.tsx,
barras de progreso en `ModuleExperienceView.tsx`) se dejaron en
`duration-500`/`duration-700` a propósito — no son una transición de
aparición/pantalla, son una animación de "llenado" de dato, donde
más duración se percibe como más precisión, no como lentitud. Igualar
esta categoría a la regla de 300ms haría que el porcentaje "saltara"
en vez de rellenarse.

**Cambios concretos** (solo en los archivos ya trabajados en Fases
1–3 de esta épica — ver alcance abajo):
- Recorte de `duration-500`/`duration-700` → `duration-300` en 14
  entradas de pantalla/tarjeta (`PythonBridge.tsx`,
  `ModuleExperienceView.tsx`, `CuriosityOpening.tsx`,
  `CuriosityFactCard.tsx`, `ConceptStep.tsx`, `ConceptPrimerCard.tsx`).
- Recorte de `duration-200` → `duration-150` en el hover/activo del
  Sidebar (es feedback inmediato, no aparición).
- Hover con elevación sutil + resplandor de marca
  (`hover:-translate-y-0.5 hover:shadow-lg hover:shadow-neural-brand/25`,
  150ms) en los 3 constantes de botón de marca ya introducidos
  (`CONTINUE_BRAND_BTN` ×2, `CTA_BRAND_BTN`) — **no** en el `Button`
  compartido por defecto (afectaría cientos de usos fuera de esta
  épica).

**Deliberadamente fuera de alcance:** `components/module/`,
`components/learningJourney/`, `components/engage/`,
`components/gamification/` — verificado que es el sistema de
fallback que atiende los 7 módulos del currículo sin
`ModuleExperienceDefinition` autorada todavía (solo Módulo 1 y 2 la
tienen). No es código muerto, pero es una superficie distinta a la
que ha cubierto esta épica (Dashboard, Lab, Navegación); sus ~80
usos de `duration-*` no se tocaron. El plugin recién instalado los
beneficia igual de forma pasiva (sus propias clases `animate-in` ya
escritas también empiezan a funcionar), sin que haya hecho falta
tocar ningún archivo de esas carpetas.

Build limpio. Validado: la regla CSS de `tailwindcss-animate` existe
realmente en el navegador (antes: 0 reglas; después: reglas reales
para `.animate-in`/`.fade-in`); el `transform` de elevación se aplica
en hover (`matrix(1,0,0,1,0,-2)`, confirmado vía
`getComputedStyle`).

## Próximos pasos (no en este commit)

- `feature/epica-d-dashboard` (continuación): resto de tarjetas de
  logros/accesos rápidos si aportan algo más allá de lo ya aplicado.
- `feature/epica-d-navigation`: Sidebar (estado activo del link) +
  botones "Continuar" de `ModuleExperienceView.tsx` bajo la misma
  regla híbrida ya validada en el Lab.
- `feature/epica-d-animations`: detalles premium (microanimaciones,
  skeleton loaders) — última fase, según lo acordado con el tesista.
