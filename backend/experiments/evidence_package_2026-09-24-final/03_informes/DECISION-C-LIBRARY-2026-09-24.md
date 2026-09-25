# DECISIÓN C — Estrategia de persistencia de `datasets/adaptation_library/` (2026-09-24)

Fase 3D. Análisis y cierre de decisión; **no se implementa nada**. Rama `feat/pretest-m1-v4` @ `d31d29c`, árbol dirty.
Autoridad: Asesoría → DECISION-CLOSURE (§9.1: biblioteca M1 versionada, «nunca sobrescribe una versión existente», reproducibilidad exigida) → Master Spec → Decision Register → informes 3/3B/3C.
Nota de nomenclatura: «Decisión C» es la etiqueta de la lista A–E de la auditoría pre-commit; **no existe** una `DEC-C` en el Decision Register para este tema (DEC-05 es Redis). El registro formal se hace como sección nueva en DECISION-CLOSURE (§7 de este informe).

## 1. Alcance
Decidir cómo persistir la biblioteca (10 versiones + caché TTS) para: reproducibilidad, próximo evidence package, Git, almacenamiento de artefactos multimodales y trazabilidad lib-v1…lib-v10, sin contradecir la especificación. Solo lectura del repositorio y de la biblioteca; ninguna consulta ni escritura en PostgreSQL. Experimentos: bibliotecas sintéticas de **symlinks** en el scratchpad de la sesión (fuera del repo) para medir dependencias, ejecutando únicamente tests que no usan PostgreSQL (verificado por `grep`; sí usan Redis con prefijos de prueba efímeros).

## 2. Estado actual (observado)

| Dato | Valor | Fuente |
|---|---|---|
| Versiones | 10 (`lib-v1-3f931e10` … `lib-v10-5dd83cd4`) + `_tts_cache/` (393 mp3) | `ls`, manifiestos |
| Linaje | v1→v3→v4→v5→v6→v7→v8→v9→v10; **v2** es rama lateral (base v1, sin descendientes) | `base_version` de cada manifiesto |
| Tamaño **físico** (inodos únicos) | 1 198 MB | análisis de inodos |
| Tamaño **lógico** de las 10 versiones (cada versión con sus propias copias) | 2 226 MB (+383 MB de caché = 2 610 MB) | suma de `size_bytes` |
| Contenido **único** por sha256 (lo que Git almacenaría) | **406.0 MB**: audio 368.5 (378 blobs) · SVG 37.0 (279) · resto 0.5 | manifiestos |
| Manifiestos | 10 archivos, 9.7 MB crudos → **1.1 MB** comprimidos (zlib) | medido |
| Estimación comprimida en Git (zlib por blob, sin deltas) | audio 357.4 MB · SVG 11.1 MB · code/cpp/diagram/text 0.25 MB · manifiestos 1.1 MB | medido |
| Repositorio hoy | 14.6 MB rastreados; pack 9.83 MiB; **mayor archivo rastreado 0.72 MB**; sin `.gitattributes`, sin LFS, sin `.github/` (sin CI) | `git ls-files`, `count-objects` |
| Remoto | `origin` = GitHub `Renato5Lara/multiagent-llm-education`, **visibilidad PUBLIC**, diskUsage ≈ 9.7 MB | `gh repo view` |
| `git-lfs` | **no instalado** (`git lfs` no es un comando) | prueba |
| Precedente de datasets en Git | 5 archivos `.jsonl` pequeños en `datasets/` (`bloom_level_tasks`, `humaneval_pedagogical`, `mbpp_pedagogical`…) | `git ls-files datasets` |
| Caché TTS | 393 mp3 (383 MB): 378 idénticos a mp3 de versiones; **15 huérfanos (14.7 MB)** que ninguna versión usa | comparación por sha256 |
| Hardlinks existentes | v5→v10 comparten inodos (2 008 archivos con `nlink>1`); Git **no** los preserva: un checkout materializa copias independientes | `stat` |

## 3. Inventario exacto y dependencias

### 3.1 Por versión (lo que cada una contiene y para qué sirve)

| Versión | Entradas | Contenido | Función |
|---|---|---|---|
| v1 (24) · v2 (336) · v3 (384) · v4 (672) | audio/código/diagrama/texto | construcción incremental; v2 es rama lateral | historial |
| **v5** (720) | py, mmd, txt, mp3 (sin SVG ni C++) | **`corrida-poc-1`** | evidencia experimental |
| v6 (1 029) · v7 (1 047) · v8 (1 071) | + SVG y C++ (66→75→81) | etapas de las correcciones | historial documentado (auditoría semántica v6–v8) |
| **v9** (1 077) | + C++ 87/90, SVG 270 | **`corrida-poc-2`** | evidencia experimental |
| **v10** (1 080) | C++ 90/90 | última; ninguna corrida | latest / SUS |

Únicos **solo** en v1–v4 y v6–v8 (no están en v5/v9/v10): audio 99 blobs = **99.1 MB**, SVG 9 blobs = 1.5 MB, resto 0.07 MB.
Contenido único v5+v9+v10: **305.3 MB** (audio 269.5, SVG 35.5, resto 0.3).

### 3.2 Dependencias por corrida
- `corrida-poc-1` → `lib-v5-9ae9ffdd`; `corrida-poc-2` → `lib-v9-a0231e9b` (`config.library_version` en JSON y Postgres).
- **Verificar** los resultados congelados (F1, k_stop, matrices) **no requiere la biblioteca**: basta el JSON/CSV y su hash (paquete 2026-09-23).
- **Volver a ejecutar** ciclos sí requiere la biblioteca. Medición de esta fase (bibliotecas sintéticas de symlinks con v5/v9/v10, sin tocar la real):

| Biblioteca disponible | Resultado en `test_cycle_integration` + `test_package_validation` |
|---|---|
| Completa (baseline, Fase 3C) | pasan |
| Sin **audio** (con SVG) | 9 fallan + 13 errores: el ciclo entrega `status=failed` |
| Sin **SVG** (con audio) | 9 fallan + 13 errores: idem |
| Sin audio ni SVG | `test_library_full_coverage`: falla `…audios_are_valid_and_chained`; `test_agents_library`, `test_package_validation` y 8 de `test_cycle_integration` fallan; `test_all_code_variants_pass_reference_behavior_in_real_sandbox` y las pruebas de PSO/fitness/F1 puros pasan (79 pasan en el conjunto ejecutado) |

**Hallazgo:** en el código actual la **validación de paquete es obligatoria en la entrega** (`validation.py` carga los bytes de audio y de SVG; AG0 rechaza un paquete inválido). El camino de selección del PSO lee solo metadatos de audio/SVG (`audio(..., load=False)`), pero **ningún ciclo completo se entrega sin ambos archivos**. Las funciones puras (PSO, fitness, gold/F1) no dependen de la biblioteca.
- Tests que leen la biblioteca real: `conftest.py` (`store` = última versión), `test_agents_library`, `test_library_full_coverage`, `test_cpp_render`, `test_cycle_integration`, `test_package_validation` (vía `store`), `test_corrida_poc_1_preserved` (v5, lee sha256 de entradas incluido audio), `test_evidence_and_tools` (v10 + latest); además `run_experiment`, `analysis/f1_audit`, `multimodal/{builder,extend,verify}`, `stack.py`.
- El paquete 2026-09-23 referencia la biblioteca solo por **manifiestos** (v5, v9 copiados) y por el nombre de versión en los JSON; no contiene artefactos.

### 3.3 Clasificación por naturaleza (para decidir dónde vive cada cosa)

| Clase | Contenido | Único | ¿Reproducible? | ¿Costoso? |
|---|---|---|---|---|
| Metadatos | `manifest.json` (sha256, `derived_from`, tiempos de calibración, `changes`) | 9.7 MB (1.1 MB zip) | No: es el registro de una generación real; su hash da nombre a la versión | No |
| Código Python/C++, texto | salida de LLM validada en sandbox / semánticamente (una sola generación, DEC-09 §9.1) | 0.35 MB | **No garantizado** (muestreo de LLM; diseñado para generarse una vez) | Sí (API + validación) |
| Diagramas `.mmd` | derivados del AST del código por AG3 | 0.15 MB | Sí (algoritmo determinista sobre el código) | No |
| SVG | render de `.mmd` con mermaid-cli 11.4.2 + puppeteer 23.11.1 + Chrome del sistema | 37.0 MB (11.1 zip) | Probable, **bit-identidad no verificada** (Chrome no está fijado) | Bajo |
| Audio | TTS OpenAI sobre el texto (3 perfiles × 90 textos = ≈ 252 000 caracteres en v10) | 368.5 MB | Servicio externo: **bytes idénticos no garantizados** (no verificado; la caché evitó regeneraciones: 0 casos de mismo texto con audios distintos) | Sí (API) |
| Caché `_tts_cache` | copias del audio por clave de entrada | 383 MB (368 duplicados + 14.7 huérfanos) | Derivada de la biblioteca | — |

## 4. Comparación A/B/C/D (sin preferencia)

Cifras en MB salvo indicación. «Local» = checkout de trabajo; «Git» = tamaño estimado del almacén (zlib por blob).

| Dimensión | **A — Git normal** | **B — Git LFS** | **C — Fuera de Git** (solo manifiestos, hashes, índice, instrucciones) | **D — Híbrida** (según la naturaleza de cada artefacto) |
|---|---|---|---|---|
| Qué entra en Git | todo (10 versiones) | punteros LFS + manifiestos; binarios en el servidor LFS | manifiestos + índice + `.gitignore` | manifiestos + todo lo no-audio (+ SVG); audio fuera |
| Tamaño Git | ≈ 370 (10 versiones; ≈ 300 si solo v5+v9+v10) | ≈ 1.1 (punteros/manifiestos) en Git + 358 en LFS | ≈ 1.1 | **≈ 12.4** (≈ 1.3 sin SVG) |
| Tamaño local del checkout | **2 226** lógicos (copias por versión; audio 2 045) | ídem tras `smudge` (o solo lo que se descargue) | 9.7 (manifiestos) | ≈ 181 con SVG (≈ 12 sin SVG) |
| Reproducibilidad de ciclos tras `git clone` | Inmediata | Requiere `git-lfs` + cuota | **No** hasta restaurar todo (artefactos irremplazables de LLM incluidos) | No hasta restaurar **solo el audio** (incluye el código/texto irremplazable ya en Git) |
| Verificación de integridad | sha256 de manifiesto | ídem + OID LFS | sha256 de manifiesto, pero **no hay artefacto** que verificar | sha256 de todo lo presente; audio verificable al restaurar |
| Trazabilidad lib-v1…v10 | Total | Total | Solo metadatos: el contenido de LLM podría perderse | Total para código/diagrama/texto/SVG; audio por hash |
| Dependencia de servicios externos | ninguna (GitHub ya usado) | GitHub LFS (cuota **no verificada**) + `git-lfs` **no instalado** | mecanismo aún inexistente | mecanismo externo solo para el audio (aún inexistente) |
| Riesgo de pérdida | bajo (todo replicado en el remoto) | medio (objetos LFS, cuota) | **alto** para lo irremplazable | medio: solo el audio (357 MB comprimidos, un único origen local hoy) |
| Compatibilidad con evidence package | directa | directa | paquete describe pero no puede reconstruir | directa para lo no-audio; inventario de audio por hash |
| Compatibilidad con auditoría | máxima | alta | débil (no se puede re-auditar sin restaurar) | alta (auditoría semántica no usa audio) |
| Impacto en Git | pack 9.8 → ≈ 380 MiB (**×38**); el mayor archivo (2.1 MB) supera al mayor rastreado hoy (0.72 MB); irreversible en un remoto **público** salvo reescritura de historial | pack pequeño; migrar después a LFS reescribe historia | sin cambios | pack 9.8 → ≈ 22 MiB (×2.2) |
| Impacto en CI/tests | tests corren tras clonar (no existe CI hoy) | igual + `git lfs pull` | tests de integración no corren; hay que marcarlos | tests de ciclo/validación requieren restaurar el audio; PSO/fitness/F1 puros y auditoría semántica corren |
| Impacto en `corrida-poc-1` (v5) | re-ejecución posible | posible | solo verificación por hash del JSON | re-ejecución tras restaurar los 258 MB de audio de v5 (v5 no tiene SVG/C++) |
| Impacto en `corrida-poc-2` (v9) | posible | posible | idem | tras restaurar 258 MB de audio de v9 |
| Futuras corridas / v11… | + los blobs nuevos de cada versión, para siempre (p. ej. v6 añadió ≈ 32 MB de SVG, estimado) | idem en LFS | nulo en Git | ≈ +1 MB en Git por versión (manifiesto+texto) |
| Requisitos adicionales | ninguno técnico; decisión de publicar audio TTS en repo público (términos **no verificados**) | instalar `git-lfs`; verificar cuota; cambia clones | definir mecanismo de recuperación + copia sellada | igual que C solo para el audio; herramienta de inventario/verificación |

Trade-offs que no se ocultan:
1. **A/B maximizan la reproducibilidad inmediata a costa de irreversibilidad en un repositorio público** (una vez publicado, quitar 400 MB exige reescribir historia) y de un checkout de 2.2 GB (Git no conserva hardlinks).
2. **C es la más liviana pero deja fuera de Git material irremplazable** (código/texto de LLM, 0.5 MB en total): su pérdida no se puede corregir regenerando.
3. **D deja un único punto pendiente (el audio)**, pero un clon no ejecuta ciclos completos hasta restaurarlo; a cambio la trazabilidad de todo lo demás queda en Git.
4. **SVG en Git (D) cuesta ≈ 11 MB comprimidos y 170 MB de checkout** por ser el 91 % del contenido no-audio; es prescindible en principio (derivable del `.mmd`), pero la bit-identidad del render no está verificada y los ciclos lo exigen; por eso se incluye.

## 5. Preservación del historial (sin eliminar nada)

| Pregunta | Respuesta (evidencia) |
|---|---|
| ¿Conservar lib-v5? | **Sí**: evidencia de `corrida-poc-1`; sus artefactos (código/texto generados antes de las correcciones de v6) **no están** en v9/v10 |
| ¿lib-v9? | **Sí**: evidencia de `corrida-poc-2` |
| ¿lib-v10? | **Sí**: latest, C++ 90/90, auditada 0/0/0; la que verán los evaluadores |
| ¿v1–v4, v6–v8? | **Conservar** como historial trazable: sus manifiestos (`changes`, sha256) y su código/diagramas/texto (≈ 0.1 MB únicos) son ínfimos; solo su audio (99 MB únicos) plantea el coste, y su descarte sigue **sin decidirse** (Decisión D) |
| ¿Alguna versión es reconstruible? | **Ninguna con garantía**: `.mmd`/SVG son derivables, pero código, texto y audio salen de LLM/TTS y se generaron una vez |

## 6. Impacto sobre reproducibilidad y sobre `evidence_package_2026-09-24`

Para que el paquete demuestre **qué biblioteca usó cada corrida, cuál era latest, qué hashes tenía, qué artefactos había, cómo verificar/reconstruir y qué está en Git**, cualquiera de las opciones exige incluir un **inventario de biblioteca**. Bajo la estrategia propuesta (D), el paquete contendría:
1. manifiestos de v5, v9 y v10 (poc-1, poc-2, latest; ya con el orden numérico corregido en 3C) y, por cada una de las 10 versiones, su `manifest sha256`, linaje y conteos por modalidad;
2. **inventario de audio** (ruta, sha256, tamaño) de v5, v9 y v10 derivado de los manifiestos, y el resultado de `multimodal.verify` **al momento de generar el paquete** (con conteo de archivos de audio presentes localmente);
3. una tabla «dónde vive cada cosa»: Git (manifiestos, código, C++, diagramas, texto, SVG) / fuera de Git (audio, `_tts_cache` no versionada);
4. la auditoría semántica de cada versión (ya en `experiments/results/`) y las corridas congeladas;
5. sin copiar mp3 ni informes de auditoría a Git (los informes viven en `Auditoria Tesis/`; el paquete puede llevar copias congeladas, acordado en 3C).
Lo que el paquete **no** podrá probar bajo D es la bit-identidad del audio sin acceso al almacén externo: solo podrá probar que **el sha256 registrado en el manifiesto** es el de la corrida.

## 7. Riesgos

| # | Riesgo | Mitigación |
|---|---|---|
| R1 | Publicar ≈ 370 MB en un repositorio **público** y no poder retirarlos | no elegir A/B antes de decidir el mecanismo; reescritura de historial como única salida |
| R2 | El audio (357 MB comprimidos; 269.5 MB únicos en v5+v9+v10) tiene **hoy un único origen local** (+ la caché) | copia sellada con lista sha256 antes de tocar nada; ver §9 |
| R3 | Con D un clon no ejecuta ciclos completos hasta restaurar audio | documentado en `REPRODUCIBILITY.md` (§9 de ese archivo); marcar los tests que requieren audio como de integración |
| R4 | Confundir verificación de **resultados** (basta el JSON) con re-ejecución (requiere biblioteca) | declararlo en el paquete |
| R5 | Términos de publicación del audio TTS y de LLM en repo público **no verificados** | verificar antes de elegir A/B o un almacén público |
| R6 | `git-lfs` ausente y cuota de LFS/GitHub sin verificar | no basar la decisión en LFS hasta comprobarlas |
| R7 | El dedupe (Decisión A) no reduce nada en Git y no debe presentarse como parte de esta estrategia | mantener diferido |

## 8. Recomendación técnica

Con la evidencia observada: **D híbrida, particionada por naturaleza** (no por antigüedad):
- **En Git (normal):** los 10 `manifest.json`, y para las 10 versiones todo artefacto **no-audio** (código, C++, `.mmd`, texto y SVG): ≈ 12.4 MB comprimidos, dentro de lo que un repositorio de tesis ya maneja; da trazabilidad completa y hace que la única dependencia externa sea el audio.
- **Fuera de Git:** los mp3 (368.5 MB únicos en las 10 versiones; **v5, v9 y v10: 269.5 MB**, obligatorios de retener) y `_tts_cache/` (derivada; no se versiona ni se necesita).
- **Nunca:** A/B hoy (irreversibles en repositorio público, con términos y cuota sin verificar) ni C (dejaría fuera de Git contenido irremplazable de LLM).
Esto **cambia** la recomendación provisional de la auditoría pre-commit («solo manifiestos en Git») por evidencia nueva: el contenido no-audio son 12 MB, no 400.

## 9. Decisión propuesta

**DECISIÓN C — Estrategia de persistencia de la biblioteca.**
1. **CERRADO (estrategia):** opción D. Dentro de Git: manifiestos de todas las versiones y todos los artefactos no-audio de todas las versiones. Fuera de Git: audio (mp3) y `_tts_cache/`. Ninguna versión se elimina; v5, v9 y v10 se conservan íntegras (incluido su audio) como evidencia y latest.
2. **ABIERTO (mecanismo de almacenamiento externo del audio y, en su caso, LFS):** no se elige proveedor ni mecanismo. **Evidencia que falta para cerrarlo:**
   a. si la asesoría/jurado requieren que el audio sea públicamente descargable o basta con el manifiesto + sha256 (define público/privado);
   b. si existe almacenamiento institucional o personal con retención asegurada (hoy no hay ninguno declarado);
   c. viabilidad de Git LFS: instalar `git-lfs` y cuota del plan de la cuenta (no verificado);
   d. términos de publicación de las salidas de OpenAI TTS/LLM en un repositorio público (no verificado);
   e. política de retención de `lib-v1…v4` y `v6…v8` (Decisión D).
3. **Hasta que se cierre (2):** el audio permanece solo en el disco local y debe protegerse con una copia sellada + lista sha256 (acción propuesta, §10), y ningún mp3 se agrega a Git.

## 10. Acciones necesarias para implementar posteriormente (no ejecutadas)

1. `.gitignore`: `datasets/adaptation_library/_tts_cache/` y `datasets/adaptation_library/lib-v*/artifacts/**/*.mp3`.
2. Herramienta pequeña de **inventario/verificación** (nueva, con RFC/ADR mínimo si aplica): genera `library_inventory` (versión → sha256 de manifiesto, linaje, conteos, presencia de audio) y hace que `multimodal.verify` distinga «audio ausente» de «hash discrepante».
3. Marcar como integración los tests que requieren audio (`test_cycle_integration`, `test_package_validation`, `test_library_full_coverage`, `test_agents_library`, `test_corrida_poc_1_preserved`) con causa explícita, sin ocultar fallos; no usar `skip` genérico.
4. `REPRODUCIBILITY.md` §9: reemplazar «no está autocontenida» por el reparto real (qué viene en Git y qué requiere restauración) cuando se cierre el mecanismo.
5. Copia sellada del audio (v5, v9, v10 como mínimo): `tar` + lista sha256 en un segundo medio bajo control del propietario, antes de cualquier limpieza o dedupe.
6. Plan de commits corregido: añadir un commit «biblioteca: manifiestos + artefactos no-audio» (tras el commit de tablas swarm y antes del paquete), con el `.gitignore` ya aplicado.
7. Generar `evidence_package_2026-09-24` con el contenido de §6 (constructor con `--out` explícito).
8. Cerrar el punto (2) de la decisión con la evidencia a–e.

## 11. Verificaciones ejecutadas
`ls`/manifiestos/`stat` de las 10 versiones y la caché; agregación por modalidad y por conjunto de versiones; compresión zlib por blob; comparación de sha256 caché↔versiones; `git ls-files`/`count-objects`/`git lfs`; `gh repo view` (solo lectura); experimentos con bibliotecas de symlinks (audio y/o SVG ausentes) en el scratchpad de la sesión; comparación de audios por (concepto, clave, texto de origen) entre versiones.

## 12. Integridad (ver check al final del informe de cierre de esta fase)
Ver §Integridad más abajo.

## Integridad
- Hashes de corridas, gold, dataset, manifiestos, auditorías, PSO/fitness/gold y paquete 2026-09-23: comparados con la instantánea de 3C — **idénticos** (resultado en el mensaje final).
- Sin dedupe, sin borrados, sin `git add`/commit/reset/clean, sin escrituras en la biblioteca, sin cambios de PostgreSQL, sin archivos de tesis modificados; documento formal actualizado: solo `DECISION-CLOSURE-2026-09-23.md` (sección nueva §14, añadida al final; el resto del archivo sin cambios, verificado con `diff`).
