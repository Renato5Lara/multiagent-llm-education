# RFC-0010 — Frontera con la Plataforma (contrato de integración)

- **Estado:** Aceptado (2026-07-10 — última Architecture Review de la
  Foundation Phase; el tesista verificó: cero conceptos nuevos)
- **Autor:** Equipo de arquitectura (Claude + tesista)
- **Fecha:** 2026-07-10
- **Aprueba:** Renato Lara (tesista / Product Owner)
- **Tipo de revisión:** Architecture Review
- **Gobernado por:** P11, P14, P15, RFC-0001 §1, RFC-0003 (Grieta A),
  RFC-0004 §1, RFC-0005, RFC-0007 §5, RFC-0009
- **Capa (RFC-0001 §1):** Platform Boundary
- **Runtime Contract:** define por dónde entran los hechos que responden
  la pregunta 1 y por dónde salen las decisiones que la pregunta 5 valida

**Declaración de vara (mandato del tesista): este RFC introduce CERO
conceptos nuevos.** Todo su contenido es el inventario de lo que los
demás documentos ya delegaron al borde. Si algún término de este RFC no
tiene fila en VOCABULARY.md, el RFC está mal y la Foundation no estaba
cerrada.

## Objetivo

Cerrar el diseño definiendo el contrato único por el que la plataforma
educativa (v1: FastAPI, PostgreSQL, React) consume el runtime — sin
migración, sin compatibilidad, sin wrappers (decisión D-001).

## Decisión irreversible

> **La forma del contrato: cuatro entradas y tres salidas, todas
> expresadas en vocabulario del runtime. El Boundary traduce, jamás
> interpreta; ningún tipo de la plataforma cruza al Kernel o al Domain;
> ninguna operación del contrato permite escribir el estado.**

## Contexto

El inventario delegado al borde por el resto del plano:

- El Boundary autora los hechos del mundo, jamás claims (Grieta A).
- El Boundary traduce sin interpretar (RFC-0004 §1, paso 2).
- Las decisiones se entregan al mundo y la entrega vuelve como fact
  (Walkthrough-0001, T11).
- La entrada humana es un fact con provenance `humano` (RFC-0009).
- La memoria persistente se carga al abrir y se consolida al cerrar
  (RFC-0005).
- Las superficies de lectura: exportación de investigación, Modo
  Evidencia, visor de replay (RFC-0007 §5) y el student model vigente
  (RFC-0005).

## Propuesta

### 1. Las cuatro entradas (mundo → runtime)

| # | Entrada | Qué produce dentro |
|---|---------|--------------------|
| E1 | **Abrir sesión** | la transición T0: cargar memoria persistente → `identidad` + `contexto` (RFC-0005, INV-1) |
| E2 | **Hechos del mundo** — interacciones del estudiante, resultados de actividades, telemetría, ciclo de vida | facts (autor: Boundary o la capacidad correspondiente vía captura; Grieta A) |
| E3 | **Palabra humana** — juicios, aprobaciones, resoluciones de escalada del docente | facts con provenance `humano` (+ `human_reason` opcional) (RFC-0009) |
| E4 | **Cerrar sesión** | la transición de cierre: `salidas` → consolidar en memoria persistente (RFC-0005) |

### 2. Las tres salidas (runtime → mundo)

| # | Salida | Naturaleza |
|---|--------|-----------|
| S1 | **Entregas** — la decisión de experiencia (qué presentar, cómo) hacia la plataforma, que la renderiza; la confirmación de entrega regresa como fact E2 | la única salida "activa" |
| S2 | **Notificaciones de escalada** — aviso al docente de que una deliberación espera su autoridad (RFC-0009), con su contexto navegable | aviso; la respuesta vuelve por E3 |
| S3 | **Superficies de lectura** — exportación de investigación, Modo Evidencia, visor de replay (RFC-0007 §5) y consulta del student model vigente (RFC-0005) | solo lectura; los observadores jamás escriben |

### 3. Las reglas del contrato

1. **Traducción, jamás interpretación.** El Boundary convierte los DTOs
   de la plataforma al vocabulario del runtime y viceversa; no infiere,
   no resume, no decide (RFC-0004 §1). Si algo requiere interpretación,
   entra crudo como fact y lo interpreta una capacidad.
2. **Anticorrupción en ambos sentidos.** Ningún tipo, tabla o convención
   de la plataforma cruza el borde hacia adentro; hacia afuera, solo las
   superficies S1–S3 exponen el interior, y S3 lo expone en vocabulario
   del runtime (la evidencia se muestra como es, no traducida a jerga de
   la plataforma — el Modo Evidencia enseña el vocabulario, no lo
   esconde).
3. **Ninguna operación de escritura del estado.** El contrato no contiene
   —ni contendrá— una operación "actualizar estado": todo lo que entra es
   apertura, hecho, palabra humana o cierre. La mutación es monopolio de
   los reducers (INV-10); la plataforma no tiene reducers.
4. **El contrato es versionado**: forma parte de la `spec_version`
   (ADR-0003). Cambiarlo es enmendar este RFC.
5. **La indisponibilidad no corrompe.** Si el runtime cae, las
   transiciones son completas o inexistentes (R1/R2); qué experiencia de
   contingencia ofrece la plataforma es decisión de la plataforma — el
   runtime no promete degradación elegante, promete no mentir.
6. **El transporte es ingeniería.** HTTP, in-process o cola: lo decide un
   ADR (Engineering Review) preservando este contrato y R1–R6.

### 4. El Legacy, formalmente despedido

Este contrato completa la decisión D-001: la plataforma consumirá el
runtime por E1–E4/S1–S3 y por nada más. No existe modo de compatibilidad,
adaptador de `BaseAgent`, ni doble escritura. El Legacy Runtime permanece
archivado como línea base experimental (grupo de control de la hipótesis
operacional) — intocado, ejecutable, citable.

## Alternativas consideradas y rechazadas

1. **API rica de consulta/mutación del estado** para la plataforma:
   rechazada. El estado no es una API (P1); una operación de escritura
   externa destruiría el monopolio de los reducers (INV-10) y el
   determinismo (P12).
2. **Integración por base de datos compartida** (la plataforma lee/escribe
   las tablas del runtime): rechazada. Acoplamiento por esquema — el
   clásico que sobrevive a todos sus autores; además violaría la
   inmutabilidad multicapa (ADR-0002) por la puerta del DBA.
3. **Domain Events como bus público** (la plataforma suscrita al torrente
   interno): rechazada. Los eventos son derivada interna (INV-10);
   exponerlos como contrato acoplaría a la plataforma a la forma interna
   del estado. La plataforma consume superficies (S3), no el torrente.
4. **Wrapper de compatibilidad con BaseAgent**: rechazado desde el acta
   fundacional (D-001); aquí muere formalmente.

## Ventajas / Riesgos / Impacto / Complejidad

- **Ventajas:** cero conceptos nuevos (verificable contra VOCABULARY); la
  plataforma v1 no necesita rediseño — consume siete operaciones; el
  interior puede evolucionar por completo sin tocar el contrato; la
  regla 3 hace imposible el bypass que arruinaría la tesis.
- **Riesgos:** (1) la tentación de "una operación más" durante la
  implementación — mitigación: regla 4, cambiar el contrato es enmendar
  este RFC, y el Gate lo verifica; (2) S3 con demasiado detalle interno —
  mitigación: son de solo lectura y su forma la gobierna RFC-0007.
- **Impacto:** habilita la Closure Review (no queda diseño pendiente); el
  transporte y los DTOs concretos son los primeros ADRs de la
  Implementation Phase, junto al Blueprint.
- **Complejidad:** baja — es un inventario con reglas; el trabajo
  conceptual ya estaba hecho.

## Recomendación

Aceptar el contrato. Con ello, el diseño queda completo: ejecutar la
**Closure Review** con la pregunta única del tesista — *¿existe algún
concepto usado por la implementación prevista sin definición autoritativa
en la Constitución, un RFC, un Concept Standard, un ADR o el Vocabulary?*
— y, si la respuesta es no, declarar abierta la **Implementation Phase**
con el Architecture Blueprint como primer entregable.

## Consecuencias

- Vocabulario: **ningún término nuevo** (E1–E4/S1–S3 son enumeración, no
  conceptos).
- La plataforma interactúa con el runtime exclusivamente por las siete
  operaciones; toda ampliación enmienda este RFC.
- El Legacy queda formalmente sin puente: solo comparación experimental.
- Quedan habilitadas: la Closure Review y, tras ella, la Implementation
  Phase.
