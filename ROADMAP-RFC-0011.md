# ROADMAP — RFC-0011 (Generación de Recursos Pedagógicos)

> Documento de planificación y oficialización de conceptos — no de
> arquitectura pedagógica nueva. Ningún principio PP0–PP8 cambia; ninguna
> frontera de RFC-0002 §3 se toca. **No implementar nada de este
> documento sin aprobación explícita del tesista (RFC-0000 §proceso:
> "Solo el tesista aprueba RFCs").**

- **Fecha:** 2026-07-24
- **Estado:** Aprobado (tesista, 2026-07-24) — habilita el Engineering
  Gate de RFC-0011/1
- **Propietario:** RFC-0011 (nuevo, Boundary — `docs/architecture/`, no
  `docs/architecture/pedagogical/`), subordinado a RFC-0002 §3 (frontera
  Adaptar) y extensión directa de Adenda A (Arquitectura Pedagógica v1.0,
  Documento 5 §4.1)
- **Motivo:** decisión del tesista (2026-07-24) de levantar el FEATURE
  FREEZE del 2026-07-15 para incorporar selección dinámica del *tipo de
  recurso* pedagógico (no solo la *forma* categórica que Adenda A ya
  resuelve) y generación de un prompt reutilizable para producirlo con un
  modelo generativo externo. Antes de tocar código, este documento fija
  qué es realmente nuevo, qué ya existe, y en qué orden se construye.

---

## 0. Auditoría — qué existe hoy contra qué se pidió

| Pieza pedida | Estado real |
|---|---|
| "Motor de selección multimodal" que elige el tipo de recurso | **No existe como tal.** Lo más cercano es `seleccionar_forma()` (`backend/app/services/adaptive_form_selection.py`, Adenda A): función pura y determinista que traduce `modalidad × profundidad × alternativas_descartadas` (ya producidas por Adaptar) a **una** forma del catálogo fijo de PP4 (`ejemplo_adicional`, `animacion`, `reto_mas_pequeno`, `pista_progresiva`, `audio`, `codigo_guiado`, `narracion_tutor`). Vive en el Boundary, se invoca hoy en `POST /students/.../cycle-evidence` (`students.py:582-591`). No elige *variantes* dentro de una forma ni genera nada. |
| Perfil VARK como entrada de la decisión | **Ya existe, no es nuevo.** Es literalmente el campo `modalidad` (visual/reading/audio/kinesthetic) que Adaptar (RFC-0002 R3) ya produce vía consenso (RFC-0006) y que `seleccionar_forma()` ya consume. |
| "Experience Recipe" / "Experience Orchestrator" | Existen (`frontend/src/lib/experiences/experienceOrchestrator.ts`, `frontend/src/types/moduleExperience.ts`). Son una capa de **composición del frontend**, explícita en su propio docstring: "NO un agente ni un rol nuevo". Reordenan contenido ya autorado a mano; no generan nada ni deciden pedagogía. |
| Generación de prompts especializados por perfil + consenso de agentes | **Existe, pero es código retirado.** `PromptEngineeringAgent` + `MultimodalPlanningAgent` (`backend/app/agents/`) hacen casi exactamente esto, orquestados por `PedagogicalOrchestrationService` con `ConsensusMediator`. Son subclases de `BaseAgent`, declaradas retiradas del flujo en vivo por este mismo `CLAUDE.md` ("no reciben funcionalidad nueva... no se usan como referencia de diseño para implementaciones nuevas"). Su único invocador real es `app/experiment/benchmark/real/executor.py` (grupo de control experimental, D-001). **No se reutilizan ni como base de diseño.** |
| Registro/caché de recursos generados (evitar regenerar) | **No existe en ningún lado.** |
| Trazabilidad de "por qué se eligió este recurso" | Parcial: `entrega.diseno` (RFC-0003, cadena de claims de Adaptar) ya es trazable hasta la decisión de modalidad/profundidad. Nada conecta esa cadena con un recurso físico concreto todavía. |
| Vocabulario normativo (`VOCABULARY.md`) | No tiene fila para "recurso pedagógico", "prompt de recurso" ni términos equivalentes — hueco confirmado, se cierra por parte (§3) cuando cada pieza aterrice en código, igual que hizo RFC-0006. |

**Conclusión de la auditoría:** lo pedido no es una capacidad aislada
nueva — es una **extensión downstream de Adenda A**, en el mismo locus
(Boundary) y con el mismo patrón (función pura y determinista,
trazabilidad explícita, ningún concepto pedagógico nuevo). El pipeline
de agentes que "ya hace esto" no es reutilizable: es exactamente el
código que el régimen vigente de este `CLAUDE.md` prohíbe usar como
referencia.

---

## 1. Frontera — qué NO cambia (para que no se cuele durante la implementación)

- **PP0–PP8 (Arquitectura Pedagógica v1.0) no se modifican.** Congelada
  2026-07-23; su propia regla de evolución exige revisar toda la cadena
  documental si un principio cambia — ninguna parte de este roadmap lo
  requiere. La elección del *tipo concreto de recurso* dentro de una
  forma ya es, por declaración explícita de Adenda A, "contenido/producto,
  no arquitectura" ("lo que esta adenda NO decide: el mapeo específico").
- **RFC-0002 §3 no se modifica.** Adaptar sigue produciendo únicamente
  categorías pedagógicas (`modalidad × profundidad × ritmo × andamiaje`).
  Nunca decide, ni lee, ni escribe un recurso físico o un prompt.
- **Ningún agente ni capacidad nueva.** Las 8 capacidades de RFC-0002 y
  el consenso de RFC-0006 no crecen. "Elegir qué prompt generar" es
  traducción determinista, exactamente como "elegir qué forma mostrar" ya
  lo es en Adenda A — no una novena capacidad votando.
- **`backend/runtime/` no se toca.** Todo lo nuevo vive en
  `backend/app/services/` (Boundary), mismo paquete que
  `adaptive_form_selection.py`.
- **La plataforma nunca genera el recurso final (imagen/audio/video).**
  Solo produce el prompt. Llamar a una API externa de generación queda
  fuera de este roadmap (ver §4).
- **Guardrail de implementación (decisión del tesista, 2026-07-24):** si
  en cualquier punto del Engineering Gate de una parte se descubre que la
  nueva capa obliga a cambiar una regla pedagógica del Boundary ya
  cerrada (p. ej. introducir un criterio de decisión nuevo, o modificar
  el mapeo de Adenda A más allá de añadir plantillas), **la
  implementación se detiene** y se solicita revisión arquitectónica
  antes de continuar — en ese momento, y solo en ese momento, se
  reconsidera si corresponde una Adenda D sobre
  `docs/architecture/pedagogical/` en vez de este RFC de Boundary.

---

## 2. Conceptos nuevos a oficializar (locus: RFC-0011)

Cinco términos nuevos, ninguno más — cada uno con fila pendiente en
`VOCABULARY.md` cuando su parte cierre con código real:

1. **Recurso Pedagógico Generado** (`RecursoGenerado`): dato inmutable
   `{forma, modalidad, asunto, texto_prompt, version_plantilla,
   referencia_recurso, origen}` — no es solo un prompt, es el artefacto
   completo (prompt + metadata + referencia al recurso físico cuando
   exista + origen trazable). `referencia_recurso` es opcional y llega
   después (ver punto 5). `origen` es la referencia de trazabilidad (ver
   punto 6) — decisión del tesista (2026-07-24), corregida en su forma de
   implementación (ver nota debajo de la tabla §3).
2. **Plantilla de Prompt** (`PlantillaPrompt`): contenido (no
   arquitectura, mismo estatus que el mapeo de formas de Adenda A) que
   define cómo se redacta el prompt para una combinación
   `forma × modalidad`. Empieza cubriendo solo las combinaciones que el
   runtime ya produce en vivo hoy — mismo criterio ya usado en
   `_MODALIDAD_DESCARTADA_A_FORMA`. **Parametrizada, no hardcodeada**:
   la plantilla usa variables (`{{concepto}}`, `{{nivel}}`, `{{perfil}}`,
   `{{objetivo}}`), nunca el texto literal "Python" — esto es mecánica
   de plantillas, no expansión de alcance: el curso sigue siendo
   exclusivamente Fundamentos de la Programación (`THESIS_SCOPE_FREEZE.md`);
   la plantilla simplemente no repite el nombre del curso en cada string.
3. **Registro de Recursos** (`RegistroRecursos`): persistencia
   versionada en Postgres de cada `RecursoGenerado`, con clave
   `(asunto, forma, modalidad, version_plantilla)` — permite reutilizar
   sin regenerar.
4. **`generar_prompt_recurso()`**: función pura del Boundary, mismo
   estándar de determinismo que `seleccionar_forma()` (ADR-0001 §4) —
   nunca llama a un LLM en el camino síncrono del estudiante. Enriquecer
   el prompt con un LLM queda explícitamente fuera de v1 (ver §4):
   añadiría latencia y no-determinismo a un endpoint que hoy es
   determinista de punta a punta.
5. **Referencia de Recurso** (`referencia_recurso`): campo opcional,
   genérico y agnóstico de proveedor (una cadena con esquema —
   `url:...`, `storage:...`, `asset:...` — nunca un tipo acoplado a un
   proveedor concreto) para asociar, después de generado externamente,
   el recurso físico resultante (imagen/audio/video/documento) al
   `RecursoGenerado` que lo originó. Decisión del tesista (2026-07-24):
   entra desde v1, sin validación automática de que el recurso
   corresponde al prompt — eso es una épica aparte, si se decide más
   adelante.
6. **Origen** (`origen: {asunto, alternativas_descartadas}`): decisión
   del tesista (2026-07-24) de preservar trazabilidad — "¿por qué se
   generó este recurso?" debe poder responderse, no solo "porque era
   visual". Implementación: **referencia a la decisión que Adaptar ya
   produjo, nunca una explicación nueva fabricada por esta capa.**
   RFC-0002 (§3, capacidad Adaptar) ya exige que la propuesta de diseño
   de experiencia se entregue "con las alternativas que evaluó" — ese
   dato ya existe en `entrega.diseno.alternativas_descartadas` y ya se
   copia hoy a `seleccionar_forma()` (`students.py:585-589`). `origen`
   simplemente conserva esa misma referencia (asunto + alternativas ya
   evaluadas) junto al `RecursoGenerado`, sin costo adicional de consulta
   ni interpretación nueva. **Se descarta explícitamente** un campo de
   "motivo" en texto libre o etiquetas fabricadas por el Boundary
   (`["perfil_visual", "dominio_bajo", ...]`): eso sería la nueva capa
   redactando una explicación por su cuenta, violando el criterio ya
   registrado en `VOCABULARY.md` ("la explicación se recorre, no se
   redacta") y la regla de derivación de este mismo `CLAUDE.md` — si el
   motivo real ya existe en la cadena de claims de RFC-0003, se referencia,
   no se reinterpreta en una copia paralela que puede desincronizarse.

   > **Nota de intención (pedida por el tesista, 2026-07-24):** el campo
   > `origen` es una referencia estable a la decisión pedagógica que
   > originó el recurso. No constituye una explicación generada por esta
   > capa; cualquier explicación presentada al usuario deberá
   > reconstruirse recorriendo dicha referencia, conforme a los
   > principios de trazabilidad del proyecto.

---

## 3. Las partes — dependencias, riesgo, tamaño

| Parte | Qué hace | Depende de | Riesgo | Tamaño |
|---|---|---|---|---|
| **0 — Registro de Recursos (persistencia)** | Tabla Postgres nueva + migración; decide el mecanismo de versionado/clave, incluyendo `referencia_recurso` (genérico, nulo hasta que exista) y `origen` (asunto + alternativas_descartadas, copiado de `entrega.diseno`, nunca recalculado). No especificado por ningún documento existente → candidata a mini-ADR corto (mismo criterio que Parte 0 de RFC-0006). | — | Medio (decide un mecanismo, pero acotado: una tabla, no un subsistema) | Bajo-Medio |
| **A — Contrato `generar_prompt_recurso()`** | Función pura + catálogo mínimo de `PlantillaPrompt` (una por combinación forma×modalidad ya viva en producción). | — (no depende de 0: es pura) | Medio (definir el shape del prompt sin sobre-diseñar) | Medio |
| **B — Reutilización** | Antes de generar, consulta el Registro por clave; si existe y la plantilla no cambió de versión, reutiliza sin regenerar. | 0, A | Bajo | Bajo |
| **C — Wiring del Boundary** | `POST /cycle-evidence` invoca A/B tras `seleccionar_forma()`; añade `runtime_decision["recurso"]`. Aditivo, mismo patrón que Adenda A (`if entrega.diseno and ...`) — nunca rompe a quien no lo lea. | A, B | Bajo | Bajo |
| **D — Frontend** | Cierra la migración que la propia Adenda A dejó pendiente ("migrar el frontend para consumir este contrato... commit separado") extendida a mostrar `recurso.texto_prompt` con acción "copiar prompt", y un campo para adjuntar `referencia_recurso` una vez generado el recurso externamente (sin validación automática). | C | Bajo-Medio | Medio |
| **E — E2E** | Postgres real + navegador real: un ciclo produce y muestra el prompt; una segunda ocurrencia con la misma clave reutiliza sin regenerar (verificable por timestamp/versión). | D | Bajo | Bajo |

**Orden:** `0` y `A` pueden ir en paralelo (no dependen entre sí) →
`B` → `C` → `D` → `E`. Estrictamente secuencial desde B.

---

## 4. Fuera de alcance (explícito)

- **Llamar directamente a una API de generación de imagen/audio/video**
  (ChatGPT, Gemini, Claude, generador de imágenes). La plataforma entrega
  el prompt; nunca ejecuta la generación. Si se decide integrar esto más
  adelante, es un RFC nuevo — cambia la frontera con servicios externos.
- **Enriquecer el prompt con una llamada a LLM en el camino síncrono del
  estudiante.** Ver Parte A — v1 es templating determinista.
- **Consenso o votación de agentes nueva.** La decisión pedagógica ya la
  produce Adaptar; esta capa solo traduce.
- **Ampliar el catálogo de formas de PP4** (múltiples variantes visuales
  por forma, p. ej. infografía vs. mapa conceptual vs. analogía). Es
  contenido/producto — evoluciona plantilla por plantilla dentro de la
  Parte A, sin RFC nuevo, mismo principio que Adenda A ya declara para
  el mapeo de formas.
- **Enriquecimiento visual de trazabilidad** en la Runtime Console
  ("por qué se eligió este recurso" con confianza/agentes/margen,
  representado gráficamente) — pertenece a RFC-0007 (Observabilidad, hoy
  en Borrador), cuando se retome esa épica. **Distinto de lo que sí entra
  en v1** (§2 punto 6): el campo `origen` crudo (asunto +
  alternativas_descartadas) sí se persiste y se expone en la respuesta
  HTTP desde RFC-0011/1 — es una referencia barata a datos que ya existen
  en el mismo request, no un panel nuevo de explicabilidad.
- **"Épica B"** (rediseño del entorno de programación: editor, consola,
  `input()`, ejecución real vs. simulada) — completamente fuera de este
  documento. Es un roadmap-RFC distinto, con su propia auditoría, cuando
  se decida abrirlo.

---

## 5. Estructura fija por mini-épica

Mismo patrón que RFC-0006: cada mini-épica cierra con su propio
Engineering Gate (motor→boundary→HTTP→frontend→E2E→documentación) y una
ficha de una página antes de empezar. Agrupación propuesta:

| Mini-épica | Partes | Resultado observable al cerrar |
|---|---|---|
| RFC-0011/1 — Contrato y persistencia | 0 + A | `generar_prompt_recurso()` puro y testeado contra el catálogo mínimo de plantillas; tabla del Registro creada. Sin cambio de comportamiento visible — cero consumidores todavía. **CERRADO.** |
| RFC-0011/2 — Reutilización y wiring | B + C | `/cycle-evidence` empieza a devolver `runtime_decision["recurso"]`; reutilización real verificada contra Postgres. **CERRADO.** |
| RFC-0011/3 — Frontend y cierre E2E | D + E | El estudiante ve el prompt generado, puede copiarlo y adjuntar la referencia del recurso ya generado externamente; validado con Postgres real + navegador real, incluyendo el caso de reutilización (segunda ocurrencia no regenera). |

Ficha por mini-épica (plantilla idéntica a la de RFC-0006 §7): Objetivo,
Partes, Dependencias, Riesgos, capas que cambian (Motor/Boundary/HTTP/
Frontend/E2E), **qué no debe cambiar**, Context Budget, criterios de
cierre verificables — se abre al empezar cada una, no antes.

---

## 6. Decisiones resueltas (2026-07-24)

1. **Locus: Boundary — `docs/architecture/`, no Adenda D.** Confirmado.
   "Qué prompt generar" es traducción de una decisión pedagógica ya
   tomada, no una decisión pedagógica nueva — mismo estatus que Adenda A.
   No reabre la Arquitectura Pedagógica v1.0 congelada. Ver el guardrail
   de detención explícita añadido en §1 para el caso en que la
   implementación revele lo contrario a mitad de camino.
2. **Catálogo mínimo de `PlantillaPrompt`: se redacta durante el
   Engineering Gate de la Parte A**, no antes — para no bloquear la
   infraestructura esperando contenido definitivo. Es un catálogo
   mínimo funcional, parametrizado (§2 punto 2), editable y versionable;
   el tesista lo calibra después sin que eso implique cambiar el
   contrato ni la arquitectura.
3. **`referencia_recurso` entra desde v1** (§2 punto 5, Parte 0 y D
   actualizadas) — genérico y agnóstico de proveedor, sin validación
   automática de que el recurso corresponde al prompt.
4. **Naming: "Prompt de Recurso" → "Recurso Pedagógico Generado"**
   (§2 punto 1) — el dato siempre fue `RecursoGenerado` (prompt +
   metadata + `referencia_recurso`), nunca solo el texto del prompt; el
   nombre en prosa ahora lo refleja.
5. **Trazabilidad mínima desde v1** (§2 punto 6, campo `origen`) — pero
   como **referencia** a la decisión que Adaptar ya produjo
   (`asunto` + `alternativas_descartadas`, ya disponible sin costo
   adicional), nunca como una explicación nueva fabricada por el
   Boundary. Se descartó explícitamente la variante de "motivo" en
   texto libre/etiquetas por violar "la explicación se recorre, no se
   redacta" (`VOCABULARY.md`) y la regla de derivación del proyecto.

---

## 7. Ficha — RFC-0011/1: Contrato y persistencia — CERRADO (2026-07-24)

Verificado contra Postgres real (`upao_postgres`, no mocks): migración
`b3c4d5e6f7a8` aplicada, ciclo `downgrade`/`upgrade` reversible
confirmado, e inserción/lectura real de un `RegistroRecurso` con
round-trip exacto de `origen` (fila de prueba creada y eliminada, nunca
una entidad real). 22/22 tests backend en verde (9 nuevos +
13 de `test_adaptive_form_selection.py`, sin regresión). `app.main`
importa sin error — el modelo nuevo no colisiona con `Resource`/
`resources`. Sin consumidores todavía — Boundary, HTTP, Frontend y E2E
no cambiaron, tal como exigía la ficha.

## 8. Ficha — RFC-0011/2: Reutilización y wiring — CERRADO (2026-07-24)

```
Objetivo:        obtener_o_generar_recurso() (Parte B) + wiring aditivo en
                 POST /cycle-evidence (Parte C): runtime_decision["recurso"]
                 aparece solo cuando ya existe forma; reutilización real.
Partes:          B + C
Dependencias:    RFC-0011/1 (CERRADO)
Restricciones exigidas por el tesista (todas cumplidas):
  ✅ seleccionar_forma() sin modificar (Adenda A intacta)
  ✅ ninguna decisión pedagógica nueva — forma/modalidad ya venían decididas
  ✅ generar_prompt_recurso() se ejecuta solo dentro del bloque
     `if entrega.diseno and entrega.diseno.get("modalidad")`, después de
     seleccionar_forma()
  ✅ reutilización transparente: existe -> reutiliza; no existe -> genera
     y persiste (incluye manejo de condición de carrera vía UniqueConstraint)
  ✅ contrato HTTP solo se enriquece con runtime_decision["recurso"];
     ninguna respuesta existente cambió de forma
  ✅ frontend sin cambios
  ✅ pruebas de integración para ambos caminos (generación y reutilización)
Motor:           no cambia.
Boundary:        nuevo backend/app/services/resource_registry_service.py.
HTTP:            aditivo — students.py, dentro del bloque ya existente de `forma`.
Frontend:        no cambia (RFC-0011/3).
E2E:             runtime_completo.py no se ve afectado (no toca backend/runtime/);
                 tests HTTP existentes de cycle-evidence (test_cycle_evidence_dataset.py)
                 siguen en verde sin modificarse.

Validación: 6/6 tests nuevos (test_resource_registry_service.py, incluida
la condición de carrera simulada) + 36/36 tests del alcance combinado
(RFC-0011/1 + RFC-0011/2 + cycle-evidence + consent-response) en verde.
Reutilización verificada contra Postgres real (no solo SQLite de test):
segunda llamada con la misma clave devuelve la misma fila,
veces_reutilizado=1, sin fila duplicada.

Hallazgo no bloqueante (fuera de alcance, no corregido): al correr el
resto de la suite aparecieron 2 fallos preexistentes, ninguno causado
por este cambio — `test_tavily_cache.py`/`test_tavily_client.py`
(error de import, símbolos inexistentes en `app.integrations.tavily`) y
`test_export_experiment_has_three_sheets` (503 porque `openpyxl` no
está instalado en este entorno). Los tres quedan registrados como deuda
técnica ajena a RFC-0011.
```



```
Objetivo:        generar_prompt_recurso() puro y testeado, con catálogo
                 mínimo de PlantillaPrompt; tabla del Registro creada.
                 Sin cambio de comportamiento visible — cero consumidores.
Partes:          0 + A
Dependencias:    ninguna (primera mini-épica)
Riesgos:         Medio — definir el shape del prompt/RecursoGenerado sin
                 sobre-diseñar; decidir el mecanismo de persistencia
                 (tabla nueva, nunca reutilizar `resources`/`Resource` —
                 concepto ya existente y distinto: archivos subidos por
                 docentes, app/models/resource.py).
Motor:           no cambia — backend/runtime/ no se toca.
Boundary:        cambia — nuevo backend/app/services/resource_prompt_generation.py
                 (Parte A) y backend/app/models/registro_recurso.py (Parte 0).
HTTP:            no cambia — students.py no se toca en esta mini-épica.
Frontend:        no cambia.
E2E:             no cambia — ningún escenario de runtime_completo.py se ve afectado.

No debe cambiar: adaptive_form_selection.py (Adenda A) permanece intacto;
                 students.py no invoca nada nuevo todavía (eso es RFC-0011/2);
                 ninguna tabla existente (resources, research_metrics) se toca.

Context Budget:  backend/app/services/adaptive_form_selection.py (referencia de
                 estilo), backend/tests/test_adaptive_form_selection.py
                 (referencia de estilo de tests), backend/app/models/research.py
                 (referencia de estilo Mapped/mapped_column), backend/app/models/
                 resource.py (verificar que no colisiona), backend/app/models/
                 __init__.py, backend/alembic/versions/ (última head),
                 docs/architecture/VOCABULARY.md.

Criterios de cierre:
  ✅ generar_prompt_recurso() puro, determinista, testeado contra el
     catálogo completo de formas de PP4 (7) + fallback genérico
  ✅ RecursoGenerado no confunde origen (referencia) con una explicación
     fabricada — test explícito de que origen == {asunto, alternativas_descartadas}
  ✅ Tabla recursos_generados creada vía migración Alembic, encadenada al
     head real (no a un head desactualizado)
  ✅ No colisiona con la tabla/modelo Resource ya existente (docentes)
  ✅ Ningún consumidor real invoca esto todavía (cero cambio de comportamiento)
  ✅ VOCABULARY.md recibe la fila de RFC-0011 en el mismo commit
  ✅ Tests backend pasan (pytest backend/tests/test_resource_prompt_generation.py)
  ✅ No aparecen TODO/FIXME nuevos
```
