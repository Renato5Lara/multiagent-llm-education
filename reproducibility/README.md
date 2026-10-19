# Paquete de evidencia reproducible

Tesis: *Validación de una arquitectura multiagente basada en inteligencia de enjambre para la adaptación multimodal en Programación.*
Informe contrastado: `D2.9.7-CIERRE-BRECHAS-CORRECCION-CUADROS.docx` (versión editorial; los datos provienen de `backend/experiments/`).

**Objetivo:** que una persona ajena al proyecto pueda elegir una cifra de una tabla del informe, encontrar el archivo que la respalda, ejecutar el cálculo y obtener el mismo resultado, o ver por qué no puede.
**No es** una demostración de que las hipótesis se cumplan, ni una prueba de que cada experimento se hizo en las condiciones declaradas: demuestra que *con estos archivos y estos scripts* las cifras salen. Todas las campañas (N1–N11) son **experimentales y no oficiales**.

## Cadena que se comprueba
1. **Peticiones → corrida:** cada fila de `runs.csv` se recalcula con el código del proyecto a partir de los registros por petición (`raw/*.csv`): N2, N3, N4, N8, N8b, N9b y N11, sin diferencias (máx. 3.6e-12).
2. **Corridas → resultados derivados:** los 37 CSV/JSON que generan los scripts de análisis del proyecto (sin modificar) se regeneran **byte a byte** tras borrar antes sus salidas.
3. **Derivados → tablas del informe:** se comparan las cifras del informe con lo recalculado.

## Resultado de la última ejecución (Python 3.13.5, entorno limpio, 27 pruebas)
| | |
|---|---|
| Archivos del manifiesto con SHA-256 coincidente | 1540 / 1540 |
| Cifras del informe comprobadas | 869 |
| ↳ `VERIFICADO_DESDE_DATOS` (recalculadas; 3 de la Tabla 13 difieren 1 unidad del último decimal por **doble redondeo demostrado**: `publicacion/AUDITORIA_REDONDEO_TABLA13.md`) | **861** |
| ↳ `VERIFICADO_DESDE_DERIVADO` | 0 |
| ↳ `DISCREPANCIA` | **0** |
| ↳ `NO_REPRODUCIBLE` (con motivo) | 8 |
| Tablas del informe verificadas desde datos | 18: 8–11, 13, 14, 17–24, 28, 29, 40 y 41. Parciales: 6 y 27 |

Detalle por tabla: [`RESULTS_TRACEABILITY.csv`](RESULTS_TRACEABILITY.csv). Detalle por cifra: `outputs/tables/comparacion_con_informe.csv` y `outputs/verification_report.json`.

**Lo que NO está verificado** (estado `PARCIAL`/`NO_REPRODUCIBLE`/`NO_APLICA` en la matriz): estados categóricos de N1 (Tablas 5, 37); K10 histórico (15, 30); pruebas de carga exploratorias (25); síntesis bibliográfica (32, 44); la última fila de la Tabla 6 y las estadísticas por perfil de la 27; SUS y panel de expertos (**no hay datos: 0 evaluadores reales; no se simulan**). Las celdas «sin efecto» de la Tabla 13 no se comprueban.

> «Coincide» significa que el valor recalculado, redondeado a la precisión del informe, iguala al publicado. Un hash prueba la identidad de un archivo frente a una referencia, no que su contenido sea verdadero. Que los registros por petición sean reales (y no fabricados) **no puede demostrarse con cómputo**: solo que las métricas salen de ellos.

## N9 y N9b
- **N9** (`oe_n9_2026-10-13`): campaña **abortada y descartada** (38 de 160 iniciadas; falló Locust). Solo se publica una copia sanitizada de su `campaign.log`. No respalda ninguna cifra (`data/metadata/N9_ABORTADA.md`).
- **N9b** (`oe_n9b_2026-10-14`): réplica integrada, 160/160 corridas válidas; respalda la Tabla 11. Se reanudó con `--resume`: 159 corridas proceden del intento `campaign/` y la corrida `bruteforce|u5|N20-r08` se reejecutó en `campaign_final/raw`.
- No se combinan registros de N9 con N9b. El informe llama **N8b** al directorio `oe_n10_2026-10-14_n20`.

## Cómo ejecutar
### Google Colab
Abra `notebooks/reproducibilidad_tesis.ipynb` desde GitHub (rama `repro/publicable-2026-10-19`, repositorio `Renato5Lara/multiagent-llm-education`) y ejecute las celdas **en orden**. No requiere tokens ni claves. La celda C hace un clon parcial (`reproducibility/` y `backend/adaptation_swarm`) del repositorio público. Enlace de apertura:
`https://colab.research.google.com/github/Renato5Lara/multiagent-llm-education/blob/repro/publicable-2026-10-19/reproducibility/notebooks/reproducibilidad_tesis.ipynb`

### Local (desde un clon del repositorio)
```bash
cd reproducibility
python -m venv .venv && source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r environment/requirements-dev.txt
cd scripts
python verify_hashes.py      # integridad (código 2 si hay error)
python validate_data.py      # esquema y datos (3 = esquema, 4 = datos)
python reproduce_results.py  # recálculo y comparación (5 = discrepancia); ~1,5 min
python build_traceability.py
cd .. && python -m pytest tests -q
```
`reproduce_results.py` usa el código del proyecto (`../backend/adaptation_swarm`); si trabaja con una copia aislada de `reproducibility/`, defina `REPRO_BACKEND` con la ruta a `backend/`. Los scripts escriben en `outputs/`, no modifican `data/`.

## Contenido
```
README.md  PROVENANCE.md  DATA_DICTIONARY.md  LICENSE-DATA.md  CITATION.cff
EVIDENCE_MANIFEST.csv      SHA-256 recalculado de cada archivo publicado (1540)
RESULTS_TRACEABILITY.csv   tabla del informe → campaña → archivo → script → estado
environment/               dependencias fijadas
data/experiments/          evidencia copiada de backend/experiments (≈250 MB; ver data/metadata/STAGING_REPORT.csv)
data/metadata/             transcripción de las tablas del informe, N9, sanitización, exclusiones
scripts/  tests/  notebooks/  outputs/  publicacion/
```
Los scripts de análisis del proyecto (sin modificar) están en `data/experiments/oe_n8_2026-10-13/scripts/`.

## Limitaciones y exclusiones
- **Copias sanitizadas:** 14 archivos de texto (logs, diarios, `provenance.json`) tenían rutas locales con el nombre de usuario; se publican con la ruta sustituida y **no son idénticos** a los originales (`data/metadata/SANITIZACION.csv`: hash de ambos). Sus hashes dentro de los `SHA256SUMS`/`manifest.json` internos de cada campaña ya no coinciden por esa razón.
- **No publicados:** observaciones in-process de N1/N2/N4 de gran tamaño y `statistical_input.csv` (regenerables), registros del intento N9 (solo sus hashes), `.err`, scripts con correo personal, metadatos bibliográficos de terceros. Lista y motivos: `STAGING_REPORT.csv`.
- **Licencia:** el repositorio no declara ninguna; véase `LICENSE-DATA.md` y `publicacion/PUBLICACION_Y_LICENCIA.md`.
- Verificación D2.7 hecha por el propio proyecto, no por un tercero; un solo equipo con régimen de rendimiento variable entre tramos (N11); sin evaluaciones humanas ni hardware objetivo (`PROVENANCE.md`).
