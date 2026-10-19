"""OE4 — análisis de N11 (N = 10, 20, 30 en UNA campaña aleatorizada por bloques; 6 cargas x 10 réplicas; 180 corridas previstas).
Unidad = corrida HTTP. Log para P95/throughput/T_conv. Contrastes de Welch sobre log por carga con Holm; ANOVA tipo II con el tramo de ejecución como factor de ajuste.
DISEÑO / ADVERTENCIA: la campaña se ejecutó en dos tramos de la MISMA campaña (mismo --campaign-id, plan y semillas): tramo A = ejecuciones 1-17 (primer lanzamiento, detenido por baja memoria);
tramo B = ejecuciones 18-180 (reanudación con --resume tras reiniciar Docker Desktop). El tramo B es completo y balanceado en N (el plan aleatorizado reparte N de forma pareja);
el tramo A solo tiene 17 corridas. Entre tramos el rendimiento global cambia: se informa como cambio de régimen (causa no aislada: reinicio de Docker/WSL y carga del host) y NO se atribuye.
Uso (desde oe_n8_2026-10-13/): <python analisis> scripts/oe4_n11_analysis.py   Salida: oe4_n11/"""
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

OUT = Path('oe4_n11')
OUT.mkdir(exist_ok=True)
N11 = Path('../oe_n11_2026-10-14_3N/campaign/runs.csv')
RESUME_FROM = 18                                                                  # primera ejecución del tramo B (reanudación)
M = {'p95_latency_ms': 'P95 (ms)', 'throughput_http': 'Throughput (req/s)', 't_conv_ms_mean': 'T_conv HTTP medio (ms)'}

raw = pd.read_csv(N11)
raw['N'] = raw['run_id'].str.extract(r'N(\d+)-r')[0].astype(int)
raw['rep'] = raw['run_id'].str.extract(r'-r(\d+)$')[0].astype(int)
raw['tramo'] = np.where(raw['execution_index'] < RESUME_FROM, 'A', 'B')
raw['started'] = pd.to_datetime(raw['started_utc'])
valid = raw[raw['comparable'].astype(bool) & raw['p95_latency_ms'].notna() & raw['throughput_http'].notna()].copy()   # excluye la corrida 'no_requests' (estado `invalid` en el diario: sin métricas)
valid['load'] = valid['load'].astype(int)
integrity = dict(runs_total=int(len(raw)), runs_valid=int(len(valid)), runs_invalid=raw.loc[~raw['run_id'].isin(valid['run_id']), 'run_id'].tolist(),
                 errors=int(valid['error_count'].sum()), timeouts=int(valid['timeout_count'].sum()),
                 valid_per_tramo=valid.groupby('tramo').size().to_dict(), valid_per_N_tramo=valid.groupby(['tramo', 'N']).size().unstack().to_dict(),
                 tramo_A_ends=str(raw[raw.tramo == 'A']['started'].max()), tramo_B_starts=str(raw[raw.tramo == 'B']['started'].min()),
                 n_per_cell={int(k): v for k, v in valid.groupby('load').apply(lambda x: x.groupby('N').size().to_dict(), include_groups=False).items()})

desc = valid.groupby(['N', 'load'])[list(M)].agg(['mean', 'std', 'median', 'count']).round(4)
desc.columns = ['_'.join(c) for c in desc.columns]
desc.to_csv(OUT / 'oe4_n11_descriptivos.csv')
descB = valid[valid.tramo == 'B'].groupby(['N', 'load'])[list(M)].agg(['mean', 'std', 'count']).round(4)
descB.columns = ['_'.join(c) for c in descB.columns]
descB.to_csv(OUT / 'oe4_n11_descriptivos_tramoB.csv')


def welch(x, r):
    lx, lr = np.log(x), np.log(r)
    t = stats.ttest_ind(lx, lr, equal_var=False)
    diff = lx.mean() - lr.mean()
    va, vb = lx.var(ddof=1) / len(lx), lr.var(ddof=1) / len(lr)
    df = (va + vb) ** 2 / (va ** 2 / (len(lx) - 1) + vb ** 2 / (len(lr) - 1))
    tc = stats.t.ppf(0.975, df)
    se = math.sqrt(va + vb)
    sp = math.sqrt(((len(lx) - 1) * lx.var(ddof=1) + (len(lr) - 1) * lr.var(ddof=1)) / (len(lx) + len(lr) - 2))
    return dict(ratio=math.exp(diff), ci_low=math.exp(diff - tc * se), ci_high=math.exp(diff + tc * se), p=float(t.pvalue), hedges_g=float(diff / sp) if sp > 0 else float('nan'),
                mw_p=float(stats.mannwhitneyu(x, r).pvalue), mean_N=float(x.mean()), mean_ref=float(r.mean()), n=len(x), n_ref=len(r))


PAIRS = [(20, 10), (30, 10), (30, 20)]
rows = []
for scope, d in (('tramoB', valid[valid.tramo == 'B']), ('todo', valid)):
    for m in M:
        for load in sorted(d['load'].unique()):
            for n, nref in PAIRS:
                x, r = d[(d.N == n) & (d.load == load)][m].values, d[(d.N == nref) & (d.load == load)][m].values
                rows.append(dict(scope=scope, metric=m, load=int(load), contrast=f'N{n}_vs_N{nref}', **welch(x, r)))
c = pd.DataFrame(rows)
c['p_holm'] = c.groupby(['scope', 'metric'])['p'].transform(lambda s: multipletests(s.values, method='holm')[1])
c.to_csv(OUT / 'oe4_n11_contrastes.csv', index=False)

# modelos: log y ~ N * carga (+ tramo) ; sensibilidad con bloque de réplica
anova_rows, models = [], {}
for m in M:
    for label, f, d in (('tramoB', 'y ~ C(N) * C(load)', valid[valid.tramo == 'B']), ('todo_ajustado_tramo', 'y ~ C(N) * C(load) + C(tramo)', valid),
                        ('todo_bloque_rep', 'y ~ C(N) * C(load) + C(tramo) + C(rep)', valid)):
        dd = d.copy()
        dd['y'] = np.log(dd[m])
        fit = smf.ols(f, data=dd).fit()
        an = sm.stats.anova_lm(fit, typ=2)
        an['eta2_partial'] = an['sum_sq'] / (an['sum_sq'] + an.loc['Residual', 'sum_sq'])
        an['metric'], an['modelo'] = m, label
        anova_rows.append(an.reset_index().rename(columns={'index': 'term'}))
        models[f'{m}|{label}'] = dict(shapiro_p=float(stats.shapiro(fit.resid).pvalue), r2=float(fit.rsquared), n=int(len(dd)))
pd.concat(anova_rows).to_csv(OUT / 'oe4_n11_anova.csv', index=False)

# cambio de régimen entre tramos (razón B/A por N, ajustada por carga con modelo log-lineal) y deriva dentro del tramo B
reg = []
for m in M:
    for n in (10, 20, 30):
        d = valid[valid.N == n].copy()
        d['y'] = np.log(d[m])
        fit = smf.ols('y ~ C(load) + C(tramo)', data=d).fit()
        b, se = fit.params['C(tramo)[T.B]'], fit.bse['C(tramo)[T.B]']
        reg.append(dict(metric=m, N=n, ratio_B_over_A=math.exp(b), ci_low=math.exp(b - 2 * se), ci_high=math.exp(b + 2 * se), p=float(fit.pvalues['C(tramo)[T.B]']),
                        nA=int((d.tramo == 'A').sum()), nB=int((d.tramo == 'B').sum())))
pd.DataFrame(reg).to_csv(OUT / 'oe4_n11_cambio_regimen_A_B.csv', index=False)
drift = {}
for m in M:
    d = valid[valid.tramo == 'B'].copy()
    d['res'] = smf.ols(f'np.log({m}) ~ C(N) * C(load)', data=d).fit().resid
    s = stats.spearmanr(d['execution_index'], d['res'])
    drift[m] = dict(spearman_rho=float(s.statistic), p=float(s.pvalue))

# síntesis entre campañas: razón N10/N20 por carga en P95 y throughput
n8 = pd.read_csv('campaign/runs.csv')
n8b = pd.read_csv('../oe_n10_2026-10-14_n20/campaign/runs.csv')
syn = []
for m in ('p95_latency_ms', 'throughput_http'):
    for load in (1, 5, 10, 25, 50, 100):
        def gm(df, n, col=m):
            x = df[(df['swarm_N'].astype(int) == n) & (df['load'] == load) & df['comparable']][col] if 'swarm_N' in df else df[(df['N'] == n) & (df['load'] == load)][col]
            return float(np.exp(np.log(x).mean()))
        b = valid[valid.tramo == 'B']
        syn.append(dict(metric=m, load=load, N10_over_N20_cross_session_N8_vs_N8b=gm(n8, 10) / gm(n8b, 20), N10_over_N20_misma_campania_N11_tramoB=gm(b, 10) / gm(b, 20),
                        N30_over_N10_N8=gm(n8, 30) / gm(n8, 10), N30_over_N10_N11_tramoB=gm(b, 30) / gm(b, 10)))
pd.DataFrame(syn).to_csv(OUT / 'oe4_n11_sintesis_entre_campanias.csv', index=False)

json.dump(dict(integridad=integrity, modelos=models, deriva_tramoB=drift), open(OUT / 'oe4_n11.json', 'w'), indent=1, default=str)

fig, ax = plt.subplots(1, 3, figsize=(14, 4))
for k, m in enumerate(M):
    for n, col in ((10, '#2ca02c'), (20, '#1f77b4'), (30, '#d62728')):
        g = valid[(valid.N == n) & (valid.tramo == 'B')].groupby('load')[m].agg(['mean', 'std', 'count'])
        ci = stats.t.ppf(.975, g['count'] - 1) * g['std'] / np.sqrt(g['count'])
        ax[k].errorbar(g.index, g['mean'], yerr=ci, marker='o', capsize=3, color=col, label=f'N={n}')
    ax[k].set_xscale('log')
    ax[k].set_yscale('log')
    ax[k].set_xticks([1, 5, 10, 25, 50, 100])
    ax[k].set_xticklabels([1, 5, 10, 25, 50, 100])
    ax[k].set_xlabel('Usuarios concurrentes (carga cerrada)')
    ax[k].set_ylabel(M[m])
    ax[k].grid(alpha=.3)
    if m == 'p95_latency_ms':
        ax[k].axhline(2000, ls='--', color='gray')
    if m == 'throughput_http':
        ax[k].axhline(20, ls='--', color='gray')
    ax[k].legend(fontsize=8)
fig.suptitle('OE4 (N11): desempeño HTTP por carga y N, tramo B (ejecuciones 18-180) · media ± IC95 t · ~9-10 corridas por celda', fontsize=10)
fig.text(0.5, -0.03, 'Datos: oe_n11_2026-10-14_3N/campaign · experimental no oficial · una sola campaña aleatorizada en dos tramos de ejecución', ha='center', fontsize=7)
fig.tight_layout()
fig.savefig(OUT / 'oe4_n11_carga_N.png', dpi=150, bbox_inches='tight')

print(json.dumps(integrity, indent=1, default=str))
print(descB[['p95_latency_ms_mean', 'throughput_http_mean', 't_conv_ms_mean_mean']].to_string())
print(pd.concat(anova_rows)[['metric', 'modelo', 'term', 'F', 'PR(>F)', 'eta2_partial']].to_string())
print(c[c.scope == 'tramoB'][['metric', 'load', 'contrast', 'ratio', 'ci_low', 'ci_high', 'hedges_g', 'p_holm']].query("metric in ['p95_latency_ms','throughput_http']").to_string())
print(pd.DataFrame(reg).to_string())
print(json.dumps(drift, indent=1))
print(pd.DataFrame(syn).round(3).to_string())

# ¿A qué régimen de N11 se parece cada campaña previa? Razón (campaña previa)/(tramo de N11), por N, ajustada por carga (log-lineal). ~1 = mismo régimen.
anc = []
for name, df, n in (('N8', n8, 10), ('N8', n8, 30), ('N8b', n8b, 20)):
    p = df[(df['swarm_N'].astype(int) == n) & df['comparable'].astype(bool)][['load', 'p95_latency_ms', 'throughput_http']].assign(src=name)
    for tr in ('A', 'B'):
        q = valid[(valid.N == n) & (valid.tramo == tr)][['load', 'p95_latency_ms', 'throughput_http']].assign(src='N11')
        dd = pd.concat([p, q], ignore_index=True)
        for m in ('p95_latency_ms', 'throughput_http'):
            dd['y'] = np.log(dd[m])
            fit = smf.ols('y ~ C(load) + C(src)', data=dd).fit()
            k = [i for i in fit.params.index if i.startswith('C(src)')][0]
            b, se = fit.params[k], fit.bse[k]
            sign = 1 if k.endswith('[T.N11]') else -1                              # razón previa/N11
            anc.append(dict(campania_previa=name, N=n, tramo_N11=tr, metric=m, ratio_previa_sobre_N11=math.exp(-b if sign == 1 else b), n_previa=len(p), n_N11=len(q)))
anc = pd.DataFrame(anc)
anc.to_csv(OUT / 'oe4_n11_regimen_de_campanias_previas.csv', index=False)
print(anc.round(3).to_string())
