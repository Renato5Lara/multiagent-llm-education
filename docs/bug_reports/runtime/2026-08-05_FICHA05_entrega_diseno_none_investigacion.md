# Bug Report — Investigación forense (sin remediación)

## Metadata
- **ID:** AUDIT-FICHA-05 (Auditoría-UPAO-MAS-EDU-2026-08-05.docx)
- **Fecha:** 2026-08-05
- **Severidad:** 🟠 Importante (auditoría original) — **reevaluada en Fase 2**:
  medido contra los 29 estudiantes reales con evidencia real, el mecanismo
  ocurre en 1/29 (3.4%) — caso puntual, no condición estructural del runtime
  (ver "Fase 2 — Medición de alcance real"). La corrección de esta línea
  respecto a la primera versión de este documento es intencional: la Fase 1
  no tenía todavía el dato de incidencia real y no debía calificar severidad
  sin él.
- **Categoría:** backend/runtime (kernel de deliberación + productores de dominio)
- **Tipo:** investigación forense — **NINGÚN código ni test fue modificado**
  para producir este documento. Todas las llamadas fueron de solo lectura
  (`consultar_estado`, `consultar_entrega_vigente`, `identidad_existente`) o
  contra esquemas Postgres descartables creados y eliminados en la misma
  sesión de investigación (`investigacion_ficha05_*`), nunca contra datos de
  producción — excepto la medición de Fase 2, que sí lee (nunca escribe)
  contra los 45 estudiantes y 86 matrículas reales de la base de datos.
- **Estado:** DIAGNÓSTICO CERRADO (Fase 1 + Fase 2). Remediación NO
  iniciada. **La investigación del Mecanismo A (¿debe `Aplazada` producir
  una decisión provisional en contexto educativo, o es un estado final
  válido?) se evaluó y se decidió explícitamente NO abrirla en esta
  ronda** — es una decisión de arquitectura del consenso (semántica del
  enjambre), no diagnóstico adicional de Ficha 05. Antes de retomarla:
  revisar RFC-0006 (consenso-enjambre) y CONCEPT-0002 (taxonomía del
  consenso) para la política esperada de `Aplazada`, ninguno de los dos
  releído a fondo con esta pregunta específica todavía.
- **Relacionado:** [[AUDIT-2026-08-05_REMEDIATION_STATUS]] observación #6
  (hipótesis original, ahora resuelta con evidencia)

## Baseline de cierre (Fase 2, congelado — no volver a derivar en sesiones futuras)

- El kernel determinista queda **descartado** como causa raíz del
  Mecanismo B — `derivar_decision_directa` funciona exactamente según su
  contrato documentado (D3, RFC-0006 §3 / RFC-0003 INV-6).
- La incidencia real medida es baja: **1 de 29** sesiones reales con
  evidencia (3.4%) — caso puntual, no condición estructural.
- La causa inmediata del caso auditado (EstudianteC) es la cadena
  **productor LLM activo → confianza declarada baja → `ce < θ`/`margen <
  δ` → decisión no alcanzada** — no un defecto de enrutamiento ni de
  cálculo del kernel.
- La hipótesis original de la auditoría (`runtime_bridge.py` como causa
  raíz) queda **descartada** — nunca fue la causa en ninguno de los dos
  mecanismos encontrados.

## Protocolo seguido (los 4 pasos acordados antes de abrir esta investigación)

1. Reproducir el caso EstudianteC y capturar el comportamiento actual.
2. Obtener la traza real del runtime y la decisión multiagente generada.
3. Verificar el flujo completo de datos hasta "Cómo aprenderás mejor".
4. Comparar con los 5 tests fallidos preexistentes: ¿relación causal o solo síntoma?

## Paso 1+2 — EstudianteC: reproducción y traza real

`student_id` real de Postgres: `c80f7148-7d70-4e97-9b6f-45e0308723b4`
(`est.c.mediolector.audit@upao.edu.pe`). `course_id` real: `0fbe4f4c-1520-4ecc-ac84-cf0fed353eb0`
(Fundamentos de Programación). `session_id` determinista (`_sesion_del_curso`):
`curso:0fbe4f4c-...:estudiante:c80f7148-...`.

Consulta directa de solo lectura contra Postgres real (sin registrar nada):

```
entrega.asunto: None
entrega.diseno: None
decision_adaptativa() -> None
```

Confirma el síntoma exacto que reportó la auditoría — vigente hoy, no solo
en el momento de la auditoría original.

**Traza completa del `LearningState` (30 facts, 18 claims, 1 deliberación, 0 decisiones):**

- 18 claims: `DIAGNOSTICAR` (interpretaciones de dominio) + 1 `ORIENTAR` +
  1 `REMEDIAR`. **Cero claims de `ADAPTAR`** en toda la historia de la sesión.
- 1 deliberación, y es `Aplazada`:
  `evidencia_faltante="evidencia sobre 'siguiente-paso(sesion)' que discrimine
  entre T-000004/e1 y T-000044/e1: margen 0.0331 < delta 0.10"`.
- 0 decisiones.

## Paso 3 — Cadena de datos completa, extremo a extremo

```
LearningPath.tsx:448 {adaptiveDecision.strategy_description}
  ← useAdaptiveDecision() [hooks/useStudent.ts:79]
    ← GET /api/students/adaptive-decision/{courseId} [students.py:371-373]
      ← decision_adaptativa(student_id, course_id) [runtime_bridge.py:306]
        ← consultar_entrega_vigente(peticion, almacen, almacen_memoria)
          [runtime/boundary/surfaces/entrega_vigente.py:22]
          ← materializar_sesion(...) → proyectar_entrega(sesion.estado)
            [runtime/boundary/outbound/entregas.py:33]
            → busca claims con autor=ADAPTAR y vigencia.vigente
            → ninguno existe → Entrega(asunto=None, diseno=None)
      → decision_adaptativa() retorna None (línea 326-327)
    → useStudent.ts recibe null → LearningPath.tsx no renderiza la tarjeta
      "Cómo aprenderás mejor" con datos — el frontend, en paralelo (no en la
      misma llamada), muestra el mensaje de reserva
```

**Hallazgo adicional no anticipado por la auditoría original:** la insignia
"Versión Lectora" que el estudiante SÍ ve en `ModuleLearningView.tsx:182`
(`learningPath?.dominant_modality`) lee un campo completamente distinto —
`DiagnosticResult.dominant_modality`, escrito directamente por
`student_service.save_diagnostic()` al completar el diagnóstico VARK — **sin
pasar nunca por `entrega`/`decision_adaptativa`/el runtime en absoluto**.

Esto reencuadra el hallazgo de la auditoría (*"dos superficies del producto
pueden mostrar información contradictoria sobre el mismo estudiante en el
mismo instante"*): no es una sincronización rota entre dos vistas de un mismo
dato — son **dos pipelines de datos genuinamente independientes** que
coinciden en la mayoría de los casos (cuando Adaptar sí llega a correr) y
divergen visiblemente cuando Adaptar nunca corrió. El bug no es "estas dos
superficies deberían estar sincronizadas" — es "por qué Adaptar nunca corrió
para este estudiante", que es lo que sigue abajo.

## Causa raíz mecánica: por qué Adaptar nunca produce un claim

`runtime/domain/adaptar/productor.py:146-147`:

```python
def producir(estado: LearningState) -> tuple[TransitionIntent, ...]:
    for decision in estado.decisiones:
        ...
```

Adaptar **itera sobre `estado.decisiones`, no sobre claims ni deliberaciones**.
Con `decisiones=0` (el caso de EstudianteC, y de 3 de los 5 tests fallidos —
ver Paso 4), el bucle nunca entra — `producir()` retorna `()` incondicionalmente.
`proyectar_entrega` entonces siempre ve `vigentes=[]` (ningún claim de
ADAPTAR existió jamás) → `Entrega(None, None)`.

**Se encontraron DOS mecanismos estructurales distintos que llevan a
`decisiones=0`** — no uno solo. Comparten el síntoma final, no la causa.

### Mecanismo A — aplazamiento por margen bajo sin urgencia (confirma la hipótesis original de Ficha 05)

Reproducido de forma determinista, 2 veces, con Postgres real y OpenAI real,
usando `registrar_evidencia_evaluacion(..., urgente=False)` (el default):

```
Reproducción 1 (EstudianteC real): margen 0.0331 < delta 0.10 → Aplazada
Reproducción 2 (sesión sintética fresca, 1 sola competencia): margen 0.0000 < delta 0.10 → Aplazada
```

En ambos casos: `REMEDIAR` propone "reforzar" y `ORIENTAR` propone
"avanzar-con-andamiaje" para el mismo asunto `siguiente-paso(sesion)` — una
tensión genuina, tal como describe RFC-0006. La regla de arbitraje
(`kernel/deliberation/mecanica.py:212-239`, código leído, no inferido):

```python
if margen >= politica.delta:
    resultado = Resuelta(regla=REGLA_POLITICA_V1, ...)
elif urgente:
    resultado = Resuelta(regla=REGLA_PROVISIONAL, ...)
elif _aplazamientos_en_cadena(...) >= politica.limite_reconvocatoria:
    resultado = Escalada()
else:
    resultado = Aplazada(...)
```

Sin `urgente=True`, un margen bajo cae directo a `Aplazada` — que, por
diseño (RFC-0006 §4 Parte E, CONCEPT-0002 §4: *"el aplazamiento es
productivo"*), **no crea una `DecisionEntry`**. Es un comportamiento
correcto del kernel, no un bug del kernel — el problema está en qué
llamadores del Boundary pasan `urgente=True` y cuáles no.

**Callers de `registrar_evidencia_evaluacion` y su valor de `urgente`:**

| Caller | Ruta | `urgente` |
|---|---|---|
| `students.py:566` (`submit_cycle_evidence` — práctica de un ciclo) | `POST /api/students/cycle-evidence` | `True` |
| `students.py:1047` (`submit_evaluation` — evaluación de módulo) | `POST /api/students/evaluation/{id}/submit` | `True` |
| `student_service.py:155` (diagnóstico VARK inicial) | (interno, llamado desde `save_diagnostic`) | default `False` |
| `knowledge_test_service.py:445` (pre-test, evidencia por competencia) | (interno, llamado desde el flujo de pre-test) | default `False` |
| `knowledge_test_service.py:488` (pre-test, evidencia del primer objetivo real) | (interno, llamado desde el flujo de pre-test) | default `False` |

**Toda la evidencia real de EstudianteC entró por las 3 llamadas sin
`urgente`** (confirmado: la forma exacta de sus 30 facts —
`items_totales: 5` × 8 competencias, `items_totales: 2` × 6 competencias,
`items_totales: 12` × 1 — coincide exactamente con el patrón de
`_evidencia_por_competencia` de `knowledge_test_service.py`, no con
`save_diagnostic`). Nunca llegó a completar un ciclo de práctica
(`/cycle-evidence`) ni una evaluación de módulo (`submit_evaluation`) — las
dos únicas rutas que sí habrían forzado una resolución provisional.

### Mecanismo B — ausencia estructural de tensión en la ruta por objetivo (hallazgo nuevo, no anticipado por la auditoría)

`students.py:1047` (evaluación de módulo) construye `objetivos` no vacío
(`construir_objetivos(...)`) y lo pasa a `registrar_evidencia_evaluacion`.
Esto activa una rama distinta en **ambos** productores:

`runtime/domain/orientar/productor.py:33-34` y
`runtime/domain/remediar/productor.py:32-33` (código idéntico en estructura):

```python
if objetivos:
    return _producir_por_objetivo(estado, objetivos)
```

Con `objetivos` no vacío, **ninguno de los dos vuelve a proponer para el
asunto de sesión `siguiente-paso(sesion)`** — proponen exclusivamente para
`avance(objetivo.asunto)`. Y en esa rama:

- `Orientar._producir_por_objetivo` (líneas 88-94) solo propone "avanzar"
  si encuentra un claim `dominada=True` para ese objetivo.
- `Remediar._producir_por_objetivo` (misma estructura) solo propone
  "reforzar" si `dominada=False`.

Como una competencia solo puede tener un veredicto de dominio (`True` o
`False`) en un instante dado, **como máximo uno de los dos productores
propone jamás** — nunca ambos. Reproducido con Postgres+OpenAI reales,
`urgente=True`, 1 objetivo, competencia no dominada (2/3 incorrectas — el
mismo patrón exacto de evidencia que usa el test fallido
`test_submit_evaluation_incluye_la_decision_del_runtime`):

```
=== CLAIMS (2) ===
DIAGNOSTICAR | dominio(condicionales) | dominada=False
REMEDIAR | avance(condicionales) | reforzar          ← única propuesta, sin rival

=== DELIBERACIONES (0) ===
=== DECISIONES (0) ===
```

Sin una segunda propuesta rival, `tension_bloqueante()` no detecta ninguna
tensión — `convocar()` nunca se invoca (`if tension is None: return None`,
`mecanica.py:194-195`). **`urgente=True` es irrelevante aquí: nunca llega a
evaluarse**, porque el punto de entrada a la regla de arbitraje (`convocar`)
depende de que exista una tensión, y aquí nunca existe. Una propuesta
solitaria de Remediar/Orientar queda vigente en `estado.claims` para
siempre, pero **nunca se convierte en una `DecisionEntry`**, y Adaptar (que
solo lee `estado.decisiones`) nunca la ve.

**Alcance:** `/api/students/cycle-evidence` (`students.py:566`, la práctica
dentro de un ciclo — probablemente el punto de evidencia más frecuente en
el uso real de un estudiante) **no pasa `objetivos`**, así que no activa
este mecanismo — sigue la ruta de sesión, que con `urgente=True` sí resuelve
de forma confiable (3/3 reproducciones exitosas, ver abajo). Solo
`submit_evaluation` (evaluación de módulo completa) está expuesto al
Mecanismo B.

## Paso 4 — Comparación con los 5 tests preexistentes fallidos

| Test | `urgente` | `objetivos` | Mecanismo | Relación con Ficha 05 |
|---|---|---|---|---|
| `test_evidencia_de_evaluacion_produce_una_entrega_de_adaptar` (`test_runtime_bridge.py`) | no pasado (`False`) | no | **A** — reproducido: margen 0.0000 < 0.10 → Aplazada | ✅ Misma causa raíz |
| `test_consultar_decision_vigente_refleja_la_ultima_evidencia_registrada` (`test_runtime_bridge.py`) | no pasado (`False`) | no | **A** (mismo `registrar_evidencia_evaluacion` sin `urgente`, mismo patrón de evidencia única) | ✅ Misma causa raíz (por construcción idéntica al anterior) |
| `test_mayoria_reforzar_sugiere_esa_competencia` (`test_pedagogy_runtime_bridge.py`) | no pasado (`False`) | no | **A** (mismo patrón: 1 competencia, evidencia única, sin urgencia) | ✅ Misma causa raíz |
| `test_submit_evaluation_incluye_la_decision_del_runtime` (`test_students_evaluation_runtime_wiring.py`) | `True` (vía `students.py:1047`) | **sí** | **B** — reproducido con la evidencia exacta del test: 0 deliberaciones, 0 decisiones | ⚠️ Comparte solo el síntoma — mecanismo distinto |
| `test_start_evaluation_usa_el_bloom_que_decidio_el_runtime` (`test_students_evaluation_runtime_wiring.py`) | `True` (vía `students.py:1047`) | **sí** | **B** (mismo endpoint, mismo `_sembrar_intento`) | ⚠️ Comparte solo el síntoma — mecanismo distinto |

**Verificación de que `urgente=True` por sí solo SÍ resuelve el Mecanismo A**
(descarta que el Mecanismo A explique también los 2 tests con
`urgente=True`): 3 reproducciones independientes, evidencia idéntica a la
del test fallido, `objetivos` vacío → **3/3 produjeron una `Entrega` válida**
(`Resuelta`, no `Aplazada`, margen variable 0.14–0.20 según la confianza que
declaró el LLM en cada corrida — nunca por debajo de 0 decisiones). Esto
confirma que el mecanismo de urgencia del kernel funciona correctamente tal
como lo describe RFC-0006 §4 Parte E — el fallo de esos 2 tests específicos
no es un defecto de esa regla.

## Conclusión del diagnóstico

**Causa raíz confirmada, no hipótesis — dos mecanismos independientes, ambos
con evidencia de traza real de runtime:**

1. **Mecanismo A** (el que motivó la Ficha 05 original): estudiantes cuya
   ÚNICA evidencia hasta el momento proviene del diagnóstico VARK o del
   pre-test (`knowledge_test_service.py`, `student_service.py`) — ninguno de
   los 3 call sites de esa vía pasa `urgente=True` — quedan estructuralmente
   expuestos a que la primera tensión Remediar/Orientar caiga en
   `Aplazada` si el margen de confianza declarado por el LLM resulta menor
   a 0.10 (que ocurrió en 2/2 reproducciones con evidencia fresca en esta
   sesión). Mientras no completen un ciclo de práctica o una evaluación de
   módulo — las únicas dos vías con `urgente=True` — quedan sin ninguna
   decisión, y por tanto sin ninguna adaptación, indefinidamente.
2. **Mecanismo B** (hallazgo nuevo, no reportado por la auditoría original):
   la ruta de evaluación de módulo (`submit_evaluation`), al pasar
   `objetivos` no vacío, activa una rama de Orientar/Remediar donde **como
   máximo un productor propone** por cada objetivo — nunca hay una segunda
   propuesta rival, así que nunca se forma una tensión, así que `convocar()`
   nunca se invoca, así que `urgente=True` nunca llega a aplicarse. Esto es
   independiente del margen de confianza del LLM — ocurre siempre que la
   evaluación de un objetivo produce un veredicto de dominio inequívoco (que
   es el caso normal, no el excepcional).

**Ninguna de las dos causas está en `runtime_bridge.py`** (la hipótesis que
la auditoría original planteó como más probable, sin confirmarla) — está en
`runtime/kernel/deliberation/mecanica.py` (Mecanismo A, comportamiento
correcto del kernel expuesto por un default de `urgente` en callers
específicos) y en `runtime/domain/{orientar,remediar}/productor.py`
(Mecanismo B, una asimetría estructural entre la rama de sesión y la rama
por objetivo).

## Nuevas líneas de investigación que este diagnóstico abre (no iniciadas)

1. **¿El Mecanismo B es el comportamiento pretendido?** El propio docstring
   de `orientar/productor.py:32` dice *"Ambos asuntos coexisten; uno no
   reemplaza al otro"* — pero el código (`if objetivos: return
   _producir_por_objetivo(...)`) los hace mutuamente excluyentes dentro de
   una misma invocación. Vale la pena revisar `DESIGN-orientar-ruta-
   completa.md` (Fase 2) para confirmar si esa fue una decisión consciente
   o una desviación entre docstring e implementación.
2. **Alcance real del Mecanismo B en producción**: no se verificó cuántos
   de los 45 estudiantes reales de la base de datos tienen `entrega.diseno`
   en `None` en este momento, ni si siguen un patrón dominante (Mecanismo A
   vs B vs ninguno). Sería el primer paso de cualquier remediación futura.
3. **¿Por qué el margen del Mecanismo A varía entre 0 y 0.20+ en corridas
   con evidencia casi idéntica?** Proviene de que Diagnosticar/Remediar/
   Orientar declaran su `confianza` vía LLM real (no determinista) — esto
   ya está fuera del alcance de este documento, pero explica por qué el
   Mecanismo A es "a veces sí, a veces no" en vez de siempre reproducible
   con el mismo margen exacto.

---

# Fase 2 — Análisis limitado a evidencia (sin código, sin remediación)

Continuación de la investigación de Fase 1, con 3 preguntas específicas:
(1) intención arquitectónica del Mecanismo B, (2) alcance real en datos de
producción, (3) estabilidad del margen como observación secundaria. **Cero
archivos de código modificados** — todas las consultas de esta fase son de
solo lectura (`consultar_estado`, `consultar_entrega_vigente`,
`identidad_existente`, `calcular_confianza_efectiva` invocada directamente
sobre estado ya persistido) o instrumentación aislada en esquemas Postgres
descartables ya eliminados al cierre de esta investigación.

## Punto 1 — ¿El contrato exige consenso, o una propuesta única también decide?

**Respuesta, con cita textual de código y RFC, no interpretación:**
el sistema **no** requiere tensión entre agentes para producir una decisión.

`runtime/kernel/deliberation/mecanica.py:280-310`
(`derivar_decision_directa`, docstring citado literal):

> *"Propuesta única deriva decisión directa si `ce` alcanza θ (RFC-0006 §3,
> D3; RFC-0003 INV-6, 'el origen de una decisión es ... el claim-propuesta
> único'). Corrección de un bug preexistente, no una capacidad nueva desde
> cero: ... el ejemplo real es 'siguiente-paso(sesion)' cuando
> `dominada=True` — Orientar propone solo, Remediar nunca compite, y el
> walkthrough terminaba en END sin decisión ni Adaptar."*

Es decir: el propio kernel ya documenta, como bug corregido, exactamente el
síntoma del Mecanismo B — una propuesta sin rival que antes terminaba sin
decisión. La función que lo corrige (`derivar_decision_directa`) es
**genérica por asunto** (`for asunto in sorted(por_asunto): ...`, línea 335
— sin ningún `if asunto == "..."` hardcodeado) y está efectivamente cableada
en el enrutamiento real (`runtime/engine/graph/walkthrough.py:354`,
`enrutar()`).

**Se reprodujo la comparación exacta `ce` vs `θ` con instrumentación
directa** (mismo escenario del Mecanismo B, objetivo con evidencia
`dominada=False`, `urgente=True`):

```
politica.theta: 0.5
Capacidad.REMEDIAR | asunto=avance(condicionales) | confianza_declarada=0.2077 |
  ce_efectiva=0.2077 | theta=0.5 | ce>=theta: False
derivar_decision_directa() -> None
```

`enrutar()` alcanza correctamente `derivar_decision_directa`; la función se
ejecuta; `ce (0.2077) < θ (0.5)` → "insuficiencia (D3)" — el comportamiento
documentado, no un fallo de enrutamiento. **Se verificó además, contra el
axioma A2 (Anclaje) del propio módulo** (*"en el instante en que un claim se
registra ... `ce` es exactamente `claim.confianza`, la declarada"*), que no
hay ningún descuento oculto del kernel: la confianza declarada YA nació en
0.2077, no fue reducida desde un valor mayor.

**Por qué 0.2077 y no el `0.82` que aparece hardcodeado en
`remediar/productor.py`:** ese valor pertenece a la versión-regla
(`producir`), que **no es la que corre en este entorno**.
`runtime/boundary/inbound/productores.py:42-45`:

```python
def productor_remediar_activo() -> Callable:
    if os.environ.get("OPENAI_API_KEY"):
        return partial(producir_remediacion_llm, proveedor=OpenAIProvider())
    return producir_remediacion_regla
```

Con `OPENAI_API_KEY` configurada (confirmado, backend real de esta sesión),
la versión LLM está activa — es el LLM quien declaró 0.2077, no el kernel
quien lo calculó. **El kernel determinista queda descartado como bloqueador**
para el Mecanismo B: hace exactamente lo que su contrato documenta. El
origen real del bloqueo está aguas arriba, en la confianza que el productor
LLM declara — que por tu instrucción explícita, esta fase NO investiga más
a fondo.

## Punto 2 — Alcance real en datos de producción (solo lectura, 45 estudiantes / 86 matrículas)

Se recorrieron las 86 matrículas reales (`Enrollment`) de los 45 estudiantes
reales de la base de datos, derivando el `session_id` determinista de cada
par y consultando (sin escribir) su estado de runtime si existía.

```
Pares estudiante-curso matriculados:                         86
Sesiones de runtime que realmente existen (E1 ya ocurrió):    34
Sesiones con al menos 1 fact (evidencia real registrada):     29
Sesiones con entrega.diseno = None:                            6
Sesiones con 0 decisiones:                                     6
```

**De las 6 con 0 decisiones, 5 nunca recibieron ningún hecho** (`facts=0,
claims=0` — sesiones abiertas, E1, pero abandonadas antes de cualquier E2;
`decision_adaptativa_neutra()` es exactamente el comportamiento correcto
para este caso, no un bug). **Solo 1 de las 29 sesiones con evidencia real
está genuinamente bloqueada — y es `est.c.mediolector.audit@upao.edu.pe`,
la propia cuenta de prueba que usó la auditoría original.**

Desglose de las 29 sesiones con evidencia real por exposición a cada
mecanismo:

```
Expuestas al Mecanismo A y al B simultáneamente (avance-objetivo presente): 13 → 12 resolvieron OK, 1 bloqueada (EstudianteC)
Expuestas solo al Mecanismo A (solo siguiente-paso-sesion):                12 → 12 resolvieron OK
```

**Corrección a la Fase 1:** el análisis original clasificó a EstudianteC
como expuesta únicamente al Mecanismo A. La medición de Fase 2 encontró que
también tiene un claim `avance(fundamentos-de-python)` de Remediar sin
rival — Mecanismo B — generado por
`knowledge_test_service.py:488` (la evidencia del pre-test sobre el primer
objetivo real del curso, que **también** pasa `objetivos`, no solo
`submit_evaluation` como se afirmó en la Fase 1). Está expuesta a ambos
mecanismos a la vez, no solo a uno.

**Respuesta a la pregunta del punto 2:** con 28 de 29 sesiones reales
(96.6%) produciendo al menos una decisión — incluyendo 12 de 13 con la
misma exposición exacta al Mecanismo B que el caso bloqueado — esto es
**un caso puntual, no una condición estructural del runtime**. Es
consistente con el propio hallazgo de la auditoría original (§17: 0.5%,
3 de 660 deliberaciones reales, cayeron en "Aplazada" en todo el sistema).
El mecanismo es real y está demostrado con trazas — su incidencia medida es
baja.

## Punto 3 — Estabilidad del margen (observación secundaria, sin abrir investigación de LLM)

Ya registrado en la Fase 1 y confirmado aquí sin profundizar más (por tu
instrucción explícita): la confianza que declaran Diagnosticar/Remediar/
Orientar en su versión LLM activa varía entre invocaciones con evidencia de
forma idéntica (Fase 1: margen 0 y 0.0331 en dos corridas; `ce_efectiva`
observada en el rango 0.14–0.21 en las corridas de esta fase). El Punto 1
ya estableció que esta varianza —no el kernel— es la que determina si un
caso puntual cae por debajo de `θ`/`δ` o no. No se abre investigación
adicional del LLM en este documento.

## Conclusión de Fase 2

1. El kernel determinista **no** exige consenso para decidir — el contrato
   (D3, RFC-0006 §3) ya prevé y resuelve la propuesta única, y el código lo
   implementa correctamente, verificado con trazas reales.
2. El Mecanismo B **no** es una condición estructural — es un caso puntual
   (1/29 sesiones reales con evidencia, 3.4%), y coincide con ser la cuenta
   de prueba de la propia auditoría.
3. EstudianteC está expuesta a los dos mecanismos simultáneamente, no solo
   al Mecanismo A como afirmó la Fase 1 — corrección aplicada arriba.

**Sigue sin proponerse ninguna remediación.** La pregunta que planteaste
como condición para diseñarla —*"si una deliberación aplazada debe terminar
siempre en una decisión provisional, si una propuesta única debe generar
decisión, o si el sistema intencionalmente requiere múltiples agentes en
conflicto"*— ya tiene respuesta documental para el caso de propuesta única
(sí debe generar decisión, y el kernel ya lo hace cuando `ce ≥ θ`); la
pregunta sobre el aplazamiento (Mecanismo A) sigue abierta y no se investigó
en esta fase.
