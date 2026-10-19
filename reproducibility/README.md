# Paquete de evidencia reproducible

Tesis: *Validación de una arquitectura multiagente basada en inteligencia de enjambre para la adaptación multimodal en Programación.*
Informe contrastado: `D2.9.7-CIERRE-BRECHAS-CORRECCION-CUADROS.docx` (versión editorial; los datos provienen de `backend/experiments/`).

**Objetivo:** que una persona ajena al proyecto pueda elegir una cifra de una tabla del informe, encontrar el archivo que la respalda, ejecutar el cálculo y obtener el mismo resultado, o ver por qué no puede.
**No es** una demostración de que las hipótesis se cumplan. Todas las campañas (N1–N11) son **experimentales y no oficiales**.

## Estado de la verificación (ejecución real, Python 3.13.5, entorno limpio)

| | |
|---|---|
| Archivos del manifiesto cuyo SHA-256 coincide | 214 / 214 |
| Filas de `runs.csv` validadas | N2 80/80, N4 60/60, N8 120/120, N8b 60/60, **N9b 160/160**, N11 179/180 (1 excluida: `no_requests`) |
| CSV derivados regenerados por los scripts del proyecto, idénticos byte a byte | 10 / 10 |
| Cifras del informe recalculadas y comparadas | **328 COINCIDEN** (a la precisión publicada), 0 diferencias explicables, **0 discrepancias** |
| Cifras que no pueden reproducirse con este paquete | 13 (con motivo en cada una; ver `outputs/verification_report.json`) |
| Pruebas automáticas | 18 / 18 pasan (`tests/`) |

Tablas **reproducidas** desde los datos publicados: 8, 9, 10 (N2), 11 (N9b), 18, 19 (N8), 20 (N8b); la 17 (N4) salvo `k_stop`.
Tablas **no** recalculadas aquí (estado `PARCIAL`/`NO_REPRODUCIBLE`/`NO_APLICA`): ver [`RESULTS_TRACEABILITY.csv`](RESULTS_TRACEABILITY.csv). Incluye N1, N3, N5, N11 (Tablas 21–24), K10, estado del arte y todo lo que requiere evaluadores humanos (SUS, expertos: no hay datos y **no se simulan**).

> «Coincide» significa que el valor recalculado, redondeado a la precisión del informe, iguala al publicado. No prueba que los datos sean auténticos ni que la hipótesis sea cierta.

## N9 y N9b
- **N9** (`oe_n9_2026-10-13`): campaña **abortada y descartada** (38 de 160 iniciadas; falló Locust). Solo se publica una copia sanitizada de su `campaign.log` (rutas locales sustituidas). No respalda ninguna cifra. Detalle: `data/metadata/N9_ABORTADA.md`.
- **N9b** (`oe_n9b_2026-10-14/campaign_final`): réplica integrada, 160/160 corridas válidas. Respalda la Tabla 11. `campaign/` (159 filas) es su intento interrumpido previo y no se usa.
- No se combinan registros de N9 con N9b.
- Nomenclatura: el informe llama **N8b** al directorio `oe_n10_2026-10-14_n20`.

## Cómo ejecutar
### Google Colab (recomendado)
Abra `notebooks/reproducibilidad_tesis.ipynb` (Archivo → Abrir cuaderno → GitHub, repositorio `Renato5Lara/multiagent-llm-education`, rama/etiqueta que contenga este paquete) y ejecute las celdas **en orden**. No requiere tokens ni claves. La celda C clona el repositorio público en la referencia `REF`; ajuste `REF` a la rama o etiqueta publicada.
La URL directa de Colab solo existirá cuando la rama esté publicada: `https://colab.research.google.com/github/Renato5Lara/multiagent-llm-education/blob/<REF>/reproducibility/notebooks/reproducibilidad_tesis.ipynb`.

### Local
```bash
cd reproducibility
python -m venv .venv && source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r environment/requirements-dev.txt
cd scripts
python verify_hashes.py      # integridad (código 2 si hay error)
python validate_data.py      # esquema y datos (3 = esquema, 4 = datos)
python reproduce_results.py  # recálculo y comparación (5 = discrepancia)
python build_traceability.py
cd .. && python -m pytest tests -q
```
Los scripts escriben en `outputs/`. No modifican `data/`; los scripts del proyecto se ejecutan sobre una copia temporal.

## Contenido
```
README.md  PROVENANCE.md  DATA_DICTIONARY.md  LICENSE-DATA.md  CITATION.cff
EVIDENCE_MANIFEST.csv      SHA-256 recalculado de cada archivo publicado (214)
RESULTS_TRACEABILITY.csv   tabla del informe → campaña → archivo → script → estado
environment/               dependencias fijadas (requirements.txt, environment.yml)
data/experiments/          evidencia copiada byte a byte de backend/experiments (ver STAGING_REPORT.csv)
data/metadata/             informe_D2.9.7_tablas.json (transcripción documental), N9_*, STAGING_REPORT.csv
scripts/                   verify_hashes, validate_data, reproduce_results, build_* , stage_evidence (mantenimiento)
notebooks/                 reproducibilidad_tesis.ipynb (sin salidas guardadas)
outputs/                   informes JSON y tablas de la última verificación
tests/                     pruebas automáticas (incluye controles negativos)
```
Los scripts de análisis del proyecto (sin modificar) están en `data/experiments/oe_n8_2026-10-13/scripts/`.

## Qué falta o está limitado
- **Registros por petición** (`raw/*.csv`, ~222 MB) no publicados: el paso petición → `runs.csv` no es auditable desde este paquete. Sus hashes están en cada `manifest.json`.
- **Licencia pendiente** (`LICENSE-DATA.md`): hasta decidirla, no se concede licencia de reutilización.
- La verificación D2.7 es interna del proyecto, no de un tercero.
- Las campañas se ejecutaron en un único equipo, con régimen de rendimiento variable entre tramos (N11). Detalles en `PROVENANCE.md`.
- No hay evaluaciones humanas ni mediciones en hardware objetivo.
