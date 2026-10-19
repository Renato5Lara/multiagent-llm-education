"""OE4 — análisis de N8 (N = 10 y 30, 6 cargas, 10 corridas por celda) junto con N4 (N = 20) como diseño carga x N.
Unidad = corrida HTTP. Log para latencia/T_conv/throughput. ANOVA tipo II (carga, N, interacción), Kruskal-Wallis del efecto de la carga por N,
Spearman carga-P95, contrastes N10-vs-N20 y N30-vs-N20 por carga (Welch sobre log, Holm m = 12 por métrica), razones de medias geométricas con IC95.
ADVERTENCIA de diseño: N = 20 proviene de otra sesión (N4: 75 s totales, margen 5 s); N = 10 y 30 de N8 (90 s totales, margen 20 s). La ventana de medición es la misma
(10 s de calentamiento + >= 60 s), pero 'sesión' y 'N' (para N = 20) están confundidos.
Uso (desde oe_n8_2026-10-13/): <python analisis> scripts/oe4_nvar_analysis.py   Salida: oe4_nvar/"""
import json
import math
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy import stats
from statsmodels.stats.multitest import multipletests

matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402

OUT = Path('oe4_nvar')
OUT.mkdir(exist_ok=True)
a = pd.read_csv('campaign/runs.csv')
n20 = pd.read_csv('../oe_n10_2026-10-14_n20/campaign/runs.csv')                  # N = 20, misma configuración que N8 (--start-margin 20), sesión posterior
n4 = pd.read_csv('../oe_n4_2026-10-06/campaign/runs.csv')                        # N = 20 histórico (otra sesión/entorno): solo para estimar el efecto de sesión
a['session'], n20['session'], n4['session'] = 'N8', 'N8b', 'N4'
d = pd.concat([a, n20], ignore_index=True)
b = n4
status = d.groupby('session')[['comparable']].agg(lambda s: int(s.sum())).to_dict()
d = d[d['comparable']].copy()
d['N'] = d['swarm_N'].astype(int)
M = {'p95_ms': 'P95 (ms)', 'throughput_rps': 'Throughput (req/s)', 't_conv_ms_mean': 'T_conv HTTP medio (ms)', 'mean_ms': 'Latencia media (ms)'}
cells = d.groupby(['N', 'load']).size().unstack()
integrity = dict(runs_total=int(len(a) + len(n20)), runs_comparable=int(len(d)), errors=int(d['errors'].sum()), timeouts=int(d['timeouts'].sum()),
                 generator_saturated=int(d['generator_saturated'].sum()), n_per_cell=cells.to_dict())
desc = d.groupby(['N', 'load'])[list(M)].agg(['mean', 'std', 'median']).round(4)
desc.columns = ['_'.join(c) for c in desc.columns]
desc.to_csv(OUT / 'oe4_nvar_descriptivos.csv')
res = {}
anova_rows = []
for m in M:
    dd = d.copy()
    dd['y'] = np.log(dd[m])
    fit = smf.ols('y ~ C(N) * C(load)', data=dd).fit()
    an = sm.stats.anova_lm(fit, typ=2)
    ssr = an.loc['Residual', 'sum_sq']
    an['eta2_partial'] = an['sum_sq'] / (an['sum_sq'] + ssr)
    an['metric'] = m
    anova_rows.append(an.reset_index().rename(columns={'index': 'term'}))
    res[m] = dict(shapiro_p=float(stats.shapiro(fit.resid).pvalue), r2=float(fit.rsquared),
                  kruskal_load_by_N={int(n): float(stats.kruskal(*[g[m].values for _, g in x.groupby('load')]).pvalue) for n, x in d.groupby('N')},
                  spearman_load_vs_metric_by_N={int(n): float(stats.spearmanr(x['load'], x[m]).statistic) for n, x in d.groupby('N')})
pd.concat(anova_rows).to_csv(OUT / 'oe4_nvar_anova.csv', index=False)

rows = []
PAIRS = [(30, 10, 'primario_N8'), (20, 10, 'N8b_vs_N8'), (30, 20, 'N8_vs_N8b')]
for m in M:
    for load in sorted(d['load'].unique()):
        for n, nref, kind in PAIRS:
            ref = d[(d.N == nref) & (d.load == load)][m].values
            x = d[(d.N == n) & (d.load == load)][m].values
            lx, lr = np.log(x), np.log(ref)
            t = stats.ttest_ind(lx, lr, equal_var=False)
            diff = lx.mean() - lr.mean()
            va, vb = lx.var(ddof=1) / len(lx), lr.var(ddof=1) / len(lr)
            df = (va + vb) ** 2 / (va ** 2 / (len(lx) - 1) + vb ** 2 / (len(lr) - 1))
            tc = stats.t.ppf(0.975, df)
            se = math.sqrt(va + vb)
            rows.append(dict(metric=m, load=int(load), contrast=f'N{n}_vs_N{nref}', tipo=kind, ratio=math.exp(diff), ci_low=math.exp(diff - tc * se), ci_high=math.exp(diff + tc * se), p=float(t.pvalue),
                             mean_N=x.mean(), mean_ref=ref.mean(), n=len(x), n_ref=len(ref)))
c = pd.DataFrame(rows)
c['p_holm'] = c.groupby(['metric', 'tipo'])['p'].transform(lambda s: multipletests(s.values, method='holm')[1])
c.to_csv(OUT / 'oe4_nvar_contrastes.csv', index=False)
# efecto de sesión con N = 20 fijo: N4 (2026-10-06) vs N8b (2026-10-14), misma configuración nominal
ses = []
for m in M:
    for load in sorted(d['load'].unique()):
        x, r_ = n20[n20.load == load][m].values, n4[n4.load == load][m].values
        lx, lr = np.log(x), np.log(r_)
        t = stats.ttest_ind(lx, lr, equal_var=False)
        diff = lx.mean() - lr.mean()
        se = math.sqrt(lx.var(ddof=1) / len(lx) + lr.var(ddof=1) / len(lr))
        ses.append(dict(metric=m, load=int(load), ratio_N8b_over_N4=math.exp(diff), ci_low=math.exp(diff - 2.1 * se), ci_high=math.exp(diff + 2.1 * se), p=float(t.pvalue), mean_N8b=x.mean(), mean_N4=r_.mean()))
ses = pd.DataFrame(ses)
ses['p_holm'] = ses.groupby('metric')['p'].transform(lambda s_: multipletests(s_.values, method='holm')[1])
ses.to_csv(OUT / 'oe4_efecto_sesion_N20_N4_vs_N8b.csv', index=False)

# límites operativos observados por N: primera carga cuyo P95 medio supera 2 000 ms; throughput máximo
lim = {}
for n, x in d.groupby('N'):
    g = x.groupby('load')['p95_ms'].mean()
    lim[int(n)] = dict(p95_por_carga={int(k): float(v) for k, v in g.items()}, primera_carga_p95_mayor_2000ms=(int(g[g > 2000].index.min()) if (g > 2000).any() else None),
                       throughput_max_medio=float(x.groupby('load')['throughput_rps'].mean().max()), corridas_con_throughput_ge_20=int((x['throughput_rps'] >= 20).sum()),
                       corridas_con_p95_lt_2000=int((x['p95_ms'] < 2000).sum()), corridas=int(len(x)))
json.dump(dict(integridad=integrity, modelos=res, limites=lim), open(OUT / 'oe4_nvar.json', 'w'), indent=1, default=str)

fig, ax = plt.subplots(1, 3, figsize=(14, 4))
for k, m in enumerate(['p95_ms', 'throughput_rps', 't_conv_ms_mean']):
    for n, col in ((10, '#2ca02c'), (20, '#1f77b4'), (30, '#d62728')):
        g = d[d.N == n].groupby('load')[m].agg(['mean', 'std', 'count'])
        ci = stats.t.ppf(.975, g['count'] - 1) * g['std'] / np.sqrt(g['count'])
        ax[k].errorbar(g.index, g['mean'], yerr=ci, marker='o', capsize=3, color=col, label=f'N={n}' + (' (N8b)' if n == 20 else ''))
    ax[k].set_xscale('log')
    ax[k].set_yscale('log')
    ax[k].set_xticks([1, 5, 10, 25, 50, 100])
    ax[k].set_xticklabels([1, 5, 10, 25, 50, 100])
    ax[k].set_xlabel('Usuarios concurrentes (carga cerrada)')
    ax[k].set_ylabel(M[m])
    ax[k].grid(alpha=.3)
    if m == 'p95_ms':
        ax[k].axhline(2000, ls='--', color='gray')
        ax[k].text(1, 2100, 'RNF01: 2 000 ms', fontsize=7)
    if m == 'throughput_rps':
        ax[k].axhline(20, ls='--', color='gray')
        ax[k].text(1, 21, 'RNF04: 20 req/s', fontsize=7)
    ax[k].legend(fontsize=8)
fig.suptitle('OE4: desempeño HTTP por carga y tamaño del enjambre N (media ± IC95 t; 10 corridas por celda)', fontsize=10)
fig.text(0.5, -0.03, 'Datos: oe_n8_2026-10-13/campaign (N=10, 30) y oe_n10_2026-10-14_n20/campaign (N=20) · experimental no oficial · sesiones distintas, mismo protocolo', ha='center', fontsize=7)
fig.tight_layout()
fig.savefig(OUT / 'oe4_nvar_carga_N.png', dpi=150, bbox_inches='tight')
print(json.dumps(integrity, indent=1, default=str))
print(desc[['p95_ms_mean', 'throughput_rps_mean', 't_conv_ms_mean_mean']].to_string())
print(pd.concat(anova_rows)[['metric', 'term', 'F', 'PR(>F)', 'eta2_partial']].to_string())
print(c[['metric', 'load', 'contrast', 'ratio', 'ci_low', 'ci_high', 'p_holm']].query("metric in ['p95_ms','throughput_rps']").to_string())
print(json.dumps(lim, indent=1))
print(json.dumps(res, indent=1))
