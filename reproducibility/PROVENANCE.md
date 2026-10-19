# Procedencia

## Qué es este paquete
Copia, sin modificar su contenido, de la evidencia mínima de `backend/experiments/` que respalda las cifras de las Tablas 8–11 y 17–20 del informe D2.9.7 («Validación de una arquitectura multiagente basada en inteligencia de enjambre para la adaptación multimodal en Programación»), más los scripts de análisis del proyecto y las metadatos de cada campaña. `data/metadata/STAGING_REPORT.csv` lista cada archivo copiado y cada excluido, con el motivo.

## Campañas (todas no oficiales)
| Campaña (informe) | Directorio | Estado | Uso en este paquete |
|---|---|---|---|
| N1 | `oe_n1_2026-10-05` | no oficial | solo metadatos e informe OE1; observaciones no publicadas (tamaño) |
| N2 | `oe_n2_2026-10-05` | no oficial, 80/80 corridas | **Tablas 8, 9, 10** recalculadas desde `campaign/runs.csv` |
| N3 | `oe_n3_2026-10-06` | no oficial | `runs_oe3.csv`; ANOVA regenerado byte a byte |
| N4 | `oe_n4_2026-10-06` | no oficial, 60/60 | **Tabla 17** (sin `k_stop`) |
| N5 | `oe_n5_2026-10-06` | provisional (v3, `official=False`) | solo archivos; sin recálculo celda a celda |
| N6, N7 | `oe_n6/7_2026-10-06` | consolidación y suite de pruebas | solo archivos |
| N8 | `oe_n8_2026-10-13` | no oficial, 120/120 | **Tablas 18, 19**; contiene además los scripts de re-análisis y sus salidas |
| **N9** | `oe_n9_2026-10-13` | **ABORTADA Y DESCARTADA** (38 de 160 iniciadas) | solo `campaign.sanitizado.log` (copia con rutas locales sustituidas); ver `data/metadata/N9_ABORTADA.md`. **No respalda ninguna cifra.** |
| **N9b** | `oe_n9b_2026-10-14` | réplica integrada, 160/160 `ok`, no oficial | **Tabla 11** (`campaign_final/runs.csv`). `campaign/` (159 filas) es el intento previo interrumpido; no se usa. |
| N8b | `oe_n10_2026-10-14_n20` | no oficial, 60/60 | **Tabla 20**. El informe la llama N8b; el directorio se llama `oe_n10`. |
| N11 | `oe_n11_2026-10-14_3N` | no oficial, 179/180 `ok` | archivos y validación; Tablas 21–24 no recalculadas aquí |

## Cadena de evidencia
1. Locust genera carga contra el servidor; `adaptation_swarm.oe.http_campaign` (rama de este repositorio) escribe `runs.csv`, `plan.json`, `provenance.json`, `manifest.json` y registra los comandos y semillas.
2. `oe_n8_2026-10-13/scripts/*.py` (re-análisis independiente D2.7: pandas, scipy, statsmodels, no importan el código del enjambre) producen los CSV derivados.
3. `scripts/reproduce_results.py` ejecuta esos scripts sin modificarlos sobre una copia temporal y compara con el informe.

## Limitaciones de procedencia (leer antes de citar)
- **Los archivos no contienen una prueba externa de cuándo ni dónde se midieron.** La fecha documentada es la del nombre del directorio y de `provenance.json`; las fechas del sistema de archivos se perdieron al copiar.
- Los hashes (`EVIDENCE_MANIFEST.csv`, `SHA256SUMS`) prueban que un archivo es idéntico a una referencia; no que su contenido sea verdadero.
- Los registros por petición (`raw/*.csv`, unos 222 MB entre campañas, más 33 MB de la N9 abortada) no se publican. Sus hashes siguen en cada `manifest.json`. Quien quiera auditar el paso petición → `runs.csv` necesita esos archivos, que el autor conserva localmente.
- La verificación «independiente» D2.7 la realizó el mismo proyecto.
- Las campañas se ejecutaron en un único equipo (i7-12700K, 20 vCPU, 31,75 GiB según el informe) con el generador de carga en la misma máquina; el régimen del equipo cambió entre tramos de N11.
- **Estado del código durante las campañas.** `provenance.json` de N8, N8b, N9b y N11 registra `commit = 65e8c97` y `code.dirty = null` (la suciedad del árbol no se registró). Esas mismas provenance incluyen `design.start_margin_s = 20`, un campo que solo escribe el cambio de `http_campaign.py` que estaba sin confirmar; es decir, esas campañas se ejecutaron con ese cambio. Se confirma ahora en el commit `f4687e4` (`--start-margin`, diario de reanudación y `--resume`), con 11 pruebas que pasan. Git por sí solo no puede demostrar que fuera el mismo código en el momento de la ejecución; la evidencia es esa coincidencia de campos.
- Ninguna campaña es oficial. Publicarlas no las vuelve oficiales.
- No existen datos de usabilidad (SUS), de expertos ni de estudiantes: 0 evaluadores reales. Tampoco hay mediciones en hardware objetivo.
