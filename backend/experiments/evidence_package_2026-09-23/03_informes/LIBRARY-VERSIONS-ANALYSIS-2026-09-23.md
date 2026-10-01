# Análisis de las versiones de la biblioteca M1 (lib-v1 … lib-v9) — sin borrar nada

Ubicación: `datasets/adaptation_library/`. Todas las versiones selladas son inmutables (hash del manifiesto + sha256 por artefacto; `verify` y las pruebas `test_library_*` lo comprueban). **No se borró ninguna versión**, salvo `lib-v9-32977f23`, un duplicado *idéntico* de `lib-v8` (0 cambios; mismas entradas y anclas) creado por error por una pasada sin novedades y eliminado en la misma sesión (el extensor ahora se niega a sellar versiones sin cambios).

## Linaje, contenido y referencias

| versión | base | conceptos | entradas | creada (UTC) | bytes únicos que añade | referenciada por |
|---|---|---|---|---|---|---|
| lib-v1-3f931e10 | — | 1 | 24 | 01:01 | 8 MB | ancestro de v2 y v3 |
| lib-v2-767b4a53 | v1 | 14 | 336 | 01:10 | 117 MB | **rama hermana** (construcción concurrente accidental); solo filas `multimodal_candidates` de una prueba |
| lib-v3-5fa0acdd | v1 | 16 | 384 | 01:13 | 136 MB | ancestro de v4; filas `multimodal_candidates` de una prueba |
| lib-v4-039dcf58 | v3 | 28 | 672 | 01:19 | 239 MB | ancestro de v5 |
| **lib-v5-9ae9ffdd** | v4 | 30 | 720 | 01:25 | 259 MB | **corrida-poc-1** (100 ciclos) — evidencia; sus tests de inmutabilidad |
| lib-v6-86516a15 | v5 | 30 | 1029 | 03:37 | 44 MB | **libro de cambios**: `manifest.changes` = 48 regeneraciones de código (higiene/cobertura) con motivo y hashes reemplazados |
| lib-v7-7c046f32 | v6 | 30 | 1047 | 03:48 | 3 MB | añade SVG/C++ restantes |
| lib-v8-079928dc | v7 | 30 | 1071 | 03:51 | 6 MB | `manifest.changes` = 5 regeneraciones (Flujo de bucles, Tipos de datos…) |
| **lib-v9-a0231e9b** | v8 | 30 | 1077 | 03:55 | 1 MB | **corrida-poc-2**, tests, endpoint (más reciente) |

Modalidades en v9: código Python 90, C++ 87 (29/30 conceptos; «Tipos de datos primitivos» sin C++ por una divergencia real entre lenguajes: la sobrecarga de `const char*` prefiere `bool` a `std::string`), diagramas Mermaid 270, **SVG renderizado 270**, texto 90, audio 270.

## Diferencias relevantes
- v5 → v6: 48 variantes de código regeneradas (53 marcadas: asserts a nivel de módulo, construcciones ausentes), 3 textos y 9 audios regenerados (p. ej. «desde cero» vs código que cuenta desde 1), 270 diagramas reconstruidos (el constructor ahora dibuja `try/except`) y 243 SVG + 66 C++ nuevos.
- v8: 5 códigos más (con modelo de respaldo y retroalimentación precisa del sandbox).
- Auditoría semántica (`experiments/results/library_semantic_audit_*.json`): v5 = código 53/90, texto 6/90, diagramas 15/270 con hallazgos; **v9 = 0/0/0**.

## ¿Son necesarias v1–v4?
- **v5 y v9: imprescindibles** (las corridas 1 y 2 dependen de ellas).
- **v6 y v8: conservar** (contienen el libro de cambios que documenta qué se corrigió y por qué; v9 hereda los artefactos pero su manifiesto solo lista sus propios cambios).
- **v1, v3, v4: ancestros de v5** — su contenido está íntegro dentro de v5 (v5 los copió), pero v5 los nombra en `base_version`; valor histórico bajo, valor de trazabilidad medio.
- **v2: residuo** (rama hermana sin descendientes ni corridas), salvo su valor como evidencia de la variabilidad de regeneración LLM (mismos conceptos, textos/códigos distintos).

## Tamaño y limpieza PROPUESTA (separada; no ejecutada)
Aparente 1.9 GB · físico 805 MB · contenido único 406 MB → **399 MB duplicados** entre versiones (v1–v5 se copiaron antes de usar enlaces duros; v6–v9 ya usan hardlinks) + `_tts_cache/` 383 MB (393 mp3 idénticos a los de la biblioteca).
1. **Sin perder nada**: deduplicar por hardlink los archivos con el mismo sha256 entre versiones y con `_tts_cache` (ahorro ≈ 399 MB + ≈ 380 MB de caché redundante).
2. Después, y solo si se decide: archivar (no borrar) `lib-v2` fuera del árbol de trabajo.
3. Añadir `datasets/adaptation_library/_tts_cache/` a `.gitignore` (caché regenerable pero costosa de regenerar: ~400 llamadas TTS).
4. Versionar en Git solo `manifest.json` + hashes (o LFS/almacén de objetos) en vez de los binarios.
