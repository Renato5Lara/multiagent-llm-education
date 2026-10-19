# Conciliación del estado del arte (2026-10-14)

## 1. Qué representa cada cifra
| Cifra | Qué es | Dónde está |
|---|---|---|
| **63** | Referencias de la bibliografía de la tesis D2.5 (48 con DOI que coincide en Crossref; 8 libros/URL sin DOI; 4 con año distinto en línea/impresión; 3 incorrectas o inexistentes: Imran y Almusharraf 2024, Lee et al. 2025, Liu et al. 2024) | `state_of_art/auditoria_referencias_existentes.csv` |
| **49** | Filas de la matriz del repositorio (`ESTADO_DEL_ARTE_MATRIZ.csv`, N8, 2026-10-13): candidatas con metadatos verificados, **no** la bibliografía de la tesis | `ESTADO_DEL_ARTE_MATRIZ_v49_2026-10-13.csv` |
| **51** | Anexo 7 de D2.6 = esas 49 + **2** añadidas en D2.6 (Zheng et al. 2025, que reemplaza al Liu 2024 mal atribuido; Yu et al. 2024, arXiv) | D2.6, Anexo 7 / Tabla A11 |
| **82** | Referencias de la bibliografía de D2.6 (63 − 3 retiradas + 22 añadidas) | `state_of_art/auditoria_referencias_D2.6.csv` |
| **57** | Matriz v2 de esta sesión = 51 + **6** de la búsqueda estructurada del 2026-10-14 (aún no en D2.6) | `ESTADO_DEL_ARTE_MATRIZ.csv` |

Por tanto 49 y 51 **no son discrepancia de error**: 51 = 49 + 2. De las 51 del Anexo 7, 49 están en la bibliografía de D2.6; **Benjamini y Hochberg (1995)** y **Efron (1979)** están en la matriz pero **no se citan** en D2.6 (son referencias metodológicas no usadas). Las 82 referencias de D2.6 son un conjunto distinto de la matriz: la matriz recoge solo las que tienen interés comparativo/metodológico.

(El informe de auditoría de D2.6 indicó que `ESTADO_DEL_ARTE_MATRIZ.csv` estaba en «codificación mixta»; se comprobó: el archivo está en UTF-8 con BOM y se lee íntegro sin errores. La mezcla pudo producirse al abrirlo con otra codificación.)

## 2. Niveles de verificación (no se usa «verificada» como categoría única) — matriz v2, 57 entradas
| Nivel | Definición | Recuento |
|---|---|---|
| L1 | Metadatos verificados (DOI resuelve y coincide: Crossref; arXiv/DataCite para 2 preprints) | 57 (55 Crossref + 2 arXiv) |
| L2 | Resumen leído | 52 |
| L3 | **Texto completo examinado** | **0** |
| L4 | Cifras publicadas extraídas del resumen | 17 |
Pertenencia: 28 de las 57 están en la bibliografía de D2.5; 49 en la de D2.6. Origen: 49 repositorio N8 + 2 D2.6 + 6 búsqueda estructurada.
Comparabilidad: 0 directamente comparables; 8 comparables con reservas (6 + 2 nuevas de secuenciación curricular con PSO); 34 contextuales; 15 metodológicas.

## 3. Búsqueda estructurada reproducible (2026-10-14)
Script `scripts/busqueda_estructurada.py`; resultados `state_of_art/busqueda_estructurada/{prisma_conteos.json,registros_cribados.csv}`.
- Base: OpenAlex (única). Desde 2015-01-01; artículos y actas; 8 cadenas (Q1–Q8, en el JSON). 50 resultados por cadena.
- Recuperados 400; duplicados 16; únicos 384. Excluidos: sin DOI 19; sin resumen 14; no cumplen criterio A (arquitectura/algoritmo: enjambre/PSO/ACO/multiagente/metaheurística) 184; no cumplen criterio B (dominio educativo) 111. **Incluidos 56** (31 con indicadores técnicos en el resumen —latencia, throughput, convergencia, F1, precisión…—; 19 con cifras; 2 con usabilidad).
- De los 56 se leyeron los resúmenes de los 7 con relación técnica más clara y se incorporaron 6 a la matriz (Peng 2022; Sheng 2023; Srinivas 2026; Abdullah y Alzain 2026; Tan 2026; Kozhakhmet 2026). Resultado relevante: **LITE-Trust** reporta latencia de 10,5/9,5 ms y **Lumina** ≈ 11 051 inferencias/s, ambas de inferencia en proceso con otros datos y definiciones; son contexto, no metas.
- **Limitaciones:** una sola base; cribado automático por palabras clave (puede perder estudios relevantes y admitir irrelevantes; varios incluidos son de revistas de menor impacto); sin lectura de texto completo; sin doble revisión. **No es una revisión sistemática completa** y no debe presentarse como tal. La conclusión «ninguna publicación es directamente comparable» es el resultado de esta búsqueda y de la lectura de 52 resúmenes, no una afirmación universal.

## 4. Auditoría de la bibliografía D2.6 (82 referencias)
67 coinciden en Crossref (DOI, autor, año ±1, título); 8 sin DOI (libros/URL); 4 con diferencia de año en línea/impresión o año ausente en Crossref (Chu 2011, Kennedy y Eberhart 1995 y 1997, Wang 2023); 3 sin registro en Crossref (Holm 1979, sin DOI en Crossref; Wu 2025 y Yu 2024, DOI de arXiv). No quedan DOIs que apunten a un artículo distinto del citado. Sigue pendiente la comprobación manual de que **cada afirmación** de los antecedentes está respaldada por el texto completo de su fuente (no realizada).
