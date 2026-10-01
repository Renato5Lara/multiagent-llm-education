# Pruebas que requieren la biblioteca restaurada (`requires_library_audio`)

Decisión C (DECISION-CLOSURE §14): en Git van los manifiestos y los artefactos no-audio; los **mp3 y `_tts_cache/` quedan fuera de Git**.
Un clon del repositorio no trae el audio. Las pruebas de esta tabla lo necesitan físicamente; se identificaron **ejecutándolas contra una biblioteca de v5/v9/v10 sin mp3**
(27 pruebas fallan o dan error; con la biblioteca completa las 27 pasan). Las demás (189 en esa ejecución) pasan sin audio, incluidas las de PSO, fitness y gold/F1 puros.

## Por qué necesitan biblioteca y por qué audio
En el código actual, `AG0` **valida el paquete antes de entregarlo** (`multimodal/validation.py`): carga los bytes del mp3 y del SVG y comprueba su sha256 y la cadena
`audio.derived_from == sha256(texto)`. Si el audio (o el SVG) no está, el paquete es inválido y el ciclo termina en `status=failed`. El camino de selección del PSO solo lee
metadatos, pero ningún ciclo completo se entrega sin ambos archivos. Otras pruebas leen directamente los bytes de los mp3 para verificar su sha256.

## Condición externa
Audio y SVG de `lib-v5-9ae9ffdd`, `lib-v9-a0231e9b` y la última versión (hoy `lib-v10-5dd83cd4`) presentes bajo `datasets/adaptation_library/` (o `SWARM_LIBRARY_ROOT`),
con el sha256 de cada archivo igual al del manifiesto. El mecanismo de recuperación del audio está **PENDIENTE** (Decisión C, §14 de DECISION-CLOSURE); mientras tanto la única fuente
es el disco local del propietario y su copia sellada local (`Biblioteca sellada 2026-09-24/`, fuera del repositorio).

## Pruebas marcadas (27 casos)

| Prueba | Qué requiere del audio/SVG | Evidencia que produce |
|---|---|---|
| `test_cycle_integration.py::test_vertical_slice_end_to_end` | ciclo completo con paquete válido | AG0–AG4 sobre Redis + LangGraph + PSO + paquete real |
| `…::test_langgraph_controls_the_cycle` | ídem | control de LangGraph sobre el ciclo |
| `…::test_pbest_and_gbest_are_updated_and_never_worsen` | ídem | p_best/g_best monótonos |
| `…::test_reproducible_with_fixed_seed` | ídem (dos ciclos) | determinismo por semilla |
| `…::test_correlation_id_reconstructs_the_whole_cycle` | ídem | trazabilidad por `correlation_id` |
| `…::test_gbest_is_broadcast_to_all_agents` | ídem | difusión de g_best |
| `…::test_two_orchestrator_instances_do_not_steal_each_others_replies` | ciclos concurrentes completos | respuestas por instancia |
| `…::test_many_concurrent_cycles_complete_without_connection_exhaustion` | muchos ciclos concurrentes completos | ausencia de agotamiento de conexiones Redis |
| `test_package_validation.py` (6 pruebas, 13 casos) | el paquete entregado se valida abriendo mp3/SVG | validación por modalidad; el orquestador rechaza un paquete inválido |
| `test_api_adaptation.py::test_adaptation_returns_complete_multimodal_package` | respuesta HTTP con paquete completo | RF05 por HTTP |
| `…::test_package_exposes_svg_and_cpp_when_the_library_has_them` | SVG y C++ en la respuesta | exposición de SVG/C++ |
| `test_agents_library.py::test_library_artifacts_are_real_and_valid` | lee y valida los mp3 | sha256 de cada mp3 y cadena audio↔texto |
| `test_library_full_coverage.py::test_all_diagrams_texts_and_audios_are_valid_and_chained` | lee los 270 mp3 | cobertura y cadena hash de los 30 conceptos |
| `test_corrida_poc_1_preserved.py::test_library_lib_v5_is_immutable_and_hash_addressed` | lee mp3 de v5 | v5 inmutable y direccionada por hash |

## Comportamiento y cómo ejecutarlas
- **Biblioteca completa:** se ejecutan normalmente (el encabezado de pytest lo indica: «biblioteca M1: … PRESENTES»).
- **Faltan archivos (ausentes) y modo normal:** se omiten con una razón que cuenta los archivos que faltan por versión; esto **no oculta un fallo**: no hay biblioteca que evaluar. El encabezado dice «FALTAN … se omiten».
- **Modo de evidencia/CI:** `SWARM_REQUIRE_LIBRARY=1 python -m pytest tests/adaptation_swarm -q` — nunca se omiten; la ausencia las hace fallar.
- **Archivo presente con hash incorrecto:** nunca se omiten; la prueba corre y falla (no es «ausencia»).
- **Restaurar y comprobar:** tras copiar los mp3 a su ruta, `python -m adaptation_swarm.tools.library_inventory --check --require-complete` (exit 0 si todo está presente y con hash correcto) y
  `python -m adaptation_swarm.multimodal.verify lib-vN-hash` (exit 0 íntegra · 1 hash incorrecto · 2 solo faltan archivos).

Las pruebas de PSO, fitness, gold/F1, el inventario y la verificación de resultados congelados **no** dependen del audio.
