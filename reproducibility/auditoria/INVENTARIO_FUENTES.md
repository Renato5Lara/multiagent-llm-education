# Inventario de fuentes (Fase I)

Separa **hechos observados** (comprobados en esta auditoría), **afirmaciones de informes anteriores** (no aceptadas sin volver a comprobar) e **inferencias** (no verificadas).

## 1. Repositorio y estado
**Hechos observados (2026-10-19):**
- Repositorio de trabajo: `…/Aplicacion_Proyecto/mas-run`; remoto `https://github.com/Renato5Lara/multiagent-llm-education` (público, sin licencia declarada). Hay otros dos clones del mismo remoto (`multiagent-llm-education`, `mas-clean`) y una copia antigua de agosto en `Documents/Proyectos`; el que contiene las campañas N1–N11 es `mas-run`.
- Rama de esta auditoría: `repro/auditoria-integral-2026-10-19`, creada desde el commit `21c7380` de `repro/publicable-2026-10-19` (publicada). `main` y las demás ramas remotas no se tocan. El árbol de trabajo estaba limpio salvo `backend/experiments/oe_*` (campañas originales, **sin rastrear** en Git; se conservan intactas).
- Entorno de ejecución local: Windows 11, Python 3.13.5 (análisis) y 3.12.10 (campañas, según `environment.json` de N1); equipo i7-12700K, 20 vCPU, 31,75 GiB (registrado por el arnés).
- Los 1251 hashes de los `SHA256SUMS` de las campañas originales siguen coincidiendo (comprobado de nuevo en esta auditoría).

**Afirmaciones previas que se volvieron a comprobar:** «861 cifras verificadas» (ver `CONTEO_CIFRAS.md`), «ocho cifras no reproducibles» (ídem), «la Tabla 13 tiene doble redondeo» (ver `AUDITORIA_REDONDEO_TABLA13.md`: **confirmado con los datos**), «Colab ejecutado» (ver `ESTADO_NOTEBOOKS_COLAB.csv`).

## 2. Documentos de tesis: qué versión se audita
| Documento | Fecha (sistema de archivos) | Contenido | Papel |
|---|---|---|---|
| `…RESULTADOS N1-N11 - 2026-10-16 - D2.9.7-CIERRE-BRECHAS-CORRECCION-CUADROS.docx` (sha256 `a6bb2934de7fd512…`) | 2026-10-16 07:08 | informe de tesis con capítulos de resultados, 45 tablas numeradas y anexos | **versión auditada** (única con cifras de resultados; es la más reciente de la serie D2.x) |
| `Informes finales/1. Formato de proyecto de tesis - Ingeniería.docx` (sha256 `aaf94f0bdf0f58d9…`, = V7.1) | 2026-10-17 01:07 | proyecto de tesis (diseño y plan; sin capítulos de resultados) | contraste de objetivos: los cinco OE son **idénticos** a los de D2.9.7 |
| `…NUEVO PLANTEAMIENTO GENERACION MULTIMODAL - 4 PE OE HE - 2026-09-21.docx` | 2026-09-21 | borrador antiguo con **cuatro** objetivos | **obsoleto**: de aquí procede la idea de «cuatro objetivos» |

**Hallazgo.** La versión vigente (D2.9.7 y V7.1) formula **cinco objetivos específicos (OE1–OE5)**, no cuatro. Sus textos literales están en `OBJETIVOS_LITERALES.json`. Por eso hay **cinco** notebooks por objetivo (no cuatro). Si se prefiere entregar cuatro, el OE5 solo tiene evidencia parcial (sin SUS ni panel) y podría quedar como anexo; no se ha decidido por el autor.

No se mezclan resultados de versiones: las cifras auditadas son únicamente las de D2.9.7. `Brechas.docx` y las versiones D2.9.x anteriores no se usan como fuente.

## 3. Campañas (hechos extraídos de los `provenance.json`, `runs.csv` y registros)
Detalle por campaña en `INVENTARIO_CAMPANAS.csv`. Resumen:

| Campaña | Objetivo(s) | Corridas planificadas / registradas / válidas | Observaciones |
|---|---|---|---|
| N1 | OE1 | 9 500 ciclos en proceso (6 300 + 3 200) | sin runs.csv HTTP |
| N2 | OE2 | 80 / 80 / 80 | no oficial |
| N3 | OE3 | 24 000 ciclos → 240 corridas (48 condiciones × 5 lotes) | en proceso |
| N4 | OE4 | 60 / 60 / 60 | N = 20; hubo un intento fallido archivado (`ZeroDivisionError` en el análisis) y se repitió completo |
| N5 | OE5 | 10 réplicas × 100 perfiles | especificación v3 **provisional** |
| N6, N7 | integración / suite de pruebas | — | sin cifras de resultados en las tablas |
| N8 | OE4 | 120 / 120 / 120 | dos intentos previos descartados (`_n8_failed_attempt1_margin5`, `_n8_discarded_attempt2_cpu_contention`), sin rastrear |
| N8b (dir. `oe_n10`) | OE4 | 60 / 60 / 60 | el informe la llama N8b |
| **N9** | OE2 | **abortada y descartada**: 38 de 160 iniciadas (falló Locust en la 38.ª) | solo su log, sanitizado |
| N9b | OE2 | 160 / 160 / 160 | réplica integrada; se reanudó con `--resume`: 159 corridas proceden del intento previo y `bruteforce\|u5\|N20-r08` se reejecutó |
| N11 | OE4 | 180 / 180 / **179** | `u100\|N10-r01` es `no_requests` y se excluye por regla; dos tramos con régimen de equipo distinto |

Ninguna campaña es oficial (`official = False`; clase de entorno `TECHNICALLY_COMPATIBLE_P6_PENDING`). Todas se ejecutaron en un único equipo con el generador de carga en la misma máquina. Los `provenance.json` de N8, N8b, N9b y N11 registran `design.start_margin_s = 20` y `code.dirty = null` (el estado sucio del árbol no se registró): el código que las ejecutó incluye el cambio de `http_campaign.py` que hoy es el commit `f4687e4`.

## 4. Datos publicados y datos que solo existen en local
- **Publicados** (`reproducibility/data/experiments/`, ≈ 253 MB, manifiesto de 1 545 archivos): `runs.csv`, registros por petición (`raw/*.csv`) de N2, N4, N8, N8b, N9b y N11, observaciones por ciclo de N1 y N3, réplicas de N5, scripts de análisis del proyecto, derivados y metadatos.
- **Solo en local o en Git:** observaciones in-process de N1/N2/N4 de gran tamaño y `statistical_input.csv` (regenerables), registros por petición del intento N9 (solo hashes), y las campañas originales completas en `backend/experiments/oe_*` (sin rastrear). K10 (`backend/official_runs`) y la prueba de carga de antecedente (`backend/loadtest/results`) están **rastreados en Git** y los notebooks los obtienen con un clon parcial; no se duplican en el paquete.
- 14 archivos de texto se publican como **copias sanitizadas** (rutas locales sustituidas): `data/metadata/SANITIZACION.csv`.

## 5. Seguridad y privacidad (comprobado)
Sin coincidencias de claves, tokens, contraseñas, correos ni rutas locales en los archivos publicados (heurística; el apellido del autor figura en `CITATION.cff`). El correo personal del autor apareció en seis scripts bibliográficos y los metadatos con correos de terceros: se **excluyeron**. `backend/.env` está ignorado por Git y no se leyó. El texto de la tesis (prosa) **no** se publica: el CSV de conciliación solo incluye fragmentos de ±35 caracteres en torno a cada cifra y `informe_D2.9.7_tablas.json` contiene el texto de las tablas del informe (decisión de publicación ya tomada antes; el autor puede retirarlo si prefiere no exponer ese texto).

## 6. Inferencias no verificadas
- Que las campañas se ejecutaron en las fechas y condiciones declaradas: solo consta lo registrado por el propio arnés (`provenance.json`, hashes); no hay prueba externa.
- Que el código que produjo cada campaña es exactamente el del commit publicado: lo respalda la coincidencia del campo `start_margin_s`, no un hash del árbol.
