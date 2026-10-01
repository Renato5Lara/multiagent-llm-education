# `corrida2_evidence_assignment_v1.csv` — reproducibilidad

Artefacto técnico de planificación (R21), no documentación de tesis. Define
la entrada sintética previa a la generación — no contiene CMG, condición,
ni ninguna dimensión de calidad (D1/D2/D3).

## Regla de asignación

**No** se usa la paridad de `Concept.order` directamente: `order` reinicia
por módulo (1..6, 1..4, 1..5, 1..2, 1..4, 1..4, 1..5, 1..2 para M1..M8), y
la paridad de ese valor per-módulo produce **17 impares / 15 pares** — no
16/16 (verificado, no supuesto: dos módulos, M3 y M7, tienen 5 conceptos
cada uno — un total impar — lo que desequilibra el conteo global en +2).

Regla usada: un **índice de posición global 1..32**, construido ordenando
los 32 `Concept` por `(LearningObjective.order, Concept.order)` — la
secuencia curricular ya declarada por la migración `d6e7f8a9b0c1_
migrate_is301_to_8_modules.py` (Módulo 1→8, y dentro de cada módulo, el
orden ya sembrado de sus conceptos) — sin ningún criterio nuevo. El perfil
se asigna por la paridad de esa posición global:

```
posición global impar (1, 3, 5, ..., 31) → E1
posición global par   (2, 4, 6, ..., 32) → E2
```

Como la posición global recorre 1..32 sin reinicios, produce exactamente
16 impares y 16 pares — verificado, no asumido.

## Por qué es válida

- Depende únicamente de `LearningObjective.order`/`Concept.order` — ambos
  ya existían en el catálogo antes de esta ronda, sembrados por la
  migración del currículo, sin relación con D1/D2/D3, Bloom, dificultad,
  longitud o nombre del concepto, ni con ningún resultado del Piloto 1.
- La regla se fijó **antes** de observar cualquier resultado de calidad —
  de hecho, esta ronda (R21) es exclusivamente de auditoría y planificación,
  no se generó ningún CMG ni se evaluó D1/D2/D3 de Corrida 2.
- Regenerable: `SELECT ... ORDER BY lo.order, c.order` + paridad del índice
  de enumeración es determinista — dos ejecuciones independientes producen
  el CSV byte-a-byte idéntico (verificado).

## Perfiles

| Perfil | errors | items_totales | p | Confianza esperada (R16) | Configuración esperada |
|---|---|---|---|---|---|
| E1 | 2 | 10 | 0.2 | cr=0.690, co=0.810 | `avanzar-con-andamiaje` → `{mixta, fundamentos}` |
| E2 | 10 | 10 | 1.0 | cr=0.850, co=0.650 | `reforzar` → `{visual, fundamentos}` |

`items_totales=10`: parámetro del **instrumento experimental sintético**
(R16 §5/R19 Fase 6) — nunca el tamaño real de un banco de evaluación ni una
propiedad de `Concept` (R16-A: no existe tal fuente real para 26 de los 32
conceptos).

## Procedencia

Catálogo consultado: tablas `concepts`/`learning_objectives` de
`upao_mas_edu` (PostgreSQL real), estado al 2026-09-22 — 32 `Concept` / 8
`LearningObjective`, mismo catálogo cerrado usado por el Piloto 1 y por
`CMGGenerationService` (`app/services/cmg_concept_catalog.py`).
