# Dataset sintético de perfiles — `v1`

Nota de trazabilidad del dataset versionado en este directorio. Los datos no se modifican por esta aclaración.

## Estructura

- **n = 100 perfiles** (`profiles-v1.jsonl`), con `profile_id` y `seed` únicos.
- **Diseño factorial 4 × 5 × 5**: 4 arquetipos × 5 dificultades × 5 réplicas por celda.
  - 4 arquetipos (Visual-Dominant, Logical-Syntactic, Explanatory-Conceptual, Balanced-Multimodal): 25 perfiles cada uno.
  - 5 dificultades (secuencial, condicional, repetitiva, arreglos/vectores, funciones): 20 perfiles cada una.
  - 20 celdas arquetipo × dificultad, con **5 réplicas por celda**. La tercera dimensión son réplicas, no conceptos.
- Gold (`gold-v1.jsonl`, `gold-table-gold-v1.json`): se deriva solo de (arquetipo, dificultad), nunca de W.

## Asignación de conceptos

- Cada perfil tiene **exactamente un `concept_id`**.
- Los conceptos **se reutilizan** entre perfiles y celdas cuando el módulo no dispone de cinco conceptos distintos: la variación entre réplicas pasa entonces por `nivel`, `tasa_error_previa` y W (alternativa prevista en DECISION-CLOSURE §8.1).
  Conceptos disponibles por dificultad: 15 / 2 / 4 / 5 / 4 (secuencial, condicional, repetitiva, arreglos/vectores, funciones).
- **Recursividad está excluida** (DECISION-CLOSURE §8.2): ningún perfil usa sus 2 conceptos.
- Se usan **30 de los 32 conceptos** del currículo (`concepts-v1.json` lista los 32 con su módulo).

## Interpretación de «1 perfil ↔ 1 concepto»

Se adopta: **unicidad de la asignación del concepto por perfil** (cada perfil se asigna a un solo concepto; ningún perfil aparece con varios conceptos).
**No** es una biyección 100 perfiles ↔ 100 conceptos, imposible con los 30 conceptos elegibles del currículo.
Base: DECISION-CLOSURE §8.1–§8.2 y DECISION-REGISTER (DEC-07, alternativa «100 perfiles únicos, cada uno con 1 concepto asignado»).
El asesor delegó esta decisión en el tesista (DECISION-CLOSURE §8, nota de fidelidad).

## Reproducibilidad

- `batch_seed = 20260923`; `seed = derive_seed(batch_seed, profile_id, réplica)` (sha256 truncado a 64 bits) → `numpy.random.Generator(PCG64(seed))`.
- W ~ Dirichlet(κ·centroide), κ = 20, centroides `centroids-v1`; el manifiesto (`manifest-v1.json`) registra la semilla, κ, los centroides y el sha256 de `profiles-v1.jsonl`.
- Regenerar (`python -m adaptation_swarm.profiles.build_dataset`, desde `backend/`) requiere PostgreSQL con el currículo real. Con los mismos 32 conceptos de `concepts-v1.json`, `generate_profiles(refs, 20260923, "v1")` produce `profiles-v1.jsonl` idéntico byte a byte.
