# Índice de evidencia experimental — PoC `adaptation_swarm` (corridas 2026-09-23; paquete 2026-09-24)

> **Qué está en Git (2026-09-24).** Versionados: dataset y gold, biblioteca M1 (manifiestos y artefactos no-audio), corridas congeladas `corrida-poc-1/2` con sus auditorías, la sensibilidad, sus pruebas
> (`experiments/results/adaptation_swarm_frozen_runs.md` y `..._sensitivity.md` fijan semilla, versiones, configuración PSO, métricas y sha256), el paquete de evidencia que este índice describe
> (`experiments/evidence_package_2026-09-24-final/`, con `tools/build_evidence_package` para los comandos `--verify`/`--check` de abajo y la nota `experiments/EVIDENCE_PACKAGE_STATUS.md`) y `loadtest/` con sus resultados.
> Las cifras de auditoría F1, auditoría semántica y carga de este índice se contrastaron el 2026-09-24 con esos archivos. **No se declara cumplimiento de la asesoría:** F1_adapt = 0.8031 < 0.85.
>
> **Actualización 2026-09-25.** El estado de cierre, la matriz de 29 requisitos y lo que no puede afirmarse están en `CIERRE_POC.md`; **la hipótesis H1 no está confirmada**. Este índice y `experiments/evidence_package_2026-09-24-final/` no incluyen los commits posteriores al 2026-09-24
> (`081b426`, `fe5bd64`, `9c4808f`: inmutabilidad de `lib-v5`, reconstrucción parcial de `corrida-poc-1` y pruebas de sandbox). Las copias internas del paquete son instantáneas congeladas (`experiments/EVIDENCE_PACKAGE_STATUS.md`).

Todo lo listado está en este paquete con su sha256 (`MANIFEST.sha256`; verificar con
`python -m adaptation_swarm.tools.build_evidence_package --verify <este_directorio>`; hechos: `--check <este_directorio>`). Estados: **DEMOSTRADO** (medido, con evidencia) ·
**DEPENDE DE PERSONAS** (no se puede demostrar con software) · **ABIERTO** (resultado medido que no alcanza el umbral).

## 1. Congelado (no se edita, no se re-ejecuta sobre el mismo `run_label`)
| corrida | biblioteca | casos | F1_adapt | CR | evidencia |
|---|---|---|---|---|---|
| `corrida-poc-1` | lib-v5-9ae9ffdd | 100 | **0.8031** (IC95 0.711–0.877) | 1.00 | `02_corridas_y_auditorias/adaptation_swarm_corrida-poc-1*.json/csv`, `db_corrida-poc-1_*` |
| `corrida-poc-2` | lib-v9-a0231e9b | 100 | **0.8031** (IC95 0.711–0.877) | 1.00 | `…corrida-poc-2*`, `db_corrida-poc-2_*` |
Ambas con la misma configuración (semilla 20260923, N=20, w=0.729, c1=c2=1.494, ε=0.001, k_max=15, α/β/γ/δ=.40/.30/.15/.15, dataset `profiles-v1`).
La única variable que difiere es la versión de biblioteca. **Ninguna etiqueta predicha cambió entre ambas** (0/100): el F1 idéntico no es un ajuste,
es un resultado estable frente a la mejora de artefactos. **No son réplicas independientes** (misma semilla, dataset y configuración): es **una** medición vista con dos bibliotecas, no dos evidencias separadas. `lib-v10-5dd83cd4` (C++ 90/90) es posterior y NO se usó en ninguna corrida.

## 2. DEMOSTRADO
- **Arquitectura AG0–AG4 sobre Redis + LangGraph**, ciclo completo por perfil (100/100 ciclos, 0 fallos): `03_informes/IMPLEMENTATION-PHASE1/2-REPORT`.
- **PSO** con las ecuaciones de la asesoría, φ, p_best/g_best, parada literal (ε=0.001, k_max=15): `k_stop` medio 1.65 (poc-1) y 1.79 (poc-2), máx 4 y 5; CR=1.00.
- **Diagnóstico del PSO** (`PSO-AUDIT-corrida-poc-1.md`): g_best no cambia tras la inicialización en 48 % de los ciclos; la búsqueda mejora 𝓕 sobre la mejor partícula inicial en 52 %.
- **Artefactos multimodales reales** (de la **biblioteca**): código Python validado en sandbox y C++ compilado y ejecutado en sandbox (90/90, solo desde `lib-v10`), diagramas Mermaid **renderizados a SVG** (270/270), texto validado semánticamente, audio TTS real. **Los paquetes de las corridas contenían código Python**: `corrida-poc-1/2` usaron `lib-v5` y `lib-v9`; ninguna corrida usó `lib-v10`, así que el C++ está validado en la biblioteca y el sandbox pero **no** como modalidad de esas corridas. 100/100 paquetes válidos en poc-2 (`04`/`02`).
- **Validación semántica** (código/texto/diagramas con hallazgos, medida por la herramienta sobre cada versión; un archivo por versión en `library_semantic_audit_<versión>.json`): lib-v5 53/90 · 6/90 · 15/270; lib-v6 8/90 · 3/90 · 0/270; lib-v7 5/90 · 0/90 · 8/270; lib-v8, lib-v9 y **lib-v10** 0/90 · 0/90 · 0/270. El archivo de v9 se generó al extenderla hacia v10 (audita la versión *base*); el de **lib-v10-5dd83cd4** se generó aparte con `extend --base lib-v10-5dd83cd4 --audit-only` (2026-09-24) y es un archivo propio, no una inferencia desde v9.
- **Auditoría de F1** (`F1-AUDIT-corrida-poc-1/2.md`): sin bug; F1 = F1 del óptimo global de 𝓕 (0.803); argmax(W) = 0.615; 13 errores por W≠gold, 6 por Coher/Redund/CostT.
- **Rendimiento** (Locust y JMeter, 5 escenarios × {1, 4 workers}, `04_carga/`): 1 worker ≈ 16 req/s, P95@25 usuarios ≈ 2.2 s; 4 workers ≈ 41 req/s, P95@25 ≈ 1.1 s; 0 % errores. Generador y servidor comparten host (8 hilos, ~7.5 GiB de RAM, frente a los 8 vCPU / 32 GB de la asesoría); una sola corrida por escenario y herramienta; la latencia es de **selección desde una biblioteca generada offline** (M1), sin descarga de audio ni persistencia asíncrona.
- **Reproducibilidad**: `05_documentacion/REPRODUCIBILITY.md`; cadena Alembic verificada desde BD vacía con el bootstrap documentado; biblioteca verificable por hash (`multimodal.verify`).

## 3. ABIERTO (medido; no alcanza el umbral con la configuración cerrada)
- **RNF03 F1_adapt ≥ 0.85**: 0.8031 en ambas corridas. Es una propiedad de la definición (gold por centroide vs. W muestreado + 𝓕), no un defecto de implementación.
  No se ajustaron pesos, gold, regla de parada ni distribución para modificarlo; cualquier cambio requiere una decisión formal nueva y se reportaría como post-hoc.
  La sensibilidad pre-registrada (α ∈ {0.3, 0.4, 0.5}, N ∈ {10, 20, 30}; `adaptation_swarm_sensitivity.json`) es evidencia complementaria, no una corrida principal: ninguna configuración alcanza 0.85 (máximo 0.8164) y no se adoptan.
- **RNF01/RNF04 con 1 worker**: **no cumplen** (P95@25 ≈ 2.2 s; ≈ 16 req/s). Cumplen con 4 workers (configuración declarada por el tesista, no por la asesoría; P95@50 ≈ 2.1–2.4 s y P95@100 ≈ 4.0–4.5 s quedan fuera del criterio, que es hasta 25 usuarios).
- **RNF02 T_conv ≤ 15**: satisfecho (máx 5) pero tautológico por `k_max=15`; el CR=1.00 está inflado por la parada literal en plateaus (DEC-10).

## 4. DEPENDE DE PERSONAS (PENDIENTE DE RECOLECCIÓN HUMANA)
- **RNF05 SUS > 75** (n ≥ 10 docentes/ingenieros): infraestructura lista (`sus_cli`, tablas vacías); **0 respuestas**.
- **Validación del gold por el panel** (20 celdas, acuerdo/κ de Fleiss): infraestructura lista; **0 valoraciones**.
- Hasta que existan participantes reales, ni SUS ni el acuerdo del panel pueden reportarse; no se simulan. Protocolo, datos a conservar, cálculo y criterio de aceptación: `CIERRE_POC.md` §4.

## 5. Biblioteca M1 y estrategia de persistencia (Decisión C — DECISION-CLOSURE §14) — ESTRATEGIA CERRADA: D híbrida · MECANISMO EXTERNO DEL AUDIO: PENDIENTE
- **Qué biblioteca usó cada corrida** (`07_biblioteca/library_map.json`, inventario y manifiestos): `corrida-poc-1` → `lib-v5-9ae9ffdd`; `corrida-poc-2` → `lib-v9-a0231e9b`;
  **latest = `lib-v10-5dd83cd4`** (orden numérico de versión; ninguna corrida la usó). Hashes: `07_biblioteca/manifests/*.manifest.json` y `library_inventory.json` (sha256 del manifiesto y de cada artefacto, por versión).
- **Qué está en Git y qué no:** en Git, los manifiestos de las 10 versiones y todos los artefactos **no-audio** (código Python, C++, `.mmd`, texto, SVG). **Fuera de Git y fuera de este paquete:** el audio (mp3) y `_tts_cache/`.
  Este paquete NO contiene mp3; `07_biblioteca/audio_sha256_<versión>.txt` lista el sha256 de cada mp3 de las versiones de las corridas y de la última, derivado de sus manifiestos.
- **Qué artefactos había:** `library_inventory.json/.md` (por versión: archivos, entradas por modalidad, bytes, presencia y integridad de audio y SVG, `unlisted_files`) calculado desde los archivos reales el día de la generación.
- **Verificar ≠ reproducir:** los resultados congelados (F1, k_stop, matrices) se **verifican** con los JSON/CSV y su hash, sin la biblioteca. **Volver a ejecutar** ciclos exige la biblioteca con **audio y SVG** presentes
  (la validación del paquete es obligatoria al entregar; `05_documentacion/LIBRARY_TESTS.md`).
- **Cómo reconstruir/verificar la biblioteca:** restaurar los mp3 en su ruta y ejecutar `python -m adaptation_swarm.tools.library_inventory --check --require-complete` y `python -m adaptation_swarm.multimodal.verify lib-vN-hash`
  (los estados «ausente» y «hash incorrecto» son distintos).
- **Copia sellada local del audio** (`07_biblioteca/sealed_copy/`): copia adicional de los mp3 de las 10 versiones, con `SHA256SUMS`, verificada al generar el paquete. **Es una copia local; NO constituye almacenamiento externo de preservación institucional.**
- **Pendiente (no resuelto aquí):** el mecanismo de almacenamiento externo del audio (requisitos del asesor/jurado, almacenamiento disponible, Git LFS/cuota, términos de OpenAI TTS/LLM, retención de v1–v4 y v6–v8).

## 6. Estructura de este paquete
`01_datos_de_entrada/` dataset sintético + gold · `02_corridas_y_auditorias/` corridas congeladas, auditorías F1/PSO, auditorías semánticas de v5…v10, exportación de Postgres · `03_informes/` **copias congeladas** de los informes de `Auditoria Tesis/`
(las copias no convierten esa carpeta en parte de Git; el informe de la Fase 3E no está incluido porque se escribe después de generar el paquete) · `04_carga/` Locust y JMeter · `05_documentacion/` ADR, reproducibilidad, pruebas que requieren biblioteca, materiales SUS/panel (plantillas vacías) ·
`06_entorno/` versiones, `alembic_head` (dinámico), `git_status`, `pip_freeze`, estado SUS/panel (0/0/0 al generar) · `07_biblioteca/` inventario, mapa, manifiestos, listas sha256 del audio, copia sellada · `MANIFEST.sha256`.
