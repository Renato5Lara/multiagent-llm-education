# RFC-0005 — Memoria

- **Estado:** Aceptado (2026-07-10 — con la precisión del tesista:
  memoria persistente vs memoria de trabajo; rev. 2 — 2026-07-12: enmienda
  §1.1, el caso N=0, hallado durante la Engineering Review previa a M4
  PR-6)
- **Autor:** Equipo de arquitectura (Claude + tesista)
- **Fecha:** 2026-07-10 (rev. 2: 2026-07-12)
- **Aprueba:** Renato Lara (tesista / Product Owner)
- **Tipo de revisión:** Architecture Review (define modelo, no
  implementación; el almacenamiento físico será un ADR)
- **Gobernado por:** P2, P12, P14, RFC-0002 §1, RFC-0003, RFC-0006, RFC-0008
- **Capa (RFC-0001 §1):** Kernel
- **Runtime Contract:** hace que las respuestas de una sesión puedan
  informar a la siguiente sin romper ninguna de las cinco

Conforme al mandato del tesista para los transversales restantes: este
RFC no introduce conceptos nuevos — deriva de decisiones ya tomadas.
Todo su vocabulario ya existe en VOCABULARY.md.

## Objetivo

Definir qué recuerda el sistema entre sesiones, cuándo lo lee, cuándo lo
escribe, y resolver las dos herencias pendientes: H9 inter-sesión y la
extensión *reputación de capacidad*.

## Decisión irreversible

> **La memoria es el puente versionado entre sesiones: se lee al abrir
> (contexto), se escribe al cerrar (salidas), jamás durante. Su historia
> de versiones es append-only.**

## Contexto

- P2 ya lo ordena: nada persiste fuera del `LearningState` y de la capa
  de memoria, compartida y gobernada por el grafo — nunca en el agente.
- RFC-0002 §1 ya fijó el modelo de propiedad: el student model trasciende
  la sesión; la sesión consume una versión y propone la siguiente.
- RFC-0003 ya definió los dos puertos: `contexto` (entrada, inmutable) y
  `salidas` (al cierre: student model vN+1 propuesto, ruta actualizada,
  resumen destilado).
- RFC-0006 delegó aquí la consolidación inter-sesión del refuerzo y la
  extensión de reputación; CONCEPT-0002/RFC-0007 delegaron H9
  inter-sesión.

Este RFC, por tanto, solo tiene que responder: qué versiones existen,
cómo se consolidan, y qué pasa con la deuda y la reputación.

## Propuesta

### 1. La regla de las dos operaciones

La memoria tiene exactamente dos operaciones, ambas en la frontera de la
sesión:

- **Cargar** (apertura, transición T0): resolver las versiones vigentes —
  student model, ruta, deuda abierta, resumen previo — y fijarlas en
  `identidad` + `contexto` (INV-1, INV-2). Todo lo que la sesión podrá
  necesitar entra aquí; la política versionada decide *qué* se carga.
- **Consolidar** (cierre): materializar las `salidas` como nuevas
  versiones — student model vN+1, ruta, deuda, resumen — con procedencia
  de qué sesión las produjo. Una versión jamás se edita: se supersede
  (P14 alcanza a la memoria).

> **La memoria persistente nunca participa directamente de la ejecución;
> durante la sesión, toda la memoria viva reside exclusivamente en el
> `LearningState`.**

El runtime no carece de memoria durante la ejecución — el `LearningState`
entero ES la memoria de trabajo (P2 ya distingue la memoria de trabajo
efímera del estado persistente). Lo que no existe durante la sesión es el
acceso a la memoria persistente:

```
Memoria persistente ──cargar──▶ LearningState ──ejecución──▶ salidas
                                (memoria de       │
                                 trabajo)         └──consolidar──▶ Memoria persistente
```

Si un diseño pedagógico descubre que necesita más memoria a mitad de sesión,
la corrección es ampliar *qué* se carga (política), no *cuándo* (modelo).
Cualquier información que llegue de verdad a mitad de sesión (p. ej. un
docente actualiza algo) entra como fact por el Platform Boundary — es un
hecho del mundo, no una lectura de memoria.

### 1.1 El caso N=0 (primera sesión de un estudiante)

Cargar puede resolver dos estados: existe al menos una versión consolidada
para el estudiante (N≥1), o no existe ninguna versión consolidada previa
(N=0). Este segundo caso no constituye un error ni un estado excepcional,
sino el estado esperado antes de la primera sesión.

En el caso N=0, Cargar deriva un estado inicial del Student Model
correspondiente a ese caso. Este estado inicial no constituye una versión
consolidada y, por tanto, no modifica la historia append-only definida
para las versiones posteriores (P14).

La primera versión consolidada nace únicamente mediante Consolidar, al
cierre de la primera sesión, exactamente bajo las mismas reglas que
cualquier versión posterior.

Esta regla no modifica el comportamiento definido para estudiantes con
una o más versiones consolidadas.

### 2. Qué se recuerda (catálogo cerrado)

1. **El modelo del estudiante** — versionado, append-only. Incluye la
   consolidación del refuerzo (RFC-0006): lo que el sistema aprendió
   sobre la eficacia de sus señales para *este* estudiante ("la modalidad
   visual funcionó en condicionales") es una dimensión del modelo,
   escrita por Modelar a partir de los veredictos de Validar — no un
   almacén aparte.
2. **La ruta** — la progresión sobre los módulos 1–9.
3. **La deuda abierta** — veredicto sobre **H9 inter-sesión: ADOPTADA.**
   Las decisiones `no-observadas` al cierre (INV-12) viajan en las
   `salidas` y entran al `contexto` de la siguiente sesión como evidencia
   cargada: la sesión siguiente sabe qué quedó sin veredicto, y Validar
   puede saldarlo con evidencia nueva. La deuda cruza sesiones como
   contexto — ninguna sección ni almacén nuevo.
4. **El resumen destilado** — la síntesis de la sesión que RFC-0003 ya
   preveía en `salidas`; es lo que evita cargar historias completas.

La secuencia de versiones del modelo del estudiante (v1 → v2 → … → vN) es,
en sí misma, la **evidencia longitudinal** de la tesis: la evolución del
estudiante y de la eficacia de la adaptación, sesión a sesión, con
procedencia completa.

### 3. Reputación de capacidad — veredicto: DIFERIDA

La extensión registrada en RFC-0006 (ponderar la confianza por la tasa
histórica de validación del autor) **no se adopta para el alcance de la
tesis**:

- introduciría un tipo de memoria nuevo — memoria *del sistema*, que
  cruza estudiantes — cuando todo el catálogo §2 es memoria *del
  estudiante*; violaría el mandato de "sin conceptos nuevos";
- la hipótesis operacional (CONCEPT-0001) no la necesita: mide la calidad
  de la adaptación derivada del paisaje, no el meta-aprendizaje del
  sistema sobre sus capacidades;
- el álgebra A1–A8 ya permite lograr efectos equivalentes por política,
  sin nueva infraestructura.

Queda registrada como **extensión post-tesis** en el registro del README.
Si el análisis experimental muestra que una capacidad sistemáticamente
acierta o falla, ese hallazgo será un *resultado* de la tesis — y la mejor
justificación posible para adoptarla después.

## Alternativas consideradas y rechazadas

1. **Memoria consultable a mitad de sesión** (estilo RAG bajo demanda):
   rechazada. Es un canal lateral (P1), rompe la inmutabilidad del
   contexto (INV-2) e introduce lecturas no grabadas que amenazan el
   replay (P12). Lo que haga falta, se carga al abrir.
2. **Un "Memory Agent"**: rechazado. La memoria no es una capacidad del
   dominio — no se enuncia en lenguaje pedagógico (P4) — sino mecanismo
   del Kernel.
3. **Perfil único mutable del estudiante** (UPDATE in place): rechazado.
   Destruye la evidencia longitudinal y contradice P14 extendido; las
   versiones se supersede.
4. **Adoptar reputación de capacidad ahora**: rechazada para este alcance
   (§3).

## Ventajas / Riesgos / Impacto / Complejidad

- **Ventajas:** cero conceptos nuevos (verificable contra VOCABULARY);
  evidencia longitudinal por construcción; la deuda inter-sesión cierra
  H9 sin infraestructura; la frontera lee-al-abrir/escribe-al-cerrar
  mantiene el determinismo intacto.
- **Riesgos:** (1) contexto de apertura que crezca — mitigación: el
  resumen destilado existe para eso y la política decide qué cargar;
  (2) consolidación mecánica de un student model defectuoso — mitigación:
  la versión defectuosa se supersede con la siguiente, y la historia de
  versiones hace el defecto visible y estudiable, no silencioso.
- **Impacto:** el almacenamiento físico de versiones es un ADR futuro
  (mismo criterio: R1–R6 y append-only); RFC-0010 hereda que la
  plataforma consulta el student model vigente a través del Boundary.
- **Complejidad:** baja — el diseño ya estaba tomado; este RFC lo
  consolida.

## Recomendación

Aceptar la regla de las dos operaciones, el catálogo cerrado §2, la
adopción de H9 inter-sesión y el diferimiento de la reputación de
capacidad. Continuar con RFC-0009 (HITL) y RFC-0010 (Frontera) — los dos
últimos documentos de diseño antes del código.

## Consecuencias

- Vocabulario: **ningún término nuevo** (cargar/consolidar son las
  operaciones ya implícitas en RFC-0003; el catálogo usa términos
  existentes).
- H9 queda totalmente resuelta (intra: RFC-0007; inter: aquí).
- La reputación de capacidad pasa al registro de extensiones post-tesis.
- El ADR de almacenamiento de memoria hereda: versiones append-only, con
  procedencia de sesión, sin UPDATE/DELETE (patrón ADR-0002).
