# ADR-0005 — Estrategia de Pruebas

- **Estado:** Aceptado (2026-07-10, Engineering Review — con la
  convención de token canónico añadida por el tesista)
- **Fecha:** 2026-07-10
- **Preserva:** BLUEPRINT §Suites, RFC-0000 (Gate: la evidencia se
  prueba, no se presume), P7 (los dobles de test no son evidencia)
- **Criterio de aceptación:** toda norma implementada tiene al menos un
  test que la cita por nombre

## Decisión

### 1. Las suites y su mapa

```
backend/tests/runtime/
├── invariants/       INV-1..INV-12          (RFC-0003)   ← ya existe
├── guarantees/       las 4 garantías         (RFC-0004 §2)
├── reconstruction/   R1–R6, kill-test, replay bit a bit (RFC-0008)
├── algebra/          A1–A8 por versión de política       (RFC-0006)
└── walkthrough/      WALKTHROUGH-0001 como test de integración
                      ejecutable: T0–T14 de punta a punta
```

La quinta suite es la novedad de este ADR: **el walkthrough conceptual se
convierte en el test de integración canónico**. Cuando `walkthrough/`
pase en verde, la historia de María (diagnóstico → deliberación →
remediación visual → validación) correrá sobre código real — la
validación conceptual y la de ingeniería serán el mismo artefacto.

### 2. Convención de nombres: el test cita su norma

Todo test de contrato nombra la norma que verifica —
`test_p14_el_estado_anterior_queda_intacto`, `TestInv4Facts`,
`test_a3_sin_reloj_ni_azar` — de modo que:

- `pytest -k INV4` ejecuta la evidencia de una invariante concreta;
- las filas del Engineering Gate citan tests por nombre, no prosa;
- la trazabilidad Código → RFC es *greppeable*.

Un test de contrato sin norma en el nombre no es de contrato: va a la
suite unitaria del módulo correspondiente.

**Token canónico** (añadido por el tesista en la aceptación): la norma se
escribe con guion bajo en lugar de guion (`INV_5`, `R1`, `A4`, `P14`,
`ADR_0001`) y debe aparecer en el node id del test — archivo, clase o
función — de modo que `pytest -k INV_5` ejecute toda su evidencia sin
buscar dónde vive. Cuando un archivo se dedica a una sola norma, se nombra
`test_<NORMA>_<tema>.py`.

### 3. Dobles de prueba

- **El Kernel se prueba sin dobles**: es puro (estado entra, estado
  sale); un mock en un test de invariantes es señal de diseño roto.
- **Las capacidades** pueden usar dobles del LLM en sus tests unitarios
  (fixtures con provenance declarada). Aclaración de alcance: P7 gobierna
  la evidencia del runtime en ejecución, no los dobles de test — y la
  prohibición de "mocks permanentes" (CLAUDE.md) aplica al código de
  producción, no a las suites.
- **`reconstruction/` y `algebra/` jamás usan dobles**: su objeto es
  precisamente el determinismo real.

### 4. Cobertura: la que importa es la del contrato

La métrica primaria no es el % de líneas: es el **mapa
norma → test** — toda invariante, garantía, R y axioma implementados
tienen al menos un test nombrado. El % de líneas del `kernel/` se vigila
como señal secundaria (esperable ≈100 % por su pureza), nunca como
objetivo.

### 5. CI

El pipeline mínimo del runtime, en orden: (1) **lint de imports**
(las reglas del BLUEPRINT — resuelve la observación pendiente de la
primera sesión); (2) `pytest backend/tests/runtime`; (3) linter/format
del código. Los tres son filas de evidencia estándar del Engineering
Gate. La herramienta concreta de lint de imports es implementación; su
obligación, de este ADR.

*Rev. 2 (2026-07-11, orden del tesista):* el lint incluye la regla del
punto único de serialización — **`json.dumps` está prohibido fuera de
`canonical.py`** y el CI falla automáticamente si aparece. El lint se
implementa como suite de pytest (las reglas de importación son tests de
contrato, no tooling aparte).

### 6. Fixtures

Constructores compartidos por sobre (`_fact()`, `_claim()`, `_estado()`)
se consolidan en `tests/runtime/conftest.py` cuando el tercer test los
repita — regla de tres, no anticipación.

### 7. Regresiones planificadas (por disparador)

No se escriben hasta que exista el código que verifican (regla de
no-anticipación); se registran aquí para que nazcan con él.

- **Guardián de P13** — *disparador: la primera capacidad con versión LLM.*
  Test parametrizado sobre las implementaciones de una misma capacidad
  (regla y LLM); compara únicamente el **contrato del claim** — tipo,
  asunto, provenance, estructura — y **jamás el contenido**. Demuestra que
  la implementación se intercambia sin alterar la interfaz.
- **Experimento de H10** — *disparador: la segunda versión de política.*
  **Re-derivación contrafactual** (RFC-0008 §3), no dos corridas vivas: se
  toma la MISMA historia grabada (mismos facts, mismo no-determinismo LLM
  registrado) y se recomputan enrutamiento y confianza efectiva bajo otra
  política. Solo así "la historia, los hashes y la reconstrucción
  permanecen intactos" es literalmente cierto (P14): una corrida viva de
  `politica-v2` produciría su propia historia con sus propios hashes. El
  test verifica que las divergencias aparecen únicamente donde la política
  difiere, sobre una historia original que no se toca.

## Alternativas rechazadas

- **Cobertura de líneas como métrica primaria**: mide ejecución, no
  contrato; permite 100 % con cero invariantes verificadas.
- **Tests de integración ad-hoc** en lugar del walkthrough: inventaría
  escenarios cuando ya existe uno canónico, validado y citable.
- **Mocks del Kernel en suites de contrato**: verificarían el mock, no el
  contrato.

## Consecuencias

- La observación pendiente de la primera sesión (lint de imports en CI)
  queda con dueño: es la pieza (1) del pipeline y candidata a próxima
  implementación de infraestructura.
- `tests/runtime/walkthrough/` es la definición ejecutable de "el runtime
  funciona": su verde será el hito que cierre la primera versión
  operativa.
- Las suites nuevas se crean vacías solo cuando llega su primer test
  (regla de no-anticipación).
