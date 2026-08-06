# Sesión UX/UI — Paso 3: Clasificación formal (sin implementar)

## Metadata

- **Fecha:** 2026-08-05
- **Rama:** `investigacion/sesion-ux-ui`
- **Protocolo:** observar → medir → clasificar → **decidir** → implementar.
  Este documento es Paso 3 — clasificar cada hallazgo sobreviviente de
  Paso 2 en una de cuatro categorías (defecto real / decisión UX-producto
  / mejora opcional / buena práctica) y priorizarlo. **No se decide
  todavía si se implementa, ni se toca ningún archivo de código.** La
  apertura de implementación (Paso 4, fuera de este documento) requiere
  aprobación explícita separada, ficha de una página por hallazgo que se
  decida remediar, y Engineering Gate de las 4 preguntas de `CLAUDE.md`.

---

## Clasificación

### Defectos reales

**H1 — vocabulario técnico interno sin traducir** (`arrays`, `algorithms`,
`loops`... → `ProgrammingConcept`, `programming_domain.py:18-53`, sin
tabla de labels ES equivalente a `COMPETENCY_LABELS`).

- **Tipo:** defecto de presentación semántica — la capa de traducción
  existe y funciona (probado con las 6 competencias del pre-test); le
  falta cobertura para los 26 conceptos de curso.
- **Impacto:** comprensión del estudiante (etiquetas en inglés sin
  significado pedagógico reconocible) y percepción de personalización
  del sistema (parece menos cuidado de lo que realmente es). **No
  afecta ninguna decisión del enjambre** — es puramente de proyección,
  el dato correcto ya llega al Boundary.
- **Riesgo de remediar:** bajo — mismo mecanismo ya extendido una vez
  (`_etiqueta()` + tabla), sin tocar Runtime ni reducers.
- **Prioridad:** **alta** dentro de este conjunto de hallazgos — es el
  único con causa raíz exacta, mecanismo de corrección ya probado, y
  impacto directo en cómo el estudiante interpreta su propia adaptación.
- **No se implementa en este documento.**

---

### Decisiones UX/producto (no defectos técnicos)

**H2 — panel "Recurso pedagógico generado" sin contexto de propósito**
(`GeneratedResourcePromptCard.tsx`, RFC-0011/3, CERRADA).

- **Tipo:** no es un defecto — es una funcionalidad cerrada y aprobada
  cuya presentación no comunica su propio propósito al estudiante.
- **Por qué no se clasifica como "defecto real":** corregirlo no es
  "arreglar código roto" — es decidir *qué debería entender el
  estudiante* al ver ese panel, lo cual depende de una pregunta de
  producto/pedagogía sin responder todavía: ¿el estudiante participa
  como corresponsable de generar su propio recurso adaptado (un rol
  activo, "coautor del reto"), o esta pantalla es un artefacto de v1
  que se diseñó aceptando esa fricción temporalmente, a la espera de
  una v2 con generación real (fuera de alcance explícito de RFC-0011,
  §4)? `ROADMAP-RFC-0011.md` no resuelve esta pregunta — describe el
  contrato técnico, no la intención pedagógica de exponerlo así.
- **Antes de decidir cualquier cambio, revisar (no hecho en esta
  sesión):**
  1. RFC-0011/3, Parte D, específicamente la ficha de cierre (§10 del
     roadmap) — para confirmar si hubo alguna discusión de UX/copy que
     este documento no encontró.
  2. Cómo se justifica esta capacidad en la redacción actual de la
     tesis (si ya se describe como "el estudiante recibe contenido
     adaptado" en algún capítulo, este panel contradice esa
     descripción tal como se presenta hoy).
  3. Si "el estudiante genera su propio recurso" es una capacidad que
     el jurado necesita ver explicada explícitamente, o si es preferible
     ocultarla/reformularla antes de la sustentación.
- **Prioridad:** media — no bloquea ningún recorrido, pero es visible
  en cualquier demo real de Misión 1 y puede generar una pregunta
  directa del jurado si no hay una respuesta preparada.
- **No se implementa en este documento.**

---

### Mejoras opcionales

**H3 — dos patrones de espera con pesos distintos** (checklist de 3
pasos vs. spinner con una línea).

- **Tipo:** no es un bug — Paso 2 confirmó que ambos patrones
  responden correctamente a operaciones reales de peso distinto
  (decisión adaptativa completa de fin de ciclo vs. ajuste ligero
  best-effort entre pasos). Unificarlos sería una falsa mejora: haría
  parecer que cada micro-paso del editor dispara una deliberación
  multiagente completa, cuando no es así.
- **Qué sí seguiría abierto como mejora opcional (sin urgencia):** una
  señal visual de intensidad proporcional al peso real de cada espera,
  para que el estudiante entienda instintivamente "esto es un ajuste
  rápido" vs. "esto es el sistema completo reevaluándome" — sin
  necesitar dos componentes visualmente desconectados como hoy.
- **Prioridad:** baja — ninguna de las dos implementaciones actuales
  es incorrecta ni confunde de forma medible; es una oportunidad de
  pulido, no una corrección.
- **No se implementa en este documento.**

---

### Buenas prácticas detectadas (no tocar, usar como referencia)

**H4 — UX de error del editor Pyodide** (`PythonBridge.tsx`, bloque de
`SyntaxError` real).

- Consola "sin salida" clara, caja de error con la línea exacta,
  explicación en lenguaje llano encima de un traceback real opcional
  y colapsado, panel de Tutor contextual explicando la causa y luego
  la corrección. No bloqueante, con ruta de recuperación evidente.
- **Recomendación explícita:** si en el futuro se abre cualquier
  iniciativa de mejora de errores en otras superficies de la
  plataforma (por ejemplo, mensajes de error de red, de validación de
  formularios, o del propio flujo de diagnóstico), este patrón debería
  citarse como la referencia de diseño ya validada — no reinventar.

---

### Cerrados (sin acción)

**H5** — retirado en Paso 2 por no reproducirse en el código
(`Dashboard.tsx:116-167` es internamente consistente).

**H6** — resuelto en Paso 2: la pantalla de resultados existe
(`/estudiante/post-test/:courseId`), Paso 1 no la alcanzó por tiempo.

---

## Tabla resumen

| # | Categoría | Prioridad | Acción en esta sesión |
|---|---|---|---|
| H1 | Defecto real | Alta | Ninguna — queda documentado, listo para una ficha de implementación futura |
| H2 | Decisión UX/producto | Media | Ninguna — requiere responder la pregunta de producto antes de que exista algo que implementar |
| H3 | Mejora opcional | Baja | Ninguna — candidato de pulido visual, sin urgencia |
| H4 | Buena práctica | — | Ninguna — se conserva como referencia |
| H5 | Cerrado | — | Ninguna |
| H6 | Cerrado | — | Ninguna |

---

## Observación para la documentación de tesis (no acción de producto)

El recorrido de esta sesión UX/UI, sumado a lo ya encontrado en Fichas
05 y 09, revela un patrón que ninguna auditoría anterior había medido
explícitamente porque ninguna cruzó Runtime, Boundary y UI en el mismo
documento:

```
Ficha 05  →  decision  existe en el Runtime  →  entrega.diseno=None en la UI (fallback)
Ficha 09  →  answers=[1..5]  existe completo  →  known_topics=true/false (colapso binario)
H1 (UX)   →  ProgrammingConcept("arrays")     →  "Arrays" sin traducir (capa parcial)
```

En los tres casos, **el dato correcto y completo existe en una capa
más profunda del sistema** (Runtime, dato crudo persistido, o valor
enum interno) — la degradación ocurre siempre en la misma transición:
**la proyección desde el estado interno del sistema hacia la
explicación dirigida al estudiante.** Ninguno de los tres hallazgos es
un defecto del enjambre, del consenso, de la deliberación o del motor
de adaptación — los tres están *después* de que el sistema ya decidió
correctamente.

Esto es una observación con valor directo para la sección de
Discusión de la tesis: la brecha medida no es de *capacidad adaptativa*
(el sistema multiagente decide bien, con evidencia real medida en
Fichas 05/09/H1) sino de **explicabilidad educativa** — la traducción
entre el estado interno correcto y lo que el estudiante efectivamente
llega a entender. Es una brecha distinta y más específica que
"explicabilidad" en general (que ya cubre RFC-0007/Modo Evidencia,
pensado para jurado/docente): aquí el destinatario es el propio
estudiante, en su propio flujo de aprendizaje, no un observador
externo evaluando el sistema.

Esta observación queda registrada aquí como insumo de redacción — no
implica ninguna acción de código ni de producto por sí sola.

---

## Estado de la Sesión UX/UI al cierre de Paso 3

Paso 1 (observar), Paso 2 (mapear) y Paso 3 (clasificar) — cerrados.
Ningún archivo de código modificado en ninguno de los tres pasos.
**Paso 4 (decidir qué se implementa) no se abre en este documento** —
requiere instrucción explícita, y si se abre, cada hallazgo que pase a
implementación necesita su propia ficha de una página (objetivo,
archivos que cambian, qué no debe cambiar, criterio de cierre) antes de
escribir código, siguiendo la misma disciplina que Fichas 01-09.
