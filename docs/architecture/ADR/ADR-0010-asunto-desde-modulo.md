# ADR-0010 — `competencia`/`asunto` en el flujo del estudiante: slug del módulo, no COMP-N

- **Estado:** Aceptado (2026-07-12, Engineering Review dirigida — vacío
  normativo real: el flujo de módulo adaptativo en producción no
  calcula ningún COMP-N, y ninguna migración hacia `runtime/boundary/`
  puede avanzar sin fijar qué es "competencia" para ese flujo)
- **Fecha:** 2026-07-12
- **Preserva:** RFC-0002 §2 (Diagnosticar: "estado de conocimiento por
  competencia, con confianza" — sin fijar la forma concreta del
  identificador), RFC-0010 regla 1 (traducción, jamás interpretación),
  BLUEPRINT (`policy/` reserva explícitamente un "catálogo de asuntos")
- **Criterio de aceptación:** ver §5

## 1. Contexto

Al preparar la Épica 2 (migración del flujo del estudiante), la
verificación contra código real mostró que `module_orchestration_service
.py` — el servicio que hoy sirve `/api/students/module/{id}/orchestrate`,
el endpoint central del "Módulo Adaptativo" — **nunca calcula ni
almacena un valor COMP-N**. Diagnostica exclusivamente por nivel de
Bloom (`module.bloom_level`) y modalidad VARK (`dominant_modality`); el
catálogo COMP-0..5 vive únicamente en el subsistema de Pre/Post-Test
(Research Layer), un flujo distinto que el estudiante no recorre en su
uso normal del módulo.

Ni RFC-0002 ni RFC-0003 fijan `competencia` a la forma concreta
`COMP-N`: RFC-0002 §2 solo exige que Diagnosticar produzca "estado de
conocimiento por competencia" — un identificador estable del asunto
sobre el que se diagnostica, sin restringir su catálogo. Los ejemplos
`COMP-2` en RFC-0003/tests son ilustrativos, no normativos (ningún RFC
los declara el único catálogo válido). `competencia` tampoco tiene fila
propia en VOCABULARY.md que la fije a esa forma. Forzar una conversión
Bloom+VARK→COMP-N sería inventar una decisión pedagógica sin respaldo
(exactamente el tipo de vacío que el régimen prohíbe resolver en
código) — y bloquearía toda la Épica 2 hasta que existiera esa
investigación.

## 2. Decisión

> **Para el flujo del estudiante, `competencia` (el campo que las
> capacidades del runtime leen en `contenido`/`asunto`) es el slug
> determinista del `título` del módulo — nunca un valor del catálogo
> COMP-0..5.** COMP-0..5 sigue existiendo, sin tocarse, exclusivamente
> donde ya es nativo: el Pre/Post-Test.

La normalización reutiliza el mismo criterio que ya usa el código de la
plataforma para comparar títulos de forma insensible a mayúsculas y
acentos (`_norm` en `module_orchestration_service.py`): minúsculas, sin
diacríticos, espacios colapsados a un separador estable.

`normalizar_asunto("Condicionales")` → `"condicionales"`.
`normalizar_asunto("Bucles y Repetición")` → `"bucles-y-repeticion"`.

Es una función pura y determinista — no una tabla que haya que mantener
sincronizada con cada módulo que se cree (regla de derivación,
CLAUDE.md): cualquier título produce un slug reconstruible siempre de
la misma forma, sin invención de catálogo nuevo.

**Ubicación:** `runtime/boundary/inbound/asunto.py` —
`normalizar_asunto(titulo: str) -> str`. Es traducción mecánica de
vocabulario de plataforma a vocabulario del runtime (regla 1 de
RFC-0010: mecánica, no interpretación), y vive en el lado del contrato
que ya define qué forma toma `competencia` — no en `app/`, que no debe
decidir reglas del runtime, solo invocarlas.

## 3. Alternativas rechazadas

- **Definir una conversión Bloom+VARK→COMP-N**: rechazada — es una
  decisión pedagógica nueva sin investigación que la respalde; forzarla
  ahora inventaría conocimiento de dominio que el runtime no debe crear
  (P15).
- **Migrar primero el Pre/Post-Test** (que sí habla en COMP-N
  nativamente) y posponer `/module/{id}/orchestrate`: rechazada por el
  Product Owner — cambia el objetivo de la épica (migrar la aplicación
  completa) por evitar el endpoint más importante.
- **Tabla estática módulo→competencia** (un diccionario id-a-id
  mantenido a mano): rechazada — no existe un catálogo cerrado y
  confiable de módulos hoy (`PathModule.title` es texto libre sembrado
  por curso), y una tabla así violaría la regla de derivación
  (duplicaría en almacenamiento algo reconstruible del título).
- **Ubicar `normalizar_asunto` en `app/`**: rechazada — la forma válida
  de `competencia` es una regla del vocabulario del runtime (RFC-0010
  regla 1), no una decisión de la plataforma; debe vivir donde vive el
  contrato para que un cambio futuro de la regla sea un cambio de
  `runtime/boundary/`, trazable a este ADR.

## 4. Consecuencias

- Habilita el resto de la Épica 2: cualquier `contenido` de
  `PeticionHechoDelMundo` construido desde un `PathModule` usa
  `normalizar_asunto(module.title)` como su `competencia`.
- COMP-0..5 y el flujo Pre/Post-Test no se tocan — siguen siendo el
  catálogo válido exclusivamente ahí.
- Si en el futuro se decide formalizar un catálogo cerrado de asuntos
  (el "catálogo de asuntos" que BLUEPRINT reserva en `policy/`), este
  ADR se enmienda entonces — hoy no hay evidencia suficiente para
  cerrarlo sin arriesgar inventar taxonomía no validada.

## 5. Criterios de aceptación

1. `normalizar_asunto` es pura: mismo `titulo` produce siempre el mismo
   slug, sin I/O, sin estado.
2. Ningún código de la Épica 2 escribe un valor `COMP-N` en un fact o
   claim originado por el flujo de módulo adaptativo.
3. El Pre/Post-Test sigue usando COMP-0..5 sin ninguna modificación.
