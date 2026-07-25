# Estado de la Arquitectura

**Versión:** UPAO-MAS-EDU Pedagogical Architecture v1.0
**Estado:** Congelada
**Fecha de cierre:** 2026-07-23

## Composición

- [01 — Auditoría](01-AUDITORIA.md)
- [02 — Modelo de Evolución](02-MODELO-EVOLUCION.md)
- [03 — Constitución Pedagógica](03-CONSTITUCION-PEDAGOGICA.md)
- [04 — Flujo Adaptativo Continuo](04-FLUJO-ADAPTATIVO-CONTINUO.md)
- [05 — Traducción al Frontend](05-TRADUCCION-FRONTEND.md)
- [06 — Arquitectura de Experiencia](06-ARQUITECTURA-EXPERIENCIA.md)
- [07 — Sistema Visual de la Experiencia](07-SISTEMA-VISUAL.md)
- [Anexo A — Matriz de Trazabilidad Arquitectónica](ANEXO-A-MATRIZ-TRAZABILIDAD.md)
- [Adenda A — Política de Selección de Forma](ADENDA-A-seleccion-forma.md)
- [Adenda B — Semántica del Rechazo](ADENDA-B-semantica-rechazo.md)
- [Adenda C — Política de Recuperación de Memoria](ADENDA-C-recuperacion-memoria.md)

## Regla de evolución

- Cambios a PP0–PP8 requieren modificar la Constitución y revisar todos los
  documentos posteriores.
- Cambios al Flujo requieren revisar los Documentos 5–7.
- Cambios a los Documentos 5–7 no pueden contradecir la Constitución ni el Flujo.
- Las restricciones técnicas se documentan fuera de esta cadena.
- Las decisiones de producto se documentan fuera de esta cadena, salvo que alteren
  el comportamiento pedagógico.

## Criterios de implementación (post-congelación, observados desde el Commit 1)

Dos propiedades que la secuencia de commits de
[MIGRATION.md](MIGRATION.md) mostró cumplir de forma consistente — se
registran aquí como criterio a mantener en implementaciones futuras, no
como regla nueva de la arquitectura documental:

**Monotonicidad.** Cada commit de implementación añade una capacidad sin
alterar el comportamiento de las anteriores: el Boundary existió sin
consumidores (Commit 1) antes de ser consumido (Commit 3); la
infraestructura de consentimiento existe sin activarse (Commit 4). Ningún
commit reinterpretó lo que el commit anterior ya dejó funcionando.

**Dos líneas evolutivas distintas, que conviene no mezclar en un mismo
commit:**

- **Línea A — capacidad del runtime:** que el motor pedagógico llegue a
  producir nuevas decisiones (ampliar `_PRIORIDAD_POR_MODALIDAD`, un
  productor nuevo vía RFC). Cambia *qué* puede decidir el sistema.
- **Línea B — capacidad de la infraestructura:** que la plataforma ya
  sepa qué hacer cuando esas decisiones existan (contrato, endpoint,
  persistencia, eventos, pruebas, UI). Cambia *cómo* el sistema ejecuta
  lo que ya puede decidir.

El Commit 4 pertenece enteramente a la Línea B. Activar `codigo_guiado`/
`narracion_tutor` pertenece a la Línea A y es un commit distinto, cuando
corresponda.

## Validación aplicada antes de congelar

Un stress-test horizontal (matriz de diez escenarios × siete documentos, criterio:
*¿este documento aporta toda la información necesaria para que el escenario continúe
sin inventar reglas?*) encontró tres contratos de traducción sin especificar entre
capas — no contradicciones. Los tres quedaron cerrados en las Adendas A–C. Una cuarta
observación (dependencia de un cierre de sesión explícito para consolidar memoria) se
reclasificó como Restricción Técnica Conocida, no como vacío arquitectónico — ya
estaba declarada en el Flujo §5 y no amplía la arquitectura, solo exige que la
implementación la documente.

| Tipo | Estado |
|---|---|
| Vacíos arquitectónicos | 0 |
| Contratos de traducción | Cerrados (Adendas A–C) |
| Restricciones técnicas conocidas | 1 (dependencia de cierre de sesión explícito, RFC-0005) |
| Decisiones de producto futuras | Varias (correctamente fuera del alcance) |

No añade arquitectura nueva; añade gobernanza sobre la arquitectura ya definida.
