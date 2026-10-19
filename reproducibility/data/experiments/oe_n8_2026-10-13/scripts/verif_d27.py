# -*- coding: utf-8 -*-
"""D2.7 — verificación INDEPENDIENTE de N11 (OE4), N9b (OE2), N8b/N8/N4 y umbrales RNF01/RNF04. No importa adaptation_swarm ni scripts/oe4_n11_analysis.py.
Unidad = corrida; log para latencia/throughput/T_conv; Welch; Holm (por métrica sobre 18 contrastes = 3 comparaciones de N x 6 cargas).
Uso (desde backend/experiments/): <python análisis> <ruta>/verif_d27.py   Salida: oe_n8_2026-10-13/d27_verificacion/"""
import json
import math
import os

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.multitest import multipletests
import statsmodels.formula.api as smf
import statsmodels.api as sm

EXP = os.getcwd()
OUT = os.path.join(EXP, 'oe_n8_2026-10-13', 'd27_verificacion')
os.makedirs(OUT, exist_ok=True)
RES = {}


def load(p):
    r = pd.read_csv(os.path.join(EXP, p))
    return r


# ---------------------------------------------------------------- N11: integridad
n11 = load('oe_n11_2026-10-14_3N/campaign/runs.csv')
jr = [json.loads(l) for l in open(os.path.join(EXP, 'oe_n11_2026-10-14_3N/campaign.journal/runs.journal.jsonl'), encoding='utf-8') if l.strip()]
last = {}
for e in jr:
    rid = e.get('run_id') or e.get('record', {}).get('run_id')
    last[rid] = e
states = pd.Series([e.get('state') or e.get('status') for e in last.values()]).value_counts().to_dict()
RES['journal'] = dict(entradas=len(jr), run_ids_unicos=len(last), estados_finales=states, keys_ejemplo=list(jr[0].keys()))
n11['tramo'] = np.where(n11['execution_index'] <= 17, 'A', 'B')
n11['N'] = n11['swarm_N'].astype(int)
n11['ok'] = (n11['status'] == 'ok') & n11['p95_latency_ms'].notna() & n11['throughput_http'].notna()
v = n11[n11['ok']].copy()
RES['n11_integridad'] = dict(filas=len(n11), run_id_unicos=int(n11.run_id.nunique()), validas=int(len(v)), invalidas=n11.loc[~n11.ok, 'run_id'].tolist(),
                             errores=int(v.error_count.sum()), timeouts=int(v.timeout_count.sum()), generador_saturado=int(v.generator_saturated.astype(bool).sum()),
                             validas_por_tramo=v.groupby('tramo').size().to_dict(),
                             validas_por_N_tramo={f'{k[0]}|N{k[1]}': int(c) for k, c in v.groupby(['tramo', 'N']).size().items()},
                             ejecucion_u50_N30_r00=n11.loc[n11.run_id.str.contains(r'u50\|N30-r00'), ['execution_index', 'status', 'throughput_http']].to_dict('records'))
cell = v.groupby(['tramo', 'N', 'load']).size().unstack('tramo')
RES['n11_n_por_celda_B'] = {f'N{n}|u{l}': int(c) for (n, l), c in v[v.tramo == 'B'].groupby(['N', 'load']).size().items()}

# ---------------------------------------------------------------- N11: descriptivos tramo B
def desc(df, label):
    g = df.groupby(['N', 'load']).agg(n=('run_id', 'size'), p95=('p95_latency_ms', 'mean'), thr=('throughput_http', 'mean'), tconv=('t_conv_ms_mean', 'mean'),
                                      p95_sd=('p95_latency_ms', 'std'), thr_sd=('throughput_http', 'std')).reset_index()
    g.insert(0, 'ambito', label)
    return g


dB = desc(v[v.tramo == 'B'], 'N11_tramoB')
dA = desc(v[v.tramo == 'A'], 'N11_tramoA')
dAll = desc(v, 'N11_todo')
pd.concat([dB, dA, dAll]).to_csv(os.path.join(OUT, 'n11_descriptivos_independientes.csv'), index=False)

# ---------------------------------------------------------------- N11: contrastes
def contrasts(df, metric, label):
    rows = []
    for (a, b) in ((20, 10), (30, 10), (30, 20)):
        for ld in sorted(df['load'].unique()):
            x = np.log(df[(df.N == a) & (df['load'] == ld)][metric].dropna())
            y = np.log(df[(df.N == b) & (df['load'] == ld)][metric].dropna())
            if len(x) < 3 or len(y) < 3:
                continue
            t = stats.ttest_ind(x, y, equal_var=False)
            d = x.mean() - y.mean()
            se = math.sqrt(x.var(ddof=1) / len(x) + y.var(ddof=1) / len(y))
            dfw = se ** 4 / ((x.var(ddof=1) / len(x)) ** 2 / (len(x) - 1) + (y.var(ddof=1) / len(y)) ** 2 / (len(y) - 1))
            q = stats.t.ppf(0.975, dfw)
            sp = math.sqrt(((len(x) - 1) * x.var(ddof=1) + (len(y) - 1) * y.var(ddof=1)) / (len(x) + len(y) - 2))
            g = d / sp * (1 - 3 / (4 * (len(x) + len(y)) - 9))
            rows.append(dict(ambito=label, metric=metric, contraste=f'N{a}_vs_N{b}', load=int(ld), n_a=len(x), n_b=len(y), ratio=math.exp(d), ci_low=math.exp(d - q * se), ci_high=math.exp(d + q * se),
                             p=t.pvalue, hedges_g_log=g))
    r = pd.DataFrame(rows)
    r['p_holm'] = multipletests(r['p'], method='holm')[1]
    return r


cB = pd.concat([contrasts(v[v.tramo == 'B'], m, 'tramoB') for m in ('p95_latency_ms', 'throughput_http', 't_conv_ms_mean')])
cB.to_csv(os.path.join(OUT, 'n11_contrastes_tramoB_independientes.csv'), index=False)
summ = {}
for (c, m), g in cB.groupby(['contraste', 'metric']):
    summ[f'{c}|{m}'] = dict(ratio_min=round(g.ratio.min(), 3), ratio_max=round(g.ratio.max(), 3), signif_holm=int((g.p_holm < 0.05).sum()), de=len(g),
                            g_min=round(g.hedges_g_log.min(), 2), g_max=round(g.hedges_g_log.max(), 2))
RES['n11_contrastes_B_resumen'] = summ
c10 = cB[(cB.contraste == 'N20_vs_N10') & (cB['load'] == 10)]
RES['n11_N20vN10_u10'] = c10[['metric', 'ratio', 'ci_low', 'ci_high', 'p_holm']].to_dict('records')

# ---------------------------------------------------------------- N11: cambio de régimen A -> B (ajustado por carga)
reg = {}
for m, nm in (('p95_latency_ms', 'p95'), ('throughput_http', 'thr'), ('t_conv_ms_mean', 'tconv')):
    dd = v.copy(); dd['y'] = np.log(dd[m])
    mod = smf.ols('y ~ C(load) + C(N) + C(tramo)', data=dd).fit()
    reg[nm] = dict(razon_B_sobre_A=float(math.exp(mod.params['C(tramo)[T.B]'])), p=float(mod.pvalues['C(tramo)[T.B]']))
    for n in (10, 20, 30):
        s = dd[dd.N == n]
        mm = smf.ols('y ~ C(load) + C(tramo)', data=s).fit()
        reg[nm][f'N{n}'] = float(math.exp(mm.params['C(tramo)[T.B]']))
RES['n11_regimen_B_sobre_A'] = reg
RES['n11_tramoA_n_por_N'] = v[v.tramo == 'A'].groupby('N').size().to_dict()

prev = []
for lab, src, nn in (('N8 (N=10)', None, 10), ('N8 (N=30)', None, 30), ('N8b (N=20)', None, 20)):
    pass
n8_ = load('oe_n8_2026-10-13/campaign/runs.csv'); n8_ = n8_[(n8_.status == 'ok') & n8_.p95_latency_ms.notna()].copy(); n8_['N'] = n8_.swarm_N.astype(int)
n8b_ = load('oe_n10_2026-10-14_n20/campaign/runs.csv'); n8b_ = n8b_[(n8b_.status == 'ok') & n8b_.p95_latency_ms.notna()].copy(); n8b_['N'] = n8b_.swarm_N.astype(int)
for lab, src, nn in (('N8 N=10', n8_, 10), ('N8 N=30', n8_, 30), ('N8b N=20', n8b_, 20)):
    a = src[src.N == nn].copy(); a['grp'] = 'prev'
    for tr in ('A', 'B'):
        b = v[(v.N == nn) & (v.tramo == tr)].copy(); b['grp'] = 'n11'
        both = pd.concat([a[['load', 'p95_latency_ms', 'throughput_http', 'grp']], b[['load', 'p95_latency_ms', 'throughput_http', 'grp']]])
        row = dict(campania=lab, contra=f'N11 tramo {tr}', n_prev=len(a), n_n11=len(b))
        for m, nm in (('p95_latency_ms', 'p95'), ('throughput_http', 'thr')):
            both['y'] = np.log(both[m]); mod = smf.ols('y ~ C(load) + C(grp)', data=both).fit()
            row[f'razon_{nm}_prev_sobre_n11'] = float(math.exp(mod.params['C(grp)[T.prev]']))
        prev.append(row)
PV = pd.DataFrame(prev); PV.to_csv(os.path.join(OUT, 'regimen_campanias_previas_independiente.csv'), index=False)
RES['regimen_campanias_previas'] = PV.round(3).to_dict('records')

# ---------------------------------------------------------------- umbrales RNF01 / RNF04
def thresholds(df, label):
    out = []
    for (n, ld), g in df.groupby(['N', 'load']):
        out.append(dict(ambito=label, N=int(n), load=int(ld), n=len(g), p95_media=g.p95_latency_ms.mean(), n_p95_lt_2000=int((g.p95_latency_ms < 2000).sum()),
                        thr_media=g.throughput_http.mean(), n_thr_ge_20=int((g.throughput_http >= 20).sum()), thr_max=g.throughput_http.max(), errores=int(g.error_count.sum())))
    return pd.DataFrame(out)


camps = {'N4': 'oe_n4_2026-10-06/campaign/runs.csv', 'N8': 'oe_n8_2026-10-13/campaign/runs.csv', 'N8b': 'oe_n10_2026-10-14_n20/campaign/runs.csv'}
th = [thresholds(v[v.tramo == 'B'], 'N11_B'), thresholds(v[v.tramo == 'A'], 'N11_A')]
allv = {}
for k, p in camps.items():
    d = load(p); d = d[(d.status == 'ok') & d.p95_latency_ms.notna()].copy(); d['N'] = d.swarm_N.astype(int); allv[k] = d
    th.append(thresholds(d, k))
T = pd.concat(th); T.to_csv(os.path.join(OUT, 'umbrales_RNF01_RNF04_por_celda.csv'), index=False)
tot = {}
for lab, d in [('N11_B', v[v.tramo == 'B']), ('N11_A', v[v.tramo == 'A'])] + [(k, x) for k, x in allv.items()]:
    ge = d[d.throughput_http >= 20]
    tot[lab] = dict(corridas=len(d), thr_ge_20=len(ge), thr_ge_20_por_N=ge.groupby('N').size().to_dict(), thr_ge_20_por_carga=ge.groupby('load').size().to_dict(),
                    thr_max=round(d.throughput_http.max(), 2), errores_en_ge20=int(ge.error_count.sum()), p95_lt_2000=int((d.p95_latency_ms < 2000).sum()))
RES['umbrales'] = tot
umb = []
for lab, d in [('N4', allv['N4']), ('N8', allv['N8']), ('N8b', allv['N8b']), ('N11 tramo A', v[v.tramo == 'A']), ('N11 tramo B', v[v.tramo == 'B'])]:
    for n, g in d.groupby('N'):
        cells = g.groupby('load').agg(p95=('p95_latency_ms', 'mean'), thr=('throughput_http', 'mean'))
        umb.append(dict(ambito=lab, N=int(n), corridas=len(g), thr_ge_20=int((g.throughput_http >= 20).sum()), thr_max=round(g.throughput_http.max(), 2), p95_lt_2000=int((g.p95_latency_ms < 2000).sum()),
                        cargas_media_p95_lt_2000=','.join(str(int(i)) for i in cells.index[cells.p95 < 2000]), cargas_media_thr_ge_20=','.join(str(int(i)) for i in cells.index[cells.thr >= 20]),
                        errores=int(g.error_count.sum())))
pd.DataFrame(umb).to_csv(os.path.join(OUT, 'umbrales_resumen_por_campania_N.csv'), index=False)
sub = v[(v.tramo == 'B') & (v.N == 10)]
RES['N10_B_por_carga_ge20'] = {int(l): [int((g.throughput_http >= 20).sum()), len(g), round(g.throughput_http.mean(), 2)] for l, g in sub.groupby('load')}
RES['N10_B_p95_lt2000_u25'] = [int((sub[sub['load'] == 25].p95_latency_ms < 2000).sum()), int((sub['load'] == 25).sum()), round(sub[sub['load'] == 25].p95_latency_ms.mean(), 1)]
RES['thr_ge20_orden_ejecucion_N10_B'] = sub[sub.throughput_http >= 20].sort_values('execution_index')[['execution_index', 'load', 'throughput_http']].round(2).values.tolist()

# ---------------------------------------------------------------- N8b vs N4 (N = 20) y N8 descriptivos
n4 = allv['N4']; n8b = allv['N8b']; n8 = allv['N8']
ref = []
for ld in sorted(n4['load'].unique()):
    for m in ('p95_latency_ms', 'throughput_http'):
        x = np.log(n8b[n8b['load'] == ld][m]); y = np.log(n4[n4['load'] == ld][m])
        t = stats.ttest_ind(x, y, equal_var=False)
        ref.append(dict(load=int(ld), metric=m, ratio_N8b_sobre_N4=math.exp(x.mean() - y.mean()), p=t.pvalue))
R = pd.DataFrame(ref); R['p_holm'] = multipletests(R.p, method='holm')[1]
R.to_csv(os.path.join(OUT, 'n8b_vs_n4_independiente.csv'), index=False)
RES['n8b_vs_n4'] = dict(p95=[round(R[R.metric == 'p95_latency_ms'].ratio_N8b_sobre_N4.min(), 3), round(R[R.metric == 'p95_latency_ms'].ratio_N8b_sobre_N4.max(), 3)],
                        thr=[round(R[R.metric == 'throughput_http'].ratio_N8b_sobre_N4.min(), 3), round(R[R.metric == 'throughput_http'].ratio_N8b_sobre_N4.max(), 3)], min_p_holm=float(R.p_holm.min()))
d8 = pd.concat([desc(n8[n8.N == 10], 'N8'), desc(n8[n8.N == 30], 'N8'), desc(n8b, 'N8b')])
d8.to_csv(os.path.join(OUT, 'n8_n8b_descriptivos_independientes.csv'), index=False)

# ---------------------------------------------------------------- N9b (OE2) y N2
n9 = load('oe_n9b_2026-10-14/campaign_final/runs.csv'); n9 = n9[(n9.status == 'ok') & n9.p95_latency_ms.notna()]
n2 = load('oe_n2_2026-10-05/campaign/runs.csv'); n2 = n2[(n2.status == 'ok') & n2.p95_latency_ms.notna()]
RES['n9b'] = dict(filas=len(load('oe_n9b_2026-10-14/campaign_final/runs.csv')), validas=len(n9), por_sistema=n9.groupby('system').size().to_dict(),
                  errores=int(n9.error_count.sum()), timeouts=int(n9.timeout_count.sum()), run_id_unicos=int(n9.run_id.nunique()))
rows = []
for sysb in ('decision_table', 'rules', 'bruteforce'):
    for ld in (1, 5, 10, 25):
        for m in ('p95_latency_ms', 'throughput_http'):
            x = np.log(n9[(n9.system == 'swarm') & (n9['load'] == ld)][m]); y = np.log(n9[(n9.system == sysb) & (n9['load'] == ld)][m])
            t = stats.ttest_ind(x, y, equal_var=False); d = x.mean() - y.mean()
            se = math.sqrt(x.var(ddof=1) / len(x) + y.var(ddof=1) / len(y))
            dfw = se ** 4 / ((x.var(ddof=1) / len(x)) ** 2 / (len(x) - 1) + (y.var(ddof=1) / len(y)) ** 2 / (len(y) - 1))
            q = stats.t.ppf(0.975, dfw)
            rows.append(dict(sistema=sysb, load=ld, metric=m, n=f'{len(x)}/{len(y)}', ratio=math.exp(d), ci_low=math.exp(d - q * se), ci_high=math.exp(d + q * se), p=t.pvalue,
                             mean_swarm=n9[(n9.system == 'swarm') & (n9['load'] == ld)][m].mean(), mean_otro=n9[(n9.system == sysb) & (n9['load'] == ld)][m].mean()))
C9 = pd.DataFrame(rows)
C9['p_holm_m8'] = C9.groupby('sistema')['p'].transform(lambda s: multipletests(s, method='holm')[1])
C9.to_csv(os.path.join(OUT, 'n9b_swarm_vs_sistemas_independiente.csv'), index=False)
dt = C9[C9.sistema == 'decision_table']
RES['n9b_swarm_vs_decision_table'] = dict(p95_ratio=dt[dt.metric == 'p95_latency_ms'].set_index('load').ratio.round(2).to_dict(), thr_ratio=dt[dt.metric == 'throughput_http'].set_index('load').ratio.round(3).to_dict(),
                                          p95_media_swarm=dt[dt.metric == 'p95_latency_ms'].set_index('load').mean_swarm.round(1).to_dict(), p95_media_dt=dt[dt.metric == 'p95_latency_ms'].set_index('load').mean_otro.round(1).to_dict(),
                                          thr_media_swarm=dt[dt.metric == 'throughput_http'].set_index('load').mean_swarm.round(2).to_dict(), thr_media_dt=dt[dt.metric == 'throughput_http'].set_index('load').mean_otro.round(1).to_dict(),
                                          significativas_de_8=int((dt.p_holm_m8 < 0.05).sum()), max_p_holm=float(dt.p_holm_m8.max()))
for s in ('rules', 'bruteforce'):
    g = C9[C9.sistema == s]
    RES[f'n9b_swarm_vs_{s}'] = dict(p95_ratio=[round(g[g.metric == 'p95_latency_ms'].ratio.min(), 3), round(g[g.metric == 'p95_latency_ms'].ratio.max(), 3)],
                                    thr_ratio=[round(g[g.metric == 'throughput_http'].ratio.min(), 3), round(g[g.metric == 'throughput_http'].ratio.max(), 3)],
                                    signif_p95=int((g[g.metric == 'p95_latency_ms'].p_holm_m8 < 0.05).sum()), signif_thr=int((g[g.metric == 'throughput_http'].p_holm_m8 < 0.05).sum()),
                                    thr_signif_por_carga=g[(g.metric == 'throughput_http')].set_index('load').p_holm_m8.round(4).to_dict())
# consistencia N9b vs N2
cons = []
for sysn in ('swarm', 'decision_table'):
    for ld in (1, 5, 10, 25):
        for m in ('p95_latency_ms', 'throughput_http'):
            x = np.log(n9[(n9.system == sysn) & (n9['load'] == ld)][m]); y = np.log(n2[(n2.system == sysn) & (n2['load'] == ld)][m])
            cons.append(dict(sistema=sysn, load=ld, metric=m, ratio_N9b_sobre_N2=math.exp(x.mean() - y.mean()), p=stats.ttest_ind(x, y, equal_var=False).pvalue))
K = pd.DataFrame(cons); K['p_holm_m16'] = multipletests(K.p, method='holm')[1]
K.to_csv(os.path.join(OUT, 'n9b_vs_n2_consistencia_independiente.csv'), index=False)
RES['n9b_vs_n2'] = {s: dict(rango_ratio=[round(g.ratio_N9b_sobre_N2.min(), 3), round(g.ratio_N9b_sobre_N2.max(), 3)], signif=int((g.p_holm_m16 < 0.05).sum()), de=len(g)) for s, g in K.groupby('sistema')}
RES['n2_swarm_vs_dt_p95_ratio'] = {int(l): round(math.exp(np.log(n2[(n2.system == 'swarm') & (n2['load'] == l)].p95_latency_ms).mean() - np.log(n2[(n2.system == 'decision_table') & (n2['load'] == l)].p95_latency_ms).mean()), 2) for l in (1, 5, 10, 25)}

json.dump(RES, open(os.path.join(OUT, 'verificacion_independiente.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=str)
print(json.dumps(RES, ensure_ascii=False, indent=1, default=str))

# ---------------------------------------------------------------- comprobaciones adicionales (OE4 N11 y N9b)
extra = {}
vb = v[v.tramo == 'B'].copy()
for m, nm in (('p95_latency_ms', 'p95'), ('throughput_http', 'thr'), ('t_conv_ms_mean', 'tconv')):
    vb['y'] = np.log(vb[m])
    mod = smf.ols('y ~ C(N) * C(load)', data=vb).fit()
    rho = stats.spearmanr(vb['execution_index'], mod.resid)
    extra[f'deriva_B_{nm}'] = dict(rho=round(float(rho[0]), 3), p=round(float(rho[1]), 3))
    va = v.copy(); va['y'] = np.log(va[m])
    mod2 = smf.ols('y ~ C(N) * C(load) + C(tramo)', data=va).fit()
    an = sm.stats.anova_lm(mod2, typ=2)
    ss_res = an.loc['Residual', 'sum_sq']
    extra[f'eta2_parcial_{nm}'] = {t: round(float(an.loc[t, 'sum_sq'] / (an.loc[t, 'sum_sq'] + ss_res)), 3) for t in ['C(N)', 'C(load)', 'C(tramo)', 'C(N):C(load)']}
    extra[f'p_interaccion_{nm}'] = round(float(an.loc['C(N):C(load)', 'PR(>F)']), 3)
KK = pd.read_csv(os.path.join(OUT, 'n9b_vs_n2_consistencia_independiente.csv'))
for (s_, m_), g in KK.groupby(['sistema', 'metric']):
    extra[f'n9b_vs_n2_{s_}_{m_}'] = [round(g.ratio_N9b_sobre_N2.min(), 3), round(g.ratio_N9b_sobre_N2.max(), 3), int((g.p_holm_m16 < 0.05).sum())]
# k_stop por N (solo si existe la columna)
RES['extra'] = extra
json.dump(RES, open(os.path.join(OUT, 'verificacion_independiente.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=str)
print(json.dumps(extra, ensure_ascii=False, indent=1))
