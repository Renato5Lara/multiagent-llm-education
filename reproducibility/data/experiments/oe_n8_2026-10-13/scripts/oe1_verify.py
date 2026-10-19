"""OE1 — verificación independiente de los recuentos de N1 desde raw_observations.csv (oe3_run + oe4_run) y análisis de la asociación cumplimiento–desempeño.
No importa adaptation_swarm. Uso (desde oe_n8_2026-10-13/): ../../../.venv/Scripts/python.exe scripts/oe1_verify.py
Salida: oe1_verify/oe1_verify.json"""
import csv
import json
import math
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy import stats

BASE = Path('../oe_n1_2026-10-05')
rows = []
for sub in ('oe3_run', 'oe4_run'):
    for r in csv.DictReader(open(BASE / sub / 'raw_observations.csv', encoding='utf-8')):
        r['_run'] = sub
        rows.append(r)
n = len(rows)


def truthy(v):
    return str(v).strip().lower() in ('1', 'true', 't', 'yes')


overlap = [truthy(r['inflight_overlap']) for r in rows]
dispatch = ['sequential' if 'sequential' in r['condition'] else 'batch' for r in rows]
out = {'n_observaciones_total': n,
       'n_oe3_run': sum(r['_run'] == 'oe3_run' for r in rows), 'n_oe4_run': sum(r['_run'] == 'oe4_run' for r in rows),
       'ciclos_con_solape_total': int(sum(overlap)),
       'ciclos_batch': dispatch.count('batch'), 'ciclos_batch_con_solape': int(sum(o for o, d in zip(overlap, dispatch) if d == 'batch')),
       'ciclos_sequential': dispatch.count('sequential'), 'ciclos_sequential_con_solape': int(sum(o for o, d in zip(overlap, dispatch) if d == 'sequential')),
       'ciclos_batch_oe3': sum(1 for r, d in zip(rows, dispatch) if d == 'batch' and r['_run'] == 'oe3_run'),
       'ciclos_batch_oe4': sum(1 for r, d in zip(rows, dispatch) if d == 'batch' and r['_run'] == 'oe4_run')}
out['RF03_fraccion_total'] = out['ciclos_con_solape_total'] / n
out['RF03_fraccion_solo_batch'] = out['ciclos_batch_con_solape'] / out['ciclos_batch']
ok = [r for r in rows if r['status'] == 'ok' or r['status'] == 'completed']
out['status_valores'] = sorted({r['status'] for r in rows})
out['REL_C_completados'] = sum(1 for r in rows if r['status'] in ('ok', 'completed', 'complete')) / n

# Efecto del despacho sobre T_conv a nivel de ciclo (descriptivo)
def f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return math.nan


tc = defaultdict(list)
for r, d in zip(rows, dispatch):
    tc[d].append(f(r['t_conv_ms']))
out['t_conv_mediana_ms'] = {k: float(np.nanmedian(v)) for k, v in tc.items()}

# Asociación cumplimiento–desempeño por condición (n = condiciones; unidad = condición, NO ciclo)
rep = json.load(open(BASE / 'oe1_report' / 'oe1_report.json', encoding='utf-8'))
per = rep['relationship']['per_condition']
conds = sorted(per)
score = np.array([per[c]['compliance_score'] for c in conds])
res = {}
for key in ('t_conv_ms_median', 'latency_p95_ms', 'gap_vs_optimum', 'throughput_median_rps'):
    y = np.array([per[c][key] for c in conds], dtype=float)
    rho = stats.spearmanr(score, y)
    tau = stats.kendalltau(score, y)
    res[key] = {'spearman_rho': float(rho.statistic), 'spearman_p': float(rho.pvalue), 'kendall_tau_b': float(tau.statistic), 'kendall_p': float(tau.pvalue)}
out['asociacion_condiciones'] = {'n_condiciones': len(conds), 'valores_distintos_del_puntaje': sorted({round(float(s), 4) for s in score}), 'resultados': res}
# Confusión con la carga: ¿el puntaje se explica por la carga (usuarios)? (OE4 conditions codifican usuarios 'c<k>')
def users(c):
    for tok in c.split('|'):
        if tok.startswith('c') and tok[1:].isdigit():
            return int(tok[1:])
    return math.nan


u = np.array([users(c) for c in conds], dtype=float)
if not np.isnan(u).any():
    r = stats.spearmanr(u, score)
    out['asociacion_carga_vs_puntaje'] = {'spearman_rho': float(r.statistic), 'p': float(r.pvalue)}
Path('oe1_verify').mkdir(exist_ok=True)
json.dump(out, open('oe1_verify/oe1_verify.json', 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
print(json.dumps(out, indent=1, ensure_ascii=False))
