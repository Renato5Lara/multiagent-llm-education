# RFC-0000 — Proceso y plantilla de RFC

- **Estado:** Aceptado (2026-07-10; rev. 2 añade la revisión por decisión
  irreversible — aplica desde RFC-0002; rev. 3 añade la categoría Concept
  Standard y la Revisión de Conformidad de Especificación; rev. 4 añade la
  revisión dual Architecture/Engineering y el Ledger, por orden del
  tesista al cierre de la Foundation Phase; rev. 5 añade el Engineering
  Gate; rev. 6 añade la regla de no-proliferación documental, por orden
  del tesista)
- **Autor:** Equipo de arquitectura (Claude + tesista)
- **Fecha:** 2026-07-10
- **Aprueba:** Renato Lara (tesista / Product Owner)

## Objetivo

Definir cómo se proponen, discuten, aprueban y citan las decisiones de
arquitectura del nuevo runtime multiagente, de modo que cada decisión quede
documentada, justificada y sea defendible académicamente en la tesis.

## Ciclo de vida de un RFC

```
Borrador → En revisión → Aceptado
                       ↘ Rechazado
Aceptado → Supersedido (por RFC-NNNN posterior)
```

- **Borrador**: Claude redacta la propuesta completa.
- **En revisión**: el tesista comenta; Claude defiende, corrige o refuta.
- **Aceptado**: solo el tesista puede declarar este estado. Desde ese momento
  el RFC es normativo: el código no puede contradecirlo.
- **Rechazado**: se conserva el documento con la razón del rechazo (es
  evidencia metodológica citable, igual que lo aceptado).
- **Supersedido**: un RFC posterior lo reemplaza; ambos se conservan y se
  enlazan mutuamente.

## Plantilla obligatoria

Todo RFC contiene, en este orden:

1. **Objetivo** — qué decisión se toma y qué problema resuelve.
2. **Decisión irreversible** — el compromiso difícil de revertir que se
   asume al aceptar este RFC. La revisión comienza por esta sección: si la
   decisión irreversible está bien tomada, los detalles secundarios no
   bloquean la aceptación. *(Desde RFC-0002.)*
3. **Contexto** — estado actual, restricciones, relación con la hipótesis de
   la tesis (qué pregunta de investigación fortalece).
4. **Propuesta** — el diseño, con diagramas donde aporten.
5. **Alternativas consideradas y rechazadas** — mínimo una, con la razón
   técnica del rechazo. *Sección obligatoria: un RFC sin alternativas no pasa
   a revisión.*
6. **Ventajas / Riesgos / Impacto / Complejidad** — análisis explícito.
7. **Recomendación** — posición del arquitecto, aunque contradiga propuestas
   previas del tesista.
8. **Consecuencias** — qué queda prohibido, qué deuda se asume, qué RFCs
   futuros dependen de este.

## Reglas del proceso

- Ningún RFC contradice `FOUNDATIONAL_PRINCIPLES.md` (la constitución). Si un
  diseño exige violar un principio, se detiene el RFC, se propone la enmienda
  constitucional, el tesista la aprueba o rechaza, y solo entonces continúa.
- Un RFC = una decisión arquitectónica mayor. Decisiones menores van a `ADR/`
  con el mismo ciclo de vida en formato reducido.
- Los RFC se numeran secuencialmente y nunca se renumeran ni se borran.
- La discusión se hace en iteraciones cortas; no se abren dos RFC en revisión
  sobre el mismo componente a la vez.
- La verdad técnica prima sobre decisiones previas: si un RFC en revisión
  invalida uno Aceptado, se detiene la revisión y se resuelve el conflicto
  primero.
- Nada del Legacy Runtime (`BaseAgent`) se toma como restricción de diseño;
  solo el conocimiento del dominio (pedagogía, módulos, modelos de datos,
  lógica educativa) es insumo válido.
- Los documentos **CONCEPT** (*Concept Standards*) definen la semántica
  del proyecto: vocabulario y significado, jamás implementación. Siguen
  este mismo ciclo de vida, pero su autoridad es semántica: los RFC se
  apoyan en ellos y pueden especializarlos, nunca redefinirlos; cambiar un
  concepto exige enmendar primero su CONCEPT. *(Rev. 3.)*
- Todo término normativo nuevo se registra en `VOCABULARY.md` en el mismo
  commit que lo introduce. *(Rev. 3.)*
- **No-proliferación documental**: toda nueva necesidad debe intentar
  resolverse reutilizando la estructura documental existente
  (Constitución, RFC, Concept Standard, ADR, registros vivos). Solo si
  eso rompe la claridad se propone una categoría nueva, con aprobación
  del tesista. El sistema documental no debe crecer más rápido que el
  runtime. *(Rev. 6.)*

## Dos tipos de revisión (desde el RFC-0008)

*(Añadido en rev. 4, 2026-07-10, por orden del tesista al cierre de la
Foundation Phase.)*

- **Architecture Review** — pregunta: *¿el modelo es correcto?* Se aplica
  a los documentos conceptuales (RFC de modelo, Concept Standards) y a
  toda enmienda del modelo.
- **Engineering Review** — pregunta: *¿esta implementación preserva el
  modelo?* Se aplica a los RFC de ingeniería (0008 en adelante), a los ADR
  y al código (donde se instrumenta como la Revisión de Conformidad).

No se mezclan: una objeción conceptual detectada durante una Engineering
Review no se debate ahí — se traslada al documento conceptual
correspondiente y se resuelve allí antes de continuar.

## Ledger de decisiones

*(Añadido en rev. 4.)* Toda decisión arquitectónica mayor tiene una fila
en `LEDGER.md` (qué se decidió, dónde, estado), añadida **en el mismo
commit** que la introduce o la modifica. El Ledger responde "¿dónde se
decidió esto?"; no contiene contenido normativo — solo punteros.

## Revisión de Conformidad de Especificación (fase de implementación)

*(Añadida en rev. 3, 2026-07-10, por orden del tesista — cierra el ciclo
de gobernanza.)*

Cuando exista código del runtime, ningún cambio se acepta sin responder
cuatro preguntas:

1. ¿Viola algún principio constitucional (P1–P15)?
2. ¿Viola algún RFC o Concept Standard aceptado?
3. ¿Introduce un concepto nuevo? Si lo hace, el cambio se detiene: el
   concepto entra primero por CONCEPT o RFC, después el código.
4. ¿Usa el vocabulario de `VOCABULARY.md`, sin sinónimos inventados?

Un cambio que no supera las cuatro se corrige o se rechaza, y la revisión
queda registrada en el propio cambio.

## Engineering Gate

*(Añadido en rev. 5, 2026-07-10, por orden del tesista.)*

La forma operativa de la Revisión de Conformidad: **la última barrera
antes de fusionar cualquier cambio al runtime**. El cambio presenta una
tabla de conformidad:

| Contrato | Preservado | Evidencia |
|----------|:----------:|-----------|
| P1–P15 | ✅/❌ | … |
| RFCs aplicables (0003, 0004, 0006, 0008, …) | ✅/❌ | … |
| ADRs aplicables (0001, 0002, …) | ✅/❌ | … |

Reglas: (1) una fila sin **evidencia** concreta (test, propiedad
verificada, referencia al diseño) no cuenta como preservada; (2) un ❌
bloquea la fusión — se corrige el cambio o, si la objeción es conceptual,
se traslada al documento correspondiente (revisión dual); (3) el reporte
del gate se registra junto con el cambio. El gate no debate ideas:
verifica contratos.

## Alternativas consideradas y rechazadas

- **Diseñar conversando, sin documentos** (método usado en fases anteriores):
  rechazado porque las decisiones quedan dispersas en sesiones de chat, no son
  citables en la tesis y se re-litigan involuntariamente.
- **Un único documento monolítico de arquitectura**: rechazado porque impide
  aprobar por partes, mezcla decisiones con distinto nivel de madurez y hace
  imposible supersecer una decisión sin reescribir el todo.
- **ADRs puros (sin RFCs)**: rechazado como formato principal porque el ADR
  clásico registra decisiones ya tomadas; aquí necesitamos también el proceso
  de propuesta y debate. Los ADR quedan como formato complementario.

## Consecuencias

- Ningún código del nuevo runtime se escribe antes de que su RFC esté Aceptado.
- El índice canónico vive en `docs/architecture/README.md` y se actualiza en el
  mismo commit que cambia el estado de un RFC.
- El primer RFC de contenido es RFC-0001 (Visión arquitectónica).
