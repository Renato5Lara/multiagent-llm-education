# ADR-0004 — Estrategia de Manejo de Errores

- **Estado:** Aceptado (2026-07-10, Engineering Review — con la regla de
  clasificación por defecto añadida por el tesista)
- **Fecha:** 2026-07-10
- **Preserva:** P5, P7, RFC-0003 §4 (dos resultados), RFC-0007
  (telemetría operativa ≠ evidencia), R1/R2/R5, E5 (CONCEPT-0001)
- **Criterio de aceptación:** R1–R6 intactos; ningún error se disfraza de
  evidencia

## Decisión

Cinco categorías de error, cada una con exactamente un destino. La regla
madre: **un bug jamás se disfraza de rechazo** — los rechazos son
evidencia del dominio (P7); los bugs son defectos del software. Mezclarlos
contaminaría la historia científica con fallas de programación.

> **Regla de clasificación por defecto** (añadida por el tesista en la
> aceptación): *toda excepción que no pertenezca explícitamente al
> dominio es un defecto del software hasta demostrar lo contrario.* No
> existen "errores especiales" sin categoría: lo inclasificado es E-2.

| # | Categoría | Ejemplo | Destino |
|---|-----------|---------|---------|
| E-1 | **Dominio** — el contenido de una propuesta viola una invariante | claim sin respaldo vigente | JAMÁS excepción: `Rechazado` + `TransicionRechazada` (RFC-0003 §4, ya implementado) |
| E-2 | **Programación** — el propio runtime está mal escrito | invariante interna rota, tipo imposible | propagar y **abortar ruidosamente**; nunca capturar, nunca convertir en evento |
| E-3 | **Infraestructura** — la transición no pudo persistirse | BD caída, fallo de serialización | por R1/R2 la transición **no existe**; registro en telemetría operativa (RFC-0007), jamás Domain Event; recuperación = reanudación (R5) |
| E-4 | **Producción** — una capacidad no logró producir | timeout del LLM, llamada fallida | silencio, no ruido: la capacidad no aporta, la sesión continúa (E5); el reintento es política del engine; registro en telemetría operativa |
| E-5 | **Frontera** — entrada malformada del mundo | DTO inválido de la plataforma | error al llamador en el Boundary; **nada entra al estado** |

## Reglas operativas

1. Los reducers capturan **únicamente** el `ValueError` estructural que
   surge de construir entradas con datos de la propuesta (E-1 → rechazo
   registrado). Cualquier otra excepción se propaga (E-2).
2. Prohibido `except Exception` amplio en `kernel/` y `domain/`.
3. Prohibidos los eventos genéricos de "error": el único evento de fallo
   del dominio es `TransicionRechazada`, con su invariante nombrada.
4. No se definen jerarquías de excepciones propias mientras las estándar
   basten (no-proliferación aplicada al código); si una capa las
   necesita, se amplía este ADR.
5. E-3/E-4 nunca aparecen en las superficies de evidencia (S3): viven en
   la telemetría operativa, separada normativamente (RFC-0007, alt. 2).

## Alternativas rechazadas

- **Convertir toda excepción en `Rechazado`**: esconde bugs como si
  fueran hechos del dominio — corrompe la evidencia (P7) y vuelve
  indistinguible "el sistema rechazó" de "el sistema falló".
- **Jerarquía de excepciones custom desde el día uno**: sobreingeniería;
  las categorías ya distinguen por destino, no por clase.
- **Reintentos dentro del Kernel**: el reintento es política de ejecución
  (engine), no mecanismo del agregado (P5).

## Consecuencias

- `registrar_fact` ya cumple E-1; todo reducer futuro sigue el mismo
  patrón: capturar solo la invalidez del contenido propuesto.
- El engine hereda E-3/E-4 (reintentos, telemetría operativa) como
  requisitos de su implementación.
- Los tests de contrato verifican ambos lados: que la violación de
  propuesta rechaza-y-registra, y que el bug **no** se convierte en
  rechazo.
