"""Recalcula y explica los conteos de 'cifras' (auditoria/CONTEO_CIFRAS.md y .csv). Compara con el informe anterior (commit 21c7380: «861 cifras, 8 no reproducibles»).
Distingue: comprobaciones (cada valor comparado: razón, IC inferior, IC superior y p cuentan por separado), celdas de tabla cubiertas, valores publicados únicos y celdas numéricas totales."""
import json
import re
import subprocess
from collections import Counter, defaultdict

import pandas as pd

from repro_lib import META, ROOT

rep = json.loads((ROOT / "outputs" / "verification_report.json").read_text(encoding="utf-8"))
try:
    old = json.loads(subprocess.run(["git", "show", "21c7380:reproducibility/outputs/verification_report.json"], capture_output=True, text=True, cwd=ROOT, encoding="utf-8").stdout)
except Exception:  # noqa: BLE001
    old = None
tablas = json.loads((META / "informe_D2.9.7_tablas.json").read_text(encoding="utf-8"))["tables"]
T = {int(re.match(r"Tabla (\d+)\.", t["caption_prev"]).group(1)): t["rows"] for t in tablas if re.match(r"Tabla (\d+)\.", t["caption_prev"])}
num_cells = {n: sum(1 for i, r in enumerate(rows) if i > 0 for c in r if re.search(r"\d", c)) for n, rows in T.items()}
por_tabla = defaultdict(lambda: Counter())
celdas = defaultdict(set)
unicos = defaultdict(set)
for c in rep["comprobaciones"]:
    m = re.match(r"Tabla (\d+)$", c["tabla"])
    if not m:
        continue
    n = int(m.group(1))
    por_tabla[n][c["estado_cifra"]] += 1
    if c.get("celda_fila") is not None:
        celdas[n].add((c["celda_fila"], c["celda_col"]))
    if c.get("publicado") not in (None, ""):
        unicos[n].add(str(c["publicado"]))
rows = []
for n in sorted(T):
    cnt = por_tabla.get(n, Counter())
    rows.append({"tabla": n, "celdas_numericas": num_cells[n], "celdas_cubiertas": len(celdas.get(n, ())), "comprobaciones": sum(cnt.values()),
                 "verificadas_desde_datos": cnt["VERIFICADO_DESDE_DATOS"], "verificadas_desde_derivado": cnt["VERIFICADO_DESDE_DERIVADO"], "discrepantes": cnt["DISCREPANCIA"],
                 "no_reproducibles": cnt["NO_REPRODUCIBLE"], "valores_publicados_unicos": len(unicos.get(n, ()))})
df = pd.DataFrame(rows)
df.to_csv(ROOT / "auditoria" / "CONTEO_CIFRAS.csv", index=False, encoding="utf-8")
tot = {k: int(df[k].sum()) for k in df.columns if k != "tabla"}
cnt_new = Counter(c["estado_cifra"] for c in rep["comprobaciones"])
ids_old = {c["id"] for c in old["comprobaciones"]} if old else set()
ids_new = {c["id"] for c in rep["comprobaciones"]}
old_ver = Counter(c["estado_cifra"] for c in old["comprobaciones"]) if old else None
md = f"""# Conteo de cifras: qué significa «861» y cuánto vale ahora

**Definición.** Una *comprobación* (lo que antes se llamó «cifra») es **un valor numérico comparado** con su recálculo: en una celda «5,05 (4,57 a 5,58)» la razón, el límite inferior y el superior cuentan por separado (3 comprobaciones en 1 celda). Por tanto **861 no eran 861 celdas, ni 861 valores únicos**: eran 861 comprobaciones sobre 20 tablas.

**Reproducción del 861 anterior.** El informe del commit `21c7380` contiene {len(old['comprobaciones']) if old else '?'} comprobaciones, de las cuales {old_ver.get('VERIFICADO_DESDE_DATOS', '?') if old else '?'} `VERIFICADO_DESDE_DATOS`, {old_ver.get('NO_REPRODUCIBLE', '?') if old else '?'} `NO_REPRODUCIBLE` y {old_ver.get('DISCREPANCIA', 0) if old else '?'} discrepantes. El cálculo es reproducible con `git show 21c7380:reproducibility/outputs/verification_report.json`. Todas las comprobaciones antiguas siguen presentes: {len(ids_old & ids_new)} de {len(ids_old)} (faltan {len(ids_old - ids_new)}: {sorted(ids_old - ids_new)[:5]}).

## Conteo actual (esta rama)
| | |
|---|---|
| Comprobaciones totales | {len(rep['comprobaciones'])} |
| `VERIFICADO_DESDE_DATOS` | {cnt_new['VERIFICADO_DESDE_DATOS']} |
| `VERIFICADO_DESDE_DERIVADO` | {cnt_new['VERIFICADO_DESDE_DERIVADO']} |
| `DISCREPANCIA` | {cnt_new['DISCREPANCIA']} |
| `NO_REPRODUCIBLE` (elementos, no celdas: algunos agrupan varias tablas) | {cnt_new['NO_REPRODUCIBLE']} |
| Celdas numéricas del informe (excluida la fila de encabezados) | {tot['celdas_numericas']} |
| Celdas cubiertas por al menos una comprobación | {tot['celdas_cubiertas']} |

Las comprobaciones **no** deben dividirse por tablas sin cuidado: una celda numérica puede tener varias y algunas celdas son etiquetas de condición (carga, N) que no se calculan. El inventario por celda y por afirmación en prosa está en `CONCILIACION_TESIS_DATOS.csv`.

## Las «8 cifras no reproducibles»
No eran 8 cifras: son **8 elementos** del informe anterior, y varios agrupan tablas enteras. Estado actual de cada uno (ver `CONCILIACION_TESIS_DATOS.csv`, estado `NO_REPRODUCIBLE`/`PENDIENTE_DE_EVIDENCIA`):
{chr(10).join('- ' + c['id'] + ': ' + c.get('motivo', '')[:200] for c in rep['comprobaciones'] if c['estado_cifra'] == 'NO_REPRODUCIBLE')}

## Por tabla
{df.to_markdown(index=False) if hasattr(df, 'to_markdown') else df.to_string(index=False)}
"""
(ROOT / "auditoria" / "CONTEO_CIFRAS.md").write_text(md, encoding="utf-8")
print(tot, dict(cnt_new))
print("antiguas:", len(ids_old), "presentes:", len(ids_old & ids_new))
