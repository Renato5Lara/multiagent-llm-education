"""OE2 — re-análisis INDEPENDIENTE de la campaña N2 (swarm vs decision_table) desde runs.csv. No importa adaptation_swarm.
Unidad estadística = corrida (n = 10 por celda). Escala log. Welch bilateral por carga y métrica (m = 8, Holm), Mann-Whitney complementario, razón de medias
geométricas con IC95 (Welch sobre log), g de Hedges sobre log, y sensibilidad pareada por run_index (las corridas comparten semilla por índice).
Uso (desde oe_n8_2026-10-13/): <python con pandas/scipy/statsmodels/matplotlib> scripts/oe2_reanalysis.py
Salida: oe2_reanalysis/{oe2_contrastes.csv,oe2_descriptivos.csv,oe2_reanalysis.json,oe2_latencia_throughput.png}"""
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

SRC = Path('../oe_n2_2026-10-05/campaign/runs.csv')
OUT = Path('oe2_reanalysis')
OUT.mkdir(exist_ok=True)
d = pd.read_csv(SRC)
assert d['comparable'].all(), 'hay corridas no comparables'
assert (d['errors'] == 0).all() and (d['timeouts'] == 0).all()
METRICS = {'p95_ms': 'P95 latencia (ms)', 'throughput_rps': 'Throughput (req/s)'}
loads = sorted(d['load'].unique())


def welch_log(a, b):
    la, lb = np.log(a), np.log(b)
    t = stats.ttest_ind(la, lb, equal_var=False)
    diff = la.mean() - lb.mean()
    va, vb = la.var(ddof=1) / len(la), lb.var(ddof=1) / len(lb)
    se = math.sqrt(va + vb)
    df = (va + vb) ** 2 / (va ** 2 / (len(la) - 1) + vb ** 2 / (len(lb) - 1))
    tc = stats.t.ppf(0.975, df)
    sp = math.sqrt(((len(la) - 1) * la.var(ddof=1) + (len(lb) - 1) * lb.var(ddof=1)) / (len(la) + len(lb) - 2))
    g = diff / sp * (1 - 3 / (4 * (len(la) + len(lb)) - 9))
    return dict(ratio=math.exp(diff), ci_low=math.exp(diff - tc * se), ci_high=math.exp(diff + tc * se), welch_t=float(t.statistic), df=float(df), p=float(t.pvalue), hedges_g_log=float(g))


rows, desc = [], []
for load in loads:
    for m in METRICS:
        a = d[(d.system == 'swarm') & (d.load == load)].sort_values('run_index')
        b = d[(d.system == 'decision_table') & (d.load == load)].sort_values('run_index')
        r = welch_log(a[m].values, b[m].values)
        mw = stats.mannwhitneyu(a[m].values, b[m].values, alternative='two-sided')
        r.update(load=int(load), metric=m, n_swarm=len(a), n_conv=len(b), mean_swarm=a[m].mean(), mean_conv=b[m].mean(), sd_swarm=a[m].std(ddof=1), sd_conv=b[m].std(ddof=1),
                 diff_abs=a[m].mean() - b[m].mean(), mann_whitney_p=float(mw.pvalue))
        if len(a) == len(b) and (a['run_index'].values == b['run_index'].values).all():
            ld = np.log(a[m].values) - np.log(b[m].values)
            r['paired_ratio'] = math.exp(ld.mean())
            r['paired_t_p'] = float(stats.ttest_1samp(ld, 0).pvalue)
        rows.append(r)
        for sysn, g in (('swarm', a), ('decision_table', b)):
            q = g[m].quantile([0.5, 0.25, 0.75])
            desc.append(dict(load=int(load), metric=m, system=sysn, n=len(g), mean=g[m].mean(), sd=g[m].std(ddof=1), median=q[0.5], q25=q[0.25], q75=q[0.75], min=g[m].min(), max=g[m].max()))
res = pd.DataFrame(rows)
res['p_holm_m8'] = multipletests(res['p'].values, method='holm')[1]
res['p_holm_m8_mannwhitney'] = multipletests(res['mann_whitney_p'].values, method='holm')[1]
res.to_csv(OUT / 'oe2_contrastes.csv', index=False)
pd.DataFrame(desc).to_csv(OUT / 'oe2_descriptivos.csv', index=False)

# TTFC / decision_ms por perfil: N2 incluye 'inprocess' (20 000 ciclos); aquí solo se resume lo que trae runs.csv (decision_ms_mean por corrida)
dm = d.groupby('system')['decision_ms_mean'].agg(['mean', 'median', 'std', 'count']).to_dict('index')
summary = dict(source=str(SRC), n_runs=int(len(d)), cells=int(d.groupby(['system', 'load']).ngroups), all_comparable=True, errors_total=int(d['errors'].sum()), timeouts_total=int(d['timeouts'].sum()),
               holm_m=8, significant_after_holm=int((res['p_holm_m8'] < 0.05).sum()), significant_mw_after_holm=int((res['p_holm_m8_mannwhitney'] < 0.05).sum()),
               min_possible_mw_p_n10_vs_10=float(2 / math.comb(20, 10)), decision_ms_mean_by_system=dm,
               nota_pareamiento='las corridas comparten semilla por run_index (diseño bloqueado); la sensibilidad pareada es descriptiva y no sustituye al contraste primario independiente')
json.dump(summary, open(OUT / 'oe2_reanalysis.json', 'w'), indent=1, default=float)

fig, ax = plt.subplots(1, 2, figsize=(10, 4))
for k, (m, lab) in enumerate(METRICS.items()):
    for sysn, c, mk in (('swarm', '#1f77b4', 'o'), ('decision_table', '#d62728', 's')):
        g = desc_df = pd.DataFrame(desc)
        g = g[(g.metric == m) & (g.system == sysn)]
        ci = stats.t.ppf(0.975, 9) * g['sd'] / np.sqrt(g['n'])
        ax[k].errorbar(g['load'], g['mean'], yerr=ci, color=c, marker=mk, capsize=3, label=f'{sysn} (n=10/carga)')
    ax[k].set_xscale('log')
    ax[k].set_yscale('log')
    ax[k].set_xlabel('Usuarios concurrentes (carga cerrada)')
    ax[k].set_ylabel(lab)
    ax[k].set_xticks(loads)
    ax[k].set_xticklabels(loads)
    ax[k].grid(alpha=.3)
    ax[k].legend(fontsize=8)
fig.suptitle('OE2 (N2): swarm vs decision_table — media por carga ± IC95 (t, gl=9); escala log', fontsize=10)
fig.text(0.5, -0.02, 'Datos: oe_n2_2026-10-05/campaign/runs.csv · unidad = corrida HTTP · ejecución experimental, no oficial (host único, generador en el mismo host)', ha='center', fontsize=7)
fig.tight_layout()
fig.savefig(OUT / 'oe2_latencia_throughput.png', dpi=150, bbox_inches='tight')
print(res[['load', 'metric', 'mean_swarm', 'mean_conv', 'ratio', 'ci_low', 'ci_high', 'hedges_g_log', 'p', 'p_holm_m8', 'mann_whitney_p', 'p_holm_m8_mannwhitney']].to_string())
print(json.dumps(summary, indent=1, default=float))
