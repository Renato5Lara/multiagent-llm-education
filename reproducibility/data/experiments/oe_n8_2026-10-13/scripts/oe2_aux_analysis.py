"""OE2 — análisis de N9b: swarm vs decision_table (réplica de N2), y contrastes AUXILIARES swarm vs rules (ablación) y swarm vs bruteforce (óptimo exhaustivo).
Unidad = corrida HTTP (n = 10 por sistema y carga). Welch sobre log; razón de medias geométricas con IC95; g de Hedges; Mann-Whitney complementario; Holm m = 8 POR FAMILIA
(cada contraste auxiliar es su propia familia descriptiva; no entra en la familia primaria vs decision_table). Consistencia entre sesiones: N9b vs N2 por sistema (swarm y decision_table).
Uso (desde oe_n8_2026-10-13/): <python análisis> scripts/oe2_aux_analysis.py   Salida: oe2_aux/"""
import json
import math
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.multitest import multipletests

matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402

OUT = Path('oe2_aux')
OUT.mkdir(exist_ok=True)
d = pd.read_csv('../oe_n9b_2026-10-14/campaign_final/runs.csv')
n2 = pd.read_csv('../oe_n2_2026-10-05/campaign/runs.csv')
integ = dict(runs=int(len(d)), per_cell=d.groupby(['system', 'load']).size().unique().tolist(), comparable=int(d['comparable'].sum()), errors=int(d['errors'].sum()), timeouts=int(d['timeouts'].sum()),
             generator_saturated=int(d['generator_saturated'].sum()), servers_restarted=int(d['server_restarted_before_run'].sum()), status=d['status'].value_counts().to_dict())
M = ['p95_ms', 'throughput_rps']


def welch(a, b):
    la, lb = np.log(a), np.log(b)
    t = stats.ttest_ind(la, lb, equal_var=False)
    diff = la.mean() - lb.mean()
    va, vb = la.var(ddof=1) / len(la), lb.var(ddof=1) / len(lb)
    df = (va + vb) ** 2 / (va ** 2 / (len(la) - 1) + vb ** 2 / (len(lb) - 1))
    tc = stats.t.ppf(0.975, df)
    se = math.sqrt(va + vb)
    sp = math.sqrt(((len(la) - 1) * la.var(ddof=1) + (len(lb) - 1) * lb.var(ddof=1)) / (len(la) + len(lb) - 2))
    return dict(ratio=math.exp(diff), ci_low=math.exp(diff - tc * se), ci_high=math.exp(diff + tc * se), p=float(t.pvalue), hedges_g_log=float(diff / sp * (1 - 3 / (4 * (len(la) + len(lb)) - 9))),
                mw_p=float(stats.mannwhitneyu(a, b, alternative='two-sided').pvalue))


rows = []
for other, family in (('decision_table', 'primaria_replica'), ('rules', 'auxiliar_rules'), ('bruteforce', 'auxiliar_bruteforce')):
    for load in sorted(d['load'].unique()):
        for m in M:
            a = d[(d.system == 'swarm') & (d.load == load)][m].values
            b = d[(d.system == other) & (d.load == load)][m].values
            r = welch(a, b)
            r.update(familia=family, comparador=other, load=int(load), metric=m, mean_swarm=a.mean(), mean_other=b.mean(), n=len(a), n_other=len(b))
            rows.append(r)
c = pd.DataFrame(rows)
c['p_holm_m8'] = c.groupby('familia')['p'].transform(lambda s: multipletests(s.values, method='holm')[1])
c['mw_p_holm_m8'] = c.groupby('familia')['mw_p'].transform(lambda s: multipletests(s.values, method='holm')[1])
c.to_csv(OUT / 'oe2_aux_contrastes.csv', index=False)

desc = d.groupby(['system', 'load'])[['p95_ms', 'throughput_rps', 'mean_ms', 'decision_ms_mean']].agg(['mean', 'std', 'median']).round(4)
desc.columns = ['_'.join(x) for x in desc.columns]
desc.to_csv(OUT / 'oe2_aux_descriptivos.csv')

cons = []
for s in ('swarm', 'decision_table'):
    for load in sorted(d['load'].unique()):
        for m in M:
            a = d[(d.system == s) & (d.load == load)][m].values
            b = n2[(n2.system == s) & (n2.load == load)][m].values
            r = welch(a, b)
            cons.append(dict(sistema=s, load=int(load), metric=m, ratio_N9b_sobre_N2=r['ratio'], ci_low=r['ci_low'], ci_high=r['ci_high'], p=r['p']))
cons = pd.DataFrame(cons)
cons['p_holm'] = multipletests(cons['p'].values, method='holm')[1]
cons.to_csv(OUT / 'oe2_consistencia_N9b_vs_N2.csv', index=False)
json.dump(dict(integridad=integ, familias_holm_m=8, significativas_holm=c.groupby('familia').apply(lambda x: int((x['p_holm_m8'] < .05).sum())).to_dict(),
               consistencia_significativas_holm=int((cons['p_holm'] < .05).sum()), consistencia_n=int(len(cons))), open(OUT / 'oe2_aux.json', 'w'), indent=1, default=str)

fig, ax = plt.subplots(1, 2, figsize=(11, 4))
cols = {'swarm': '#1f77b4', 'decision_table': '#d62728', 'rules': '#2ca02c', 'bruteforce': '#9467bd'}
for k, m in enumerate(M):
    for s, col in cols.items():
        g = d[d.system == s].groupby('load')[m].agg(['mean', 'std', 'count'])
        ci = stats.t.ppf(.975, g['count'] - 1) * g['std'] / np.sqrt(g['count'])
        ax[k].errorbar(g.index, g['mean'], yerr=ci, marker='o', capsize=3, color=col, label=s)
    ax[k].set_xscale('log')
    ax[k].set_yscale('log')
    ax[k].set_xticks([1, 5, 10, 25])
    ax[k].set_xticklabels([1, 5, 10, 25])
    ax[k].set_xlabel('Usuarios concurrentes (carga cerrada)')
    ax[k].set_ylabel({'p95_ms': 'P95 latencia (ms)', 'throughput_rps': 'Throughput (req/s)'}[m])
    ax[k].grid(alpha=.3)
    ax[k].legend(fontsize=8)
fig.suptitle('OE2 (N9b): swarm, decision_table (comparador), rules y bruteforce (contrastes auxiliares); media ± IC95, 10 corridas por celda', fontsize=9)
fig.text(0.5, -0.03, 'Datos: oe_n9b_2026-10-14/campaign_final/runs.csv · experimental no oficial · rules y bruteforce NO son sistemas convencionales externos', ha='center', fontsize=7)
fig.tight_layout()
fig.savefig(OUT / 'oe2_aux_latencia_throughput.png', dpi=150, bbox_inches='tight')
print(json.dumps(integ, default=str))
print(desc[['p95_ms_mean', 'throughput_rps_mean', 'decision_ms_mean_mean']].to_string())
print(c[['familia', 'load', 'metric', 'ratio', 'ci_low', 'ci_high', 'hedges_g_log', 'p_holm_m8', 'mw_p_holm_m8']].to_string())
print(cons[['sistema', 'load', 'metric', 'ratio_N9b_sobre_N2', 'p_holm']].to_string())
