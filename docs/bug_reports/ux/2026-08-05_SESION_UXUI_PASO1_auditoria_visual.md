# Sesión UX/UI — Paso 1: Auditoría visual (sin código)

## Metadata

- **Fecha:** 2026-08-05
- **Rama:** `investigacion/sesion-ux-ui`
- **Protocolo:** observar → medir → clasificar → decidir → implementar
  (mismo protocolo que Fichas 05/09). Este documento cubre **solo Paso 1
  (observar)** — captura visual real, navegador real, cuenta de prueba
  fresca (`ux.nuevo.recorrido@upao.edu.pe`), sin código modificado.
- **Alcance explícitamente excluido de este documento:** remediación de
  Ficha 05, remediación de Ficha 09, rendimiento, calibración LLM. Ningún
  hallazgo de aquí se implementa en esta sesión — quedan clasificados
  para Paso 2 (mapeo contra arquitectura) y Paso 3 (priorización).
- **Pantallas recorridas:** dashboard estudiante, ruta adaptativa,
  diagnóstico inicial (pre-test), pantalla de deliberación de agentes,
  Misión 1 completa (Concepto → Práctica → Consolidar, editor Pyodide
  real incluido), Tutor IA (chat real). **Resultados/evaluación: no
  alcanzado** — no existe una pantalla de "resultados" separada
  accesible antes de completar un módulo completo; ver hallazgo H6.

## Focos explícitos de esta sesión (definidos por el usuario)

- **(A)** Comunicación del estado del sistema durante la deliberación de
  agentes / espera.
- **(B)** UX de ejercicios/editor: salida no bloqueante, rutas de
  escape, recuperación de errores.
- **(C)** Visualización adaptativa — buscar el patrón "el backend
  conserva más información que la UI derivada" ya encontrado en Fichas
  05/09, sin corregirlo todavía.

---

## Hallazgos

### H1 — Vocabulario técnico interno expuesto sin traducir al estudiante (foco C)

**Dónde aparece (4 superficies distintas, confirmado con capturas):**

1. Dashboard (`/estudiante`), panel "Tutor IA Multiagente · Análisis en
   vivo": tags `Algorithms`, `Conditionals`, `Functions`, `Operators`
   (fortalezas) y `Arrays`, `Fundamentos de python`, `Input output`,
   `Instrucciones precisas`, `Loops` (a reforzar) — mezcla de inglés
   técnico interno y español, sin curar.
2. Ruta de Aprendizaje (`/estudiante/path/{courseId}`), sección "Cómo
   aprenderás mejor": "Temas prioritarios: Arrays, Fundamentos de
   python, Input output, Instrucciones precisas, Loops, Variables" —
   mismas etiquetas crudas.
3. La misma pantalla, al expandir "Ver cómo decidió el sistema": expone
   vocabulario textual del runtime (`PLATAFORMA`, `AGENTE DIAGNÓSTICO`,
   `dominio(input-output)`, etc.) directamente al estudiante.
4. Pantalla "Consolidar" de la Misión 1 (ver H2 — mismo problema, caso
   más severo).

**¿Qué entiende el estudiante?** Que hay "temas" en los que está fuerte
o débil.

**¿Qué interpreta mal?** Las etiquetas en inglés (`Algorithms`,
`Arrays`, `Loops`) no corresponden a ningún nombre de módulo o concepto
que el estudiante haya visto en la plataforma en español — son nombres
de categorías internas del modelo de competencias (`COMP-0..5`, según
memoria `competency_model_diagnostic`), no vocabulario pedagógico
dirigido al estudiante.

**¿Qué información falta?** Una capa de traducción/mapeo entre las
categorías internas (`Arrays`, `Input output`...) y los nombres de
módulo reales que el estudiante conoce (Módulo 7 "Arreglos", etc.) —
o bien, si la intención es mostrar evidencia técnica cruda a propósito,
falta un rótulo que lo distinga claramente de contenido pedagógico
narrado (como sí ocurre en Modo Evidencia, que está pensado para
jurado/docente, no para el estudiante en su propio dashboard).

**Clasificación (sin decidir):** patrón repetido, no aislado — 4
ocurrencias en 2 pantallas centrales del flujo de estudiante (dashboard
+ ruta). Mismo patrón estructural que Ficha 05/09 ("dos pipelines,
distinta fidelidad") pero en dirección inversa: aquí el problema no es
que la UI pierda información del backend, sino que la UI expone
información interna sin curar.

---

### H2 — Superficie de autoría de contenido expuesta en el flujo real del estudiante (foco C, severidad alta)

**Dónde:** Misión 1, Ciclo 1, etapa "Consolidar"
(`/estudiante/module/{id}`), panel "Recurso pedagógico generado".

**Qué se ve textualmente (capturado con zoom, confirmado legible):**

```
Recurso pedagógico generado                    [plantilla v1]
Origen: decisión pedagógica existente (modalidad(algorithms))

Diseña un reto de práctica más pequeño que el intento actual
sobre "condiciones_evaluables", para un estudiante de nivel
aplicacion con perfil mixta. Objetivo pedagógico: reforzar
"condiciones_evaluables". Debe resolverse en menos pasos que
el ejercicio original, conservando el mismo concepto evaluado.

[Copiar prompt]

¿Ya generaste el recurso en una herramienta externa?
Pega aquí su referencia.
[https://ejemplo.test/reto-condici...] [Guardado]
```

**¿Qué entiende el estudiante?** No queda claro — no hay ningún
encabezado explicativo dirigido a él; el bloque aparece igual que el
resto de tarjetas de contenido pedagógico (mismo estilo visual que
"¿Qué hace precisa a una instrucción?").

**¿Qué interpreta mal?** Un estudiante real leería esto como una tarea
o instrucción dirigida a él («Diseña un reto...», en imperativo) — pero
el texto es en realidad un **prompt de generación de contenido dirigido
a un content designer/docente**, con un flujo de "generar en herramienta
externa → pegar URL de vuelta" que no tiene sentido en absoluto para un
estudiante en medio de un ejercicio de programación.

**¿Qué información falta?** Todo lo contrario — sobra información: esto
parece una **herramienta de autoría de contenido para el equipo
pedagógico, filtrada al camino de producción del estudiante real**, no
un problema de información faltante.

**Clasificación (sin decidir):** distinto en naturaleza a H1 (no es
vocabulario técnico sin traducir, es una superficie de un rol distinto
— autor de contenido, no estudiante — mezclada en la misma vista).
Candidato más fuerte de esta sesión para "bug de scoping de UI /
componente que no debería renderizarse para `role=estudiante`" — pero
la clasificación definitiva y la causa raíz (¿condicional de rol
faltante? ¿feature flag no aplicado? ¿componente de desarrollo
placeholder aún no retirado?) quedan para Paso 2, tal como pide el
protocolo.

---

### H3 — Comunicación del estado durante la deliberación de agentes: dos patrones distintos, uno mejor que el otro (foco A)

Se observaron **dos** momentos de espera por decisión multiagente en la
misma Misión 1, con calidad de comunicación notablemente distinta:

**Patrón débil** — dentro del editor, tras "Continuar →" en un paso de
código: aparece solo el texto `Personalizando tu siguiente paso...` con
un ícono de spinner girando, sin más detalle, en un recuadro pequeño
dentro del layout normal de la página.

**Patrón fuerte** — al terminar por completo un ciclo (Concepto →
Práctica → Consolidar) y pulsar "Continuar →": aparece una pantalla
completa dedicada, con checklist animado de 3 pasos:
```
● PERSONALIZANDO TU SIGUIENTE PASO
✓ Analizando cómo resolviste el reto
✓ Detectando qué tanto dominas el concepto
✓ Eligiendo la mejor forma de continuar
```

**¿Qué entiende el estudiante?** En el patrón fuerte, entiende que el
sistema está evaluando su desempeño real y no solo "cargando". En el
patrón débil, solo entiende que "algo está pasando", sin saber qué.

**¿Qué interpreta mal?** En el patrón débil, nada indica que se trata
de una decisión multiagente real (vs. una carga técnica genérica como
Pyodide inicializando) — el estudiante no puede distinguir "el sistema
está pensando en mí" de "la página está cargando un recurso".

**¿Qué información falta?** Consistencia: el patrón fuerte (checklist
de 3 pasos) debería ser el único usado para cualquier espera de
deliberación multiagente, incluida la del editor — actualmente coexisten
dos implementaciones distintas del mismo concepto ("el sistema está
decidiendo algo sobre mí").

**Clasificación (sin decidir):** mejora de consistencia UX, bajo riesgo
de tocar arquitectura — probablemente un solo componente de "estado de
espera" reutilizable en vez de dos implementaciones.

---

### H4 — UX de error en el editor: ejemplo positivo, no un problema (foco B)

Al ejecutar código con un `SyntaxError` real (Pyodide real, sin mocks):

```
CONSOLA DE SALIDA
(sin salida)

ERROR EN LA LÍNEA 1 — SYNTAXERROR
print(Territorio cruzado)

Python no pudo leer esta línea — revisa comillas, paréntesis y
signos: algo quedó incompleto o de más.

Corrige la línea y vuelve a presionar Ejecutar — equivocarse y
reintentar es exactamente cómo se aprende a programar.

▸ Ver el mensaje original de Python   [colapsado por defecto]
```

Con panel "Tutor" contextual a la derecha explicando en lenguaje llano
por qué falló, y una segunda explicación tras corregir el error
("Agregar las comillas fue lo que arregló el código...").

**¿Qué entiende el estudiante?** Que el error es normal, recuperable, y
por qué ocurrió — sin jerga.

**¿Qué interpreta mal?** Nada detectado — el flujo es no bloqueante (el
editor conserva el código con el error, no hay pantalla de bloqueo ni
mensaje alarmante), tiene ruta de escape clara (corregir y reintentar)
y explica la causa en dos niveles (amigable arriba, traceback real de
Python bajo un colapsable opcional).

**¿Qué información falta?** Ninguna crítica. Único detalle menor: el
traceback expandible (`Ver el mensaje original de Python`) expone rutas
internas de Pyodide (`/lib/python312.zip/_pyodide/_base.py`) que no
aportan nada al estudiante — ruido, no un bloqueo (bajo impacto, la
sección ya está colapsada por defecto y es opt-in).

**Clasificación:** **hallazgo positivo** — este patrón de error debería
ser la referencia para cualquier otra superficie de error de la
plataforma, no un problema a corregir.

---

### H5 — CTA del dashboard no corresponde a su propio texto

**Dónde:** dashboard estudiante, tarjeta "Siguiente paso recomendado":
"Tu ruta personalizada ya está lista" con una acción que, al pulsarla,
lleva al **pre-test de diagnóstico**, no a la ruta de aprendizaje que el
texto afirma que "ya está lista".

**¿Qué entiende el estudiante?** Que puede ir directo a su ruta ya
construida.

**¿Qué interpreta mal?** El botón lo envía a un flujo distinto
(diagnóstico) al que el texto promete (ruta), un desajuste texto↔acción
directo.

**¿Qué información falta?** Ninguna — es una inconsistencia de
enrutamiento del CTA, no de información.

**Clasificación:** bug de UX simple y acotado, candidato de corrección
rápida sin riesgo arquitectónico (cambiar el destino del botón o el
texto para que coincidan).

---

### H6 — No existe una pantalla de "resultados" separada antes de completar el módulo

Se buscó explícitamente una vista de resultados/evaluación (parte del
checklist de Paso 1) y no se encontró ninguna independiente accesible
desde la navegación principal (`Mi Aprendizaje`, `Ruta de Aprendizaje`)
para un estudiante que aún no completó una misión completa. La
retroalimentación de "resultado" ocurre **inline**, paso a paso, dentro
del propio ejercicio (mensajes tipo "Exacto — así se ve en pantalla.",
"Perfecto — detectaste que el objetivo disfrazado de instrucción era el
impostor.") — no como una pantalla de cierre agregada.

**Clasificación:** no es necesariamente un defecto — puede ser una
decisión de diseño válida (retroalimentación inmediata > resumen
diferido) — pero queda como pregunta abierta para Paso 2: ¿existe una
pantalla de resultados agregada en algún punto posterior del recorrido
(post-test, fin de módulo) que este Paso 1 no alcanzó a recorrer por
tiempo, y que debería visitarse antes de cerrar la sesión completa de
UX/UI?

---

## Resumen para Paso 2 (mapeo contra arquitectura — NO iniciado aquí)

| # | Hallazgo | Foco | Severidad aparente | Pantallas afectadas |
|---|---|---|---|---|
| H1 | Vocabulario interno sin traducir | C | Media — repetido, no bloqueante | Dashboard, Ruta (×2) |
| H2 | Superficie de autoría de contenido en producción | C | **Alta** — rol equivocado, confuso | Misión 1 · Consolidar |
| H3 | Dos patrones de "esperando al sistema" | A | Baja-media — inconsistencia, no error | Editor (débil), transición de ciclo (fuerte) |
| H4 | UX de error del editor | B | — (hallazgo positivo) | Editor/Pyodide |
| H5 | CTA dashboard no coincide con su texto | — | Baja — acotado | Dashboard |
| H6 | Sin pantalla de resultados agregada | — | Abierta, no evaluada | N/A |

Ningún hallazgo de esta tabla se implementa en esta sesión. El
siguiente paso explícito es **Paso 2**: mapear cada hallazgo contra la
arquitectura real del Runtime (qué reducer/capacidad produce cada dato
mostrado) antes de clasificar en Paso 3 como bug UX / mejora opcional /
decisión pedagógica / deuda técnica.
