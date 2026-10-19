"""OE3 — re-análisis INDEPENDIENTE del factorial completo 2x2x2x2x3 (N3) desde runs_oe3.csv (240 corridas = 48 condiciones x 5 lotes). Unidad = lote/corrida
(cada fila resume 100 perfiles). Modelo: OLS con efectos principales + interacciones de 2 factores, ANOVA tipo II; tamaños de efecto: eta^2 parcial y omega^2 parcial.
Supuestos: Shapiro-Wilk de residuos, Levene entre las 48 celdas. Alternativa robusta: ANOVA sobre rangos. Holm dentro de cada respuesta (todos los términos).
Uso (desde oe_n8_2026-10-13/): <python analisis> scripts/oe3_reanalysis.py   Salida: oe3_reanalysis/"""
import json
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

OUT = Path('oe3_reanalysis')
OUT.mkdir(exist_ok=True)
d = pd.read_csv('../oe_n3_2026-10-06/runs_oe3.csv')
d = d.rename(columns={'f_heuristic_seed': 'heur', 'f_replicas': 'rep', 'f_dispatch': 'disp', 'f_broadcast_gbest': 'bcast', 'f_mechanism': 'mech'})
d['heur'] = d['heur'].astype(str)
d['bcast'] = d['bcast'].astype(str)
d['rep'] = d['rep'].astype(str)
d['cell'] = d['condition']
assert len(d) == 240 and d['cell'].nunique() == 48 and (d.groupby('cell').size() == 5).all(), 'diseño no balanceado'
RESP = {'t_conv_ms': True, 'k_stop': False, 'gap_vs_optimum': False, 'n_messages': False, 'F': False}      # True => log
FACT = ['heur', 'rep', 'disp', 'bcast', 'mech']
terms = ' + '.join(f'C({f})' for f in FACT) + ' + ' + ' + '.join(f'C({a}):C({b})' for i, a in enumerate(FACT) for b in FACT[i + 1:])
summary, rows = {}, []
for y, uselog in RESP.items():
    dd = d.copy()
    dd['y'] = np.log(dd[y]) if uselog else dd[y]
    m = smf.ols(f'y ~ {terms}', data=dd).fit()
    an = sm.stats.anova_lm(m, typ=2)
    ssr = an.loc['Residual', 'sum_sq']
    dfr = an.loc['Residual', 'df']
    mse = ssr / dfr
    sst = an['sum_sq'].sum()
    an = an.drop('Residual')
    an['eta2_partial'] = an['sum_sq'] / (an['sum_sq'] + ssr)
    an['omega2_partial'] = (an['sum_sq'] - an['df'] * mse) / (an['sum_sq'] + (len(dd) - an['df']) * mse)       # aproximación parcial
    an['p_holm'] = multipletests(an['PR(>F)'].fillna(1).values, method='holm')[1]
    # robusto: ANOVA sobre rangos
    dr = dd.copy()
    dr['y'] = stats.rankdata(dd['y'])
    ar = sm.stats.anova_lm(smf.ols(f'y ~ {terms}', data=dr).fit(), typ=2).drop('Residual')
    an['p_rank_anova'] = ar['PR(>F)']
    an['p_rank_holm'] = multipletests(ar['PR(>F)'].fillna(1).values, method='holm')[1]
    an['response'] = y
    an['log_scale'] = uselog
    rows.append(an.reset_index().rename(columns={'index': 'term'}))
    res = m.resid
    sw = stats.shapiro(res)
    lev = stats.levene(*[g['y'].values for _, g in dd.groupby('cell')])
    summary[y] = dict(log_scale=uselog, residual_df=int(dfr), r2=float(m.rsquared), shapiro_W=float(sw.statistic), shapiro_p=float(sw.pvalue), levene_p=float(lev.pvalue),
                      skew=float(stats.skew(res)), kurtosis_excess=float(stats.kurtosis(res)))
out = pd.concat(rows, ignore_index=True)
out.to_csv(OUT / 'oe3_anova.csv', index=False)

# efectos marginales (medias y diferencias en escala original) por factor y respuesta
marg = []
for y in RESP:
    for f in FACT:
        g = d.groupby(f)[y].agg(['mean', 'std', 'count']).reset_index().rename(columns={f: 'level'})
        g['response'], g['factor'] = y, f
        marg.append(g)
pd.concat(marg).to_csv(OUT / 'oe3_marginales.csv', index=False)
cellmeans = d.groupby('cell')[list(RESP)].mean()
cellmeans.to_csv(OUT / 'oe3_medias_por_condicion.csv')
summary['_design'] = dict(runs=len(d), cells=int(d['cell'].nunique()), reps_per_cell=5, residual_df_expected=240 - 1 - (1 + 1 + 1 + 1 + 2) - (1 + 1 + 1 + 1 + 1 + 1 + 1 + 1 + 1 + 1)
                          - 0, nota='con 3 niveles de mecanismo los términos con mech tienen 2 gl')
json.dump(summary, open(OUT / 'oe3_reanalysis.json', 'w'), indent=1)

main = out[out['term'].str.count(':') == 0]
print(main[['response', 'term', 'F', 'PR(>F)', 'p_holm', 'p_rank_holm', 'eta2_partial']].to_string())
print('Interacciones significativas (Holm<.05) en T_conv:')
print(out[(out.response == 't_conv_ms') & (out.term.str.contains(':')) & (out.p_holm < .05)][['term', 'F', 'p_holm', 'eta2_partial']].to_string())
print(json.dumps({k: v for k, v in summary.items() if not k.startswith('_')}, indent=1))

fig, axes = plt.subplots(1, 2, figsize=(11, 4))
for ax, y, lab in ((axes[0], 't_conv_ms', 'T_conv (ms)'), (axes[1], 'gap_vs_optimum', 'Brecha frente al óptimo')):
    base = d.groupby('disp')[y]
    xs, ms, es, labels = [], [], [], []
    k = 0
    for f in FACT:
        for lv, g in d.groupby(f)[y]:
            ms.append(g.mean())
            es.append(stats.t.ppf(.975, len(g) - 1) * g.std() / np.sqrt(len(g)))
            labels.append(f'{f}={lv}')
            xs.append(k)
            k += 1
        k += 0.6
    ax.errorbar(xs, ms, yerr=es, fmt='o', capsize=3)
    ax.set_xticks(xs)
    ax.set_xticklabels(labels, rotation=75, ha='right', fontsize=7)
    ax.set_ylabel(lab)
    ax.grid(alpha=.3)
fig.suptitle('OE3 (N3): efectos marginales por nivel (media ± IC95 sobre 120 o 80 corridas por nivel; las corridas se reutilizan entre factores)', fontsize=8)
fig.text(0.5, -0.03, 'Datos: oe_n3_2026-10-06/runs_oe3.csv · 240 corridas (48 condiciones x 5 lotes) · 1 usuario, N=20 · experimental no oficial', ha='center', fontsize=7)
fig.tight_layout()
fig.savefig(OUT / 'oe3_efectos_marginales.png', dpi=150, bbox_inches='tight')
