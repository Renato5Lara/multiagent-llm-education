# Propuesta de diseño: extender Orientar/Remediar a nivel de objetivo (no de sesión)

- **Estado:** Propuesta — sin aceptar, sin implementar. Para revisión.
- **Fecha:** 2026-08-01
- **Fase:** 1 de la migración de `generate_learning_path_adaptive` al Runtime
  (ver `docs/SWARM_ACTIVATION_AUDIT.md` §8 y la conversación que originó
  esta ficha). No introduce capacidades nuevas — amplía el alcance de
  `Orientar`/`Remediar`, ya normativas en RFC-0002 §3.
- **No implica:** cambios al Kernel, a la mecánica de deliberación
  (`convocar`/`derivar_decision`/`derivar_decision_directa`), ni a
  `palabra_en_pie` — los tres ya son genéricos por `asunto` (evidencia
  abajo). Tampoco implica tocar `backend/app/agents/`, que ya no existe
  (ADR-0011).

## Documentos relacionados

- `docs/architecture/pedagogical/01-AUDITORIA.md` §"Lo que tampoco es
  continuo" — **fuente primaria de este gap**. La auditoría pedagógica
  congelada (2026-07-23) ya identificó, antes que este documento, que
  `generate_learning_path_adaptive` "no llama al runtime en ningún
  punto" y que "la estructura de módulos... no se reestructura por el
  runtime durante la sesión." La necesidad de que `Orientar` trabaje a
  nivel de objetivo, no de sesión, ya estaba implícita ahí. **Este
  documento no identifica el problema — propone una estrategia técnica
  de implementación compatible con la arquitectura ya congelada**,
  verificando contra el código actual (§1) qué cambiaría exactamente y
  qué no.
- `docs/architecture/pedagogical/04-FLUJO-ADAPTATIVO-CONTINUO.md` —
  describe el ciclo Diagnosticar→Remediar/Orientar→Deliberar→Decidir
  vigente; cualquier cambio a ese Flujo, según la regla de evolución de
  `ESTADO.md`, requiere revisar los Documentos 5–7 de esa suite antes de
  implementarse — no solo este documento.
- `docs/architecture/RFC-0002-domain-model.md` §3 — contrato normativo
  de `Orientar` ("diagnóstico + estructura de módulos → propuesta de
  siguiente objetivo de la ruta"); esta propuesta completa ese contrato,
  no lo modifica.
- `docs/SWARM_ACTIVATION_AUDIT.md` — auditoría de alcanzabilidad de
  código que motivó esta ficha.

## 1. Lo que ya existe (verificado leyendo el código, no asumido)

### 1.1 `save_diagnostic` ya alimenta el Runtime (corrección de un hallazgo previo)

`app/services/student_service.py:127` (`_registrar_diagnostico_en_runtime`)
traduce cada respuesta Likert 1–5 del diagnóstico inicial a
`items_incorrectos`/`items_totales` y la registra vía
`runtime_bridge.registrar_evidencia_evaluacion` — una competencia por
hecho, mismo patrón que el pre-test (`knowledge_test_service.py`). Esto
ya corre hoy; no es parte de esta propuesta.

### 1.2 `Diagnosticar` interpreta esa evidencia en claims por competencia

`runtime/domain/diagnosticar/productor.py`: por cada `fact` vigente con
`"competencia"` en su contenido, sin interpretar todavía, produce un
claim `INTERPRETACION` con:

```
asunto:      f"dominio({competencia})"
afirmacion:  {"dominada": bool, "errores": int}
respaldo:    (fact.id,)
confianza:   Decimal("0.78")   # o variable en la versión LLM
```

### 1.3 `Orientar`/`Remediar` ya resuelven una tensión sobre esos claims — pero a nivel de SESIÓN, no de objetivo

`runtime/domain/orientar/productor.py` y `runtime/domain/remediar/
productor.py`: ambos recorren `estado.claims` buscando **cualquier**
claim `INTERPRETACION` vigente con `"dominada"` en su afirmación —
sin distinguir DE QUÉ COMPETENCIA — y proponen sobre un único asunto
compartido:

```python
ASUNTO_SIGUIENTE_PASO = "siguiente-paso(sesion)"
```

Orientar propone `{"accion": "avanzar-con-andamiaje"}` si encuentra una
`dominada=True`; Remediar propone `{"accion": "reforzar"}` si encuentra
una `dominada=False`. Ambos están guardados por
`palabra_en_pie(estado, autor, asunto)` (`runtime/domain/shared/
propuestas.py`) para evitar re-proponer sin necesidad (anti-churn,
CONCEPT-0002 §5).

**Esto es lo que hay que ampliar.** El asunto es literal, global a la
sesión — un curso con 9 objetivos hoy solo puede tener UNA propuesta
"avanzar/reforzar" vigente a la vez, sin importar cuál de los 9
objetivos la originó. Para que esto sirva de insumo real a la
generación de la ruta (9 módulos, cada uno con su propio estado
dominado/no-dominado), el asunto necesita ser **por objetivo**, no por
sesión.

### 1.4 El Kernel ya es genérico por asunto — no hay que tocarlo

Evidencia de que esta ampliación es aditiva, no invasiva:

- `palabra_en_pie(estado, autor, asunto)` ya recibe `asunto` como
  parámetro — no asume cuál es.
- `Politica.pesos_asunto` (`runtime/kernel/deliberation/mecanica.py:149`)
  ya es un diccionario por asunto ("neutro=1 si el asunto no está
  registrado") — el comentario del propio código dice explícitamente
  que `"siguiente-paso(sesion)"` es "el ejemplo real" actual, no un
  límite de diseño.
- `convocar`/`derivar_decision`/`derivar_decision_directa` recorren
  `estado.deliberaciones`/`estado.claims` sin ningún `if asunto ==
  "siguiente-paso(sesion)"` hardcodeado.

## 2. Contrato de entrada propuesto para Orientar/Remediar

**Problema a resolver:** `LearningState` hoy no tiene ninguna noción de
"estructura del curso" (lista de objetivos, su orden). Los facts que
existen son evidencia evaluativa (`competencia`, `items_incorrectos`,
`items_totales`, `modalidad_estudiante`) — nunca metadata curricular.

**Opción evaluada y descartada:** registrar la estructura del curso como
un nuevo tipo de `fact`. Se descarta porque la estructura del curso
**no es evidencia observada del estudiante** (P7: evidencia real) — es
configuración de producto (`LearningObjective.order`, editable por un
docente en cualquier momento). Meterla como fact contaminaría la
"percepción del entorno" (CONCEPT-0001) con datos que no son percepción
de nada — violaría la distinción facts/config implícita en RFC-0003.

**Opción propuesta:** igual patrón que `politica`/`urgente` en
`_nodo_deliberar` (`runtime/engine/graph/walkthrough.py:85-91`, ya
citado en su propio docstring como parámetro externo, "información del
Boundary... jamás derivada de `estado.ejecucion`"). Los productores de
Orientar/Remediar reciben la estructura del curso como **parámetro de
invocación**, no como estado:

```python
def producir(
    estado: LearningState,
    objetivos: tuple[ObjetivoOrdenado, ...],
) -> tuple[TransitionIntent, ...]:
    ...

# ObjetivoOrdenado — tupla nombrada mínima, vive en runtime/domain/shared/
# (mismo criterio de extracción que propuestas.py: consumida por Orientar
# Y Remediar, cero lógica de negocio de una capacidad concreta)
class ObjetivoOrdenado(NamedTuple):
    id: str            # LearningObjective.id — para que la plataforma
                        # pueda mapear la decisión de vuelta a un PathModule
    asunto: str         # normalizar_asunto(objetivo.title) — MISMO slug
                        # que usa Diagnosticar para "dominio(...)"
    orden: int          # LearningObjective.order
```

Quién construye esta tupla y la pasa a `producir(...)`: el Boundary
(`runtime_bridge.py`), leyendo `LearningObjective` de la plataforma —
exactamente el mismo lugar y el mismo patrón que ya arma `Entrega`s hoy.
El Kernel/Engine no necesita saber qué es un `LearningObjective`.

## 3. Claim(s) que produciría la versión ampliada

Por cada `ObjetivoOrdenado` sin palabra vigente propia (`palabra_en_pie`
con el asunto por objetivo), Orientar/Remediar buscan un claim
`dominio({obj.asunto})` — no "cualquier claim con `dominada`", como hoy:

```python
ASUNTO_AVANCE = lambda obj_asunto: f"avance({obj_asunto})"   # nombre a decidir

# Orientar, si dominio(obj.asunto).dominada is True:
{
    "autor": Capacidad.ORIENTAR,
    "tipo": TipoClaim.PROPUESTA,
    "asunto": ASUNTO_AVANCE(obj.asunto),
    "afirmacion": {"accion": "avanzar"},
    "respaldo": (claim_dominio.id,),
    "confianza": Decimal("0.75"),
    "provenance": Provenance.de(OrigenProvenance.REGLA, id="ruta-v2"),
}

# Remediar, si dominio(obj.asunto).dominada is False:
{
    "autor": Capacidad.REMEDIAR,
    "tipo": TipoClaim.PROPUESTA,
    "asunto": ASUNTO_AVANCE(obj.asunto),
    "afirmacion": {"accion": "reforzar"},
    "respaldo": (claim_dominio.id,),
    "confianza": Decimal("0.82"),
    "provenance": Provenance.de(OrigenProvenance.REGLA, id="remediacion-v2"),
}
```

**Sin objetivo sin evidencia:** si no existe todavía un
`dominio({obj.asunto})` vigente para ese objetivo (estudiante no
evaluado en esa competencia todavía), ni Orientar ni Remediar proponen
nada — el objetivo queda sin decisión del Runtime, y la plataforma cae
a su comportamiento actual para ese módulo específico (ver §4).

Un objetivo sin tensión (solo Orientar o solo Remediar tienen algo que
decir) deriva decisión directa (D3, `derivar_decision_directa`, ya
genérico). Dos objetivos distintos nunca compiten entre sí — cada uno
tiene su propio asunto, su propia deliberación si la hay.

## 4. Cómo `generate_learning_path_adaptive` consumiría esto

Nueva función de lectura en `runtime_bridge.py`, mismo patrón que
`decision_adaptativa` (lee, nunca escribe — regla 2 de RFC-0010):

```python
def avance_por_objetivo(
    student_id: str, course_id: str, objetivos: tuple[ObjetivoOrdenado, ...],
) -> dict[str, str]:
    """{objetivo.id: "avanzar" | "reforzar"} para los objetivos con
    decisión vigente del Runtime. Objetivos ausentes del dict: sin
    evidencia todavía — el llamador decide su comportamiento por
    defecto, nunca esta función (mismo contrato que decision_adaptativa
    y consultar_decision_vigente)."""
```

`generate_learning_path_adaptive` reemplazaría su `_initial_module_
statuses(n_modules, knowledge_breakdown)` actual (que lee
`pretest.module_breakdown` — un resumen por porcentaje, calculado por
`knowledge_test_service`, nunca por el Runtime) por una lectura de
`avance_por_objetivo(...)`: `"avanzar"` → `"available"` (saltable);
`"reforzar"` → `"available"` como frente de trabajo; ausente → cae al
comportamiento histórico (`statuses[0] = "available"`, resto
`"locked"`) — best-effort, mismo patrón que cada integración existente
en `runtime_bridge.py`.

**Nota honesta:** esto no es un cambio de una línea. `_initial_module_
statuses` hoy encuentra el PRIMER módulo no dominado y lo marca como
frente de trabajo único; una lectura por objetivo de
`avance_por_objetivo` podría, en principio, devolver "reforzar" para
varios objetivos no consecutivos (si el estudiante saltó evaluaciones o
el curso no fuerza orden estricto) — el mapeo de "múltiples objetivos en
estado reforzar" a "un único frente de trabajo secuencial" es una regla
de producto que hay que decidir explícitamente, no algo que se derive
solo. Se registra aquí como pregunta abierta, no como problema resuelto.

## 5. Alineación con RFC-0002 — qué NO cambia

- Las ocho capacidades: sin cambios. No se crea ninguna capacidad nueva.
- El contrato de Orientar (RFC-0002 tabla §3: "diagnóstico + estructura
  de módulos → propuesta de siguiente objetivo de la ruta"): esta
  propuesta es precisamente completar ese contrato ya escrito, no
  reinterpretarlo.
- P13 (implementación intercambiable, contrato estable): la versión LLM
  de Orientar/Remediar (`productor_llm.py`) necesitaría el mismo cambio
  de firma (recibir `objetivos`), manteniendo idéntico el resto del
  contrato — mismo criterio que ya usa la selección regla/LLM.
- El vocabulario cerrado de VOCABULARY.md: no se introduce ningún
  término normativo nuevo — `ObjetivoOrdenado` es una tupla de
  transporte (como `PeticionAbrirSesion`), no un concepto del dominio.

## 6. Riesgos y preguntas abiertas (sin resolver aquí)

1. **Múltiples frentes de refuerzo simultáneos** (§4, nota honesta) —
   necesita una decisión de producto antes de implementar el lado de
   plataforma.
2. **Nombre del asunto** (`avance(...)` es un placeholder) — debe
   revisarse contra el resto del vocabulario de asuntos ya en uso
   (`dominio(...)`, `modalidad(...)`, `siguiente-paso(sesion)`) para
   mantener el mismo estilo, posiblemente en la misma sesión donde se
   implemente.
3. **`siguiente-paso(sesion)` no desaparece** — sigue siendo el asunto
   correcto para la adaptación EN VIVO dentro de una sesión activa (lo
   que ya consume `Adaptar`/`contexto_pedagogico_tutor`). Esta propuesta
   añade un asunto POR OBJETIVO para la planificación de ruta; no
   reemplaza el existente. Verificar que ambos puedan coexistir sin que
   Orientar/Remediar dupliquen trabajo (probablemente sí, dado que
   `palabra_en_pie` es por asunto, pero vale una revisión antes de
   implementar).
4. **Costo de la versión LLM**: si `generate_learning_path_adaptive` se
   invoca una vez por generación de ruta y ahora dispara N invocaciones
   de Orientar/Remediar (una por objetivo sin evidencia previa) en vez
   de cero, el costo/latencia de generar una ruta con proveedor LLM
   activo sube proporcionalmente a `len(objectives)`. Mismo patrón de
   timeout que ya usa `module_orchestration_service` (`_RESEARCH_TIMEOUT_S`
   etc.) probablemente aplica aquí también — a diseñar en
   implementación, no aquí.

## 7. Lo que este documento NO decide

No decide si esta migración debe ejecutarse ahora, en qué commit, ni
quién la implementa. Es el insumo técnico para esa decisión — Fase 1 de
lo acordado, sin código todavía.
