# UPAO-MAS-EDU — Arquitectura Pedagógica

Este directorio contiene la **capa pedagógica** de la arquitectura del proyecto:
qué principios gobiernan el aprendizaje adaptativo, cómo se ejecutan en el tiempo, y
cómo se traducen en experiencia de usuario — hasta el borde del lenguaje visual, sin
entrar en implementación.

> **Estado: v1.0, Congelada (2026-07-23).** Ver [ESTADO.md](ESTADO.md) para la
> página de gobernanza completa y la regla de evolución.

**Relación con `docs/architecture/` (raíz):** esta carpeta no reemplaza ni modifica
la Constitución del Runtime ([FOUNDATIONAL_PRINCIPLES.md](../FOUNDATIONAL_PRINCIPLES.md),
P1–P17) ni los RFC/ADR que gobiernan `backend/runtime/`. La complementa: el runtime
rige *cómo se decide*; esta arquitectura rige *qué evidencia alimenta esa decisión* y
*cómo se convierte en experiencia*. Sus principios se numeran **PP0–PP8** para no
colisionar con P1–P17.

## Jerarquía normativa

```
01 Auditoría              → ¿cómo funciona hoy el sistema?
        ↓
02 Modelo de Evolución     → ¿qué puede cambiar sin romperlo?
        ↓
03 Constitución (PP0–PP8)  → ¿qué principios gobiernan el aprendizaje?
        ↓
04 Flujo Adaptativo        → ¿cuándo y en qué orden ocurren esos principios?
        ↓
05 Traducción al Frontend  → ¿cómo los vive el estudiante?
        ↓
06 Arquitectura de Experiencia → ¿cómo se organiza el espacio para esa experiencia?
        ↓
07 Sistema Visual           → ¿cómo se expresa visualmente sin alterar su significado?
```

Cada documento restringe al siguiente sin sustituirlo. Un cambio en un principio
permite identificar exactamente qué documentos posteriores lo heredarían — ver
[Anexo A](ANEXO-A-MATRIZ-TRAZABILIDAD.md).

## Índice

| Documento | Responde | Estado |
|---|---|---|
| [01 — Auditoría](01-AUDITORIA.md) | Estado real del sistema (código verificado) | Cerrado |
| [02 — Modelo de Evolución](02-MODELO-EVOLUCION.md) | Qué puede evolucionar sin romper la arquitectura | Cerrado |
| [03 — Constitución Pedagógica](03-CONSTITUCION-PEDAGOGICA.md) | PP0–PP8 | Cerrado (v3) |
| [04 — Flujo Adaptativo Continuo](04-FLUJO-ADAPTATIVO-CONTINUO.md) | Los 8 Momentos del Ciclo y 3 escalas | Cerrado |
| [05 — Traducción al Frontend](05-TRADUCCION-FRONTEND.md) | Comportamiento UX, sin interfaz | Cerrado + Adendas A, B |
| [06 — Arquitectura de Experiencia](06-ARQUITECTURA-EXPERIENCIA.md) | Organización espacial funcional | Cerrado + Adenda C |
| [07 — Sistema Visual](07-SISTEMA-VISUAL.md) | Lenguaje visual agnóstico de herramienta | Cerrado (1 vacío heredado a implementación) |
| [Anexo A](ANEXO-A-MATRIZ-TRAZABILIDAD.md) | Qué revisar cuando algo cambia | — |
| [Adenda A](ADENDA-A-seleccion-forma.md) | Política de Selección de Forma | Cierra Doc 5 |
| [Adenda B](ADENDA-B-semantica-rechazo.md) | Semántica del Rechazo | Cierra Doc 5 |
| [Adenda C](ADENDA-C-recuperacion-memoria.md) | Política de Recuperación de Memoria | Cierra Doc 6 |
| [ESTADO.md](ESTADO.md) | Gobernanza y regla de evolución | v1.0 |

## Próximo paso

Prototipado y validación (fuera de esta cadena documental). Cualquier ajuste a partir
de aquí debería surgir de evidencia obtenida durante el prototipado o la evaluación
con usuarios — no de seguir refinando la teoría.
