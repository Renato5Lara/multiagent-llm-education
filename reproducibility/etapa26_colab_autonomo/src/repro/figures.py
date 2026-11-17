"""Figuras de resultados de la tesis (Figuras 1 a 5), generadas desde las SALIDAS DEL ANALISIS ejecutado en el notebook.

El dibujo reproduce el de `hacer_figuras.py` (script local con el que se generaron las imagenes de la tesis; sha256 7eccd5f6...):
mismos paneles, escalas, colores y tamanos. Diferencias deliberadas, todas documentadas en docs/figure_traceability.md:
  * sin rutas absolutas de Windows: las entradas son parametros;
  * fuente 'Arial' con respaldo (Liberation Sans / DejaVu Sans) porque Arial no existe en Colab;
  * la etiqueta 'media 0,804' se calcula de los datos en lugar de escribirse a mano;
  * las metas de diseno (2 000 ms, 20 req/s, 0,85, banda del 5 %) se leen de manifests/valores_oficiales.json.
Cada figura se exporta en PNG (300 ppi) y SVG, y se guarda el CSV exacto de la serie dibujada (figure_data/)."""
import json
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

C1, C2, C3 = '#1f4e79', '#c55a11', '#548235'
METAS = dict(p95_ms=2000, thr_rps=20, f1_ref=0.85, banda_efecto=0.05)


def _estilo():
    plt.rcParams.update({'font.family': 'sans-serif', 'font.sans-serif': ['Arial', 'Liberation Sans', 'DejaVu Sans'], 'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False,
                         'axes.titlesize': 10, 'axes.labelsize': 10, 'legend.frameon': False, 'figure.dpi': 100})


coma = FuncFormatter(lambda v, p: ('%g' % round(v, 6)).replace('.', ','))
miles = FuncFormatter(lambda v, p: ('{:,.0f}'.format(v)).replace(',', ' '))


def _guardar(fig, out_dir, nombre, serie):
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(os.path.join(out_dir, 'figure_data'), exist_ok=True)
    png = os.path.join(out_dir, nombre + '.png')
    fig.savefig(png, dpi=300, bbox_inches='tight')
    fig.savefig(os.path.join(out_dir, nombre + '.svg'), bbox_inches='tight')
    plt.close(fig)
    csv = os.path.join(out_dir, 'figure_data', nombre + '_serie.csv')
    pd.DataFrame(serie).to_csv(csv, index=False)
    return dict(png=png, svg=png[:-4] + '.svg', serie_csv=csv)


def fig_oe1(resultados_oe1_json, out_dir, metas=None):
    _estilo()
    j = json.load(open(resultados_oe1_json, encoding='utf8'))
    i13 = j['confiabilidad_I13']; rel = j['relacion_S_respuesta']
    fig, ax = plt.subplots(1, 2, figsize=(6.4, 2.9), gridspec_kw={'width_ratios': [1, 1.25]})
    labs = ['0 %', '2 %', '5 %']; keys = ['0.0', '0.02', '0.05']
    est = [i13[k]['ciclos_pool']['est'] for k in keys]; lo = [i13[k]['ciclos_pool']['lo'] for k in keys]; hi = [i13[k]['ciclos_pool']['hi'] for k in keys]
    ax[0].bar(labs, est, color=[C1, C2, C2], width=0.55)
    ax[0].errorbar(labs, est, yerr=[np.array(est) - np.array(lo), np.array(hi) - np.array(est)], fmt='none', ecolor='black', capsize=3, lw=1)
    for x, e in zip(labs, est):
        ax[0].text(x, e + 0.03, ('%.3f' % e).replace('.', ','), ha='center', fontsize=9)
    ax[0].set_ylim(0, 1.12); ax[0].yaxis.set_major_formatter(coma)
    ax[0].set_xlabel('Pérdida de mensajes en el bus'); ax[0].set_ylabel('I-13 (ciclos completados / peticiones)'); ax[0].set_title('a) Confiabilidad', loc='left')
    names = [('p95', 'P95'), ('thr', 'Throughput'), ('tconv', 'T_conv'), ('f1', 'F1_adapt')]
    rho = [rel[k]['rho_intra_bloque'] for k, _ in names]; rlo = [rel[k]['ic95_bootstrap_por_bloque'][0] for k, _ in names]; rhi = [rel[k]['ic95_bootstrap_por_bloque'][1] for k, _ in names]
    y = np.arange(len(names))[::-1]
    ax[1].errorbar(rho, y, xerr=[np.array(rho) - np.array(rlo), np.array(rhi) - np.array(rho)], fmt='o', color=C1, ecolor=C1, capsize=3)
    ax[1].axvline(0, color='gray', lw=0.8, ls='--')
    ax[1].set_yticks(y); ax[1].set_yticklabels([n for _, n in names]); ax[1].set_xlim(-0.5, 0.5); ax[1].xaxis.set_major_formatter(coma)
    ax[1].set_xlabel('ρ de Spearman intra-bloque con S (IC95 %)'); ax[1].set_title('b) Cumplimiento (S) y desempeño', loc='left')
    fig.tight_layout()
    serie = [dict(panel='a', serie='I-13 (Wilson, ciclos agrupados)', x=l, y=e, lo=a, hi=b) for l, e, a, b in zip(labs, est, lo, hi)] + \
            [dict(panel='b', serie='rho intra-bloque con S', x=n, y=r, lo=a, hi=b) for (_, n), r, a, b in zip(names, rho, rlo, rhi)]
    return _guardar(fig, out_dir, 'fig_oe1', serie)


def fig_oe2(resultados_oe2b_json, out_dir, metas=None):
    _estilo(); m = {**METAS, **(metas or {})}
    j = json.load(open(resultados_oe2b_json, encoding='utf8')); pc = j['resultados']['por_carga']
    cargas = ['1', '5', '10', '25', '50', '100']; xs = [int(c) for c in cargas]; serie = []

    def ser(ind, ci):
        return (np.array([pc[c][ind][ci]['est'] for c in cargas]), np.array([pc[c][ind][ci]['lo'] for c in cargas]), np.array([pc[c][ind][ci]['hi'] for c in cargas]))
    fig, ax = plt.subplots(1, 3, figsize=(6.6, 2.7))
    for a, (ind, ci, tit, yl, col, pan) in zip(ax, [('p95_ms', 'ic95_t_log', 'a) P95 de la latencia', 'ms', C1, 'a'), ('throughput_rps', 'ic95_t', 'b) Throughput', 'req/s', C2, 'b'), ('t_conv_ms', 'ic95_t_log', 'c) T_conv por petición', 'ms', C3, 'c')]):
        e, l, h = ser(ind, ci)
        a.errorbar(xs, e, yerr=[e - l, h - e], fmt='o-', color=col, capsize=2.5, lw=1.2, ms=4)
        a.set_xscale('log'); a.set_xticks(xs); a.set_xticklabels(cargas, fontsize=8); a.xaxis.set_minor_formatter(FuncFormatter(lambda v, p: ''))
        a.set_xlabel('Usuarios concurrentes'); a.set_ylabel(yl); a.set_title(tit, loc='left', fontsize=9)
        if ind != 'throughput_rps':
            a.set_yscale('log'); a.yaxis.set_major_formatter(miles)
        else:
            a.yaxis.set_major_formatter(coma)
        serie += [dict(panel=pan, serie=ind, x=x, y=yy, lo=ll, hi=hh) for x, yy, ll, hh in zip(xs, e, l, h)]
    ax[0].axhline(m['p95_ms'], color='gray', ls='--', lw=0.9); ax[0].text(1.1, m['p95_ms'] * 1.075, f"meta {m['p95_ms']:,} ms".replace(',', ' '), fontsize=7.5, color='gray')
    ax[1].axhline(m['thr_rps'], color='gray', ls='--', lw=0.9); ax[1].text(1.1, m['thr_rps'] + 0.8, f"meta {m['thr_rps']} req/s", fontsize=7.5, color='gray')
    fig.tight_layout()
    return _guardar(fig, out_dir, 'fig_oe2', serie)


def fig_oe3(contrastes_csv, out_dir, metas=None):
    _estilo(); m = {**METAS, **(metas or {})}
    d = pd.read_csv(contrastes_csv); d = d[d.respuesta == 'log_tconv'].copy()
    orden = [('P1_despacho', 'sequential frente a batch', 'Despacho: secuencial frente a por lotes'), ('P2_difusion_gbest', 'True frente a False', 'Difusión de g_best: con frente a sin'),
             ('M_mecanismo', 'pso frente a cognitive', 'Mecanismo: PSO frente a cognitivo'), ('M_mecanismo', 'social frente a cognitive', 'Mecanismo: social frente a cognitivo'),
             ('M_mecanismo', 'social frente a pso', 'Mecanismo: social frente a PSO'), ('R1_heuristica_AG1', 'True frente a False', 'Arranque heurístico de AG1: con frente a sin'),
             ('R2_replicas', '2 frente a 1', 'Consumidores por agente: 2 frente a 1')]
    dd = pd.DataFrame([dict(d[(d.factor == f) & (d.contraste == c)].iloc[0], et=e) for f, c, e in orden]).reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(6.4, 3.2)); y = np.arange(len(dd))[::-1]
    ax.errorbar(dd.estimacion, y, xerr=[dd.estimacion - dd.ic95_inf, dd.ic95_sup - dd.estimacion], fmt='o', color=C1, ecolor=C1, capsize=3, ms=4)
    ax.axvline(1, color='gray', ls='--', lw=0.9); b = m['banda_efecto']; ax.axvspan(1 - b, 1 + b, color='#d9d9d9', alpha=0.5, lw=0)
    ax.set_yticks(y); ax.set_yticklabels(dd.et, fontsize=8); ax.xaxis.set_major_formatter(coma)
    ax.set_xlabel('Razón de medias geométricas del T_conv (IC95 %)', fontsize=9)
    ax.text(1.0, len(dd) - 0.35, 'banda gris: efecto inferior al 5 %', ha='center', fontsize=7.5, color='#595959'); ax.set_ylim(-0.6, len(dd) - 0.1)
    fig.tight_layout()
    serie = [dict(panel='unico', serie=r.et, x=r.estimacion, y=int(i), lo=r.ic95_inf, hi=r.ic95_sup) for i, r in dd.iterrows()]
    return _guardar(fig, out_dir, 'fig_oe3', serie)


def fig_oe4(celdas_csv, out_dir, metas=None):
    _estilo(); m = {**METAS, **(metas or {})}
    c = pd.read_csv(celdas_csv); fig, ax = plt.subplots(1, 3, figsize=(6.6, 2.7)); serie = []
    for w, col, mk in [(4, C1, 'o'), (1, C2, 's')]:
        for N, ls in [(10, ':'), (20, '-'), (30, '--')]:
            s = c[(c.workers == w) & (c.N == N)].sort_values('carga'); lab = f'{w} worker{"s" if w > 1 else ""}, N = {N}'
            ax[0].plot(s.carga, s.p95_geo, ls=ls, color=col, marker=mk, ms=3, lw=1, label=lab)
            ax[1].plot(s.carga, s.thr_media, ls=ls, color=col, marker=mk, ms=3, lw=1)
            ax[2].plot(s.carga, s.tconv_geo, ls=ls, color=col, marker=mk, ms=3, lw=1)
            for pan, v in (('a', s.p95_geo), ('b', s.thr_media), ('c', s.tconv_geo)):
                serie += [dict(panel=pan, serie=lab, x=x, y=yy, lo='', hi='') for x, yy in zip(s.carga, v)]
    xs = [1, 5, 10, 25, 50, 100]
    for a, tit, yl in zip(ax, ['a) P95 de la latencia', 'b) Throughput', 'c) T_conv por petición'], ['ms', 'req/s', 'ms']):
        a.set_xscale('log'); a.set_xticks(xs); a.set_xticklabels([str(x) for x in xs], fontsize=8); a.xaxis.set_minor_formatter(FuncFormatter(lambda v, p: ''))
        a.set_xlabel('Usuarios concurrentes'); a.set_ylabel(yl); a.set_title(tit, loc='left', fontsize=9)
    for a in (ax[0], ax[2]):
        a.set_yscale('log'); a.yaxis.set_major_formatter(miles)
    ax[1].yaxis.set_major_formatter(coma)
    ax[0].axhline(m['p95_ms'], color='gray', ls='--', lw=0.9); ax[1].axhline(m['thr_rps'], color='gray', ls='--', lw=0.9)
    h, l = ax[0].get_legend_handles_labels(); fig.legend(h, l, loc='lower center', ncol=3, fontsize=7.5, bbox_to_anchor=(0.5, -0.17)); fig.tight_layout()
    return _guardar(fig, out_dir, 'fig_oe4', serie)


def fig_oe5(f1_por_perfil_csv, out_dir, metas=None):
    _estilo(); m = {**METAS, **(metas or {})}
    f = pd.read_csv(f1_por_perfil_csv); f['arq'] = f.profile_id.str.extract(r'syn-([a-z_]+?)-')
    nombres = {'balanced_multimodal': 'Equilibrado', 'explanatory_conceptual': 'Explicativo-conceptual', 'logical_syntactic': 'Lógico-sintáctico', 'visual_dominant': 'Visual dominante'}
    fig, ax = plt.subplots(1, 2, figsize=(6.6, 2.9), gridspec_kw={'width_ratios': [1, 1.1]}); media = float(f.f1_adapt_perfil.mean())
    ax[0].hist(f.f1_adapt_perfil, bins=np.linspace(0.3, 1.0, 15), color=C1, edgecolor='white')
    ax[0].axvline(m['f1_ref'], color=C2, ls='--', lw=1.2); ax[0].axvline(media, color='black', lw=1.2)
    ax[0].text(m['f1_ref'] + 0.005, ax[0].get_ylim()[1] * 0.92, 'referencia ' + ('%.2f' % m['f1_ref']).replace('.', ','), color=C2, fontsize=8)
    ax[0].text(media - 0.01, ax[0].get_ylim()[1] * 0.80, 'media ' + ('%.3f' % media).replace('.', ','), ha='right', fontsize=8)
    ax[0].set_xlabel('F1_adapt por perfil'); ax[0].set_ylabel('Perfiles'); ax[0].xaxis.set_major_formatter(coma); ax[0].set_title('a) Distribución (n = %d)' % len(f), loc='left')
    ords = ['explanatory_conceptual', 'balanced_multimodal', 'logical_syntactic', 'visual_dominant']; data = [f[f.arq == o].f1_adapt_perfil.values for o in ords]
    bp = ax[1].boxplot(data, vert=False, patch_artist=True, widths=0.55, medianprops=dict(color='black'))
    for b in bp['boxes']:
        b.set_facecolor('#bdd7ee')
    ax[1].set_yticks(range(1, 5)); ax[1].set_yticklabels([nombres[o] for o in ords], fontsize=8); ax[1].axvline(m['f1_ref'], color=C2, ls='--', lw=1.2)
    ax[1].invert_yaxis(); ax[1].xaxis.set_major_formatter(coma); ax[1].set_xlabel('F1_adapt por perfil'); ax[1].set_title('b) Por arquetipo', loc='left'); fig.tight_layout()
    serie = [dict(panel='a', serie='F1_adapt por perfil', x=r.profile_id, y=r.f1_adapt_perfil, lo='', hi='') for r in f.itertuples()]
    res = _guardar(fig, out_dir, 'fig_oe5', serie)
    res['media_f1'] = media
    return res


def fig_oe2a_complementaria(raw_observations_csv, resultados_oe2a_json, out_dir, metas=None):
    """FIGURA COMPLEMENTARIA (no figura en la tesis): distribucion del T_conv de los ciclos de OE2-A y por lote, desde las observaciones por ciclo."""
    _estilo()
    d = pd.read_csv(raw_observations_csv)
    d = d[d['package_valid'].astype(str).str.lower() == 'true'] if d['package_valid'].dtype == object else d[d['package_valid'] == True]  # noqa: E712
    r = json.load(open(resultados_oe2a_json, encoding='utf8'))['tconv_I02']
    fig, ax = plt.subplots(1, 2, figsize=(6.6, 2.9), gridspec_kw={'width_ratios': [1.1, 1]})
    ax[0].hist(d.t_conv_ms, bins=np.geomspace(max(d.t_conv_ms.min(), 1e-3), d.t_conv_ms.max(), 40), color=C1, edgecolor='white')
    ax[0].set_xscale('log'); ax[0].axvline(r['media_geometrica_ms'], color=C2, ls='--', lw=1.2)
    ax[0].text(r['media_geometrica_ms'] * 1.05, ax[0].get_ylim()[1] * 0.9, 'media geométrica ' + ('%.2f' % r['media_geometrica_ms']).replace('.', ',') + ' ms', color=C2, fontsize=7.5)
    ax[0].set_xticks([40, 60, 80, 100, 120]); ax[0].set_xticklabels(['40', '60', '80', '100', '120']); ax[0].xaxis.set_minor_formatter(FuncFormatter(lambda v, p: ''))
    ax[0].set_xlabel('T_conv por ciclo (ms)'); ax[0].set_ylabel('Ciclos'); ax[0].set_title('a) Distribución (n = %d)' % len(d), loc='left'); ax[0].xaxis.set_major_formatter(miles)
    lotes = sorted(d.lote.unique()); ax[1].boxplot([d[d.lote == l].t_conv_ms.values for l in lotes], vert=True, patch_artist=True, widths=0.55, medianprops=dict(color='black'),
                                                    boxprops=dict(facecolor='#bdd7ee'), flierprops=dict(markersize=2))
    ax[1].set_xticks(range(1, len(lotes) + 1)); ax[1].set_xticklabels([str(l) for l in lotes]); ax[1].set_xlabel('Lote'); ax[1].set_ylabel('ms'); ax[1].set_title('b) Por lote', loc='left')
    fig.tight_layout()
    serie = [dict(panel='a', serie='T_conv por ciclo', x=int(i), y=float(v), lo='', hi='') for i, v in zip(d.exec_index, d.t_conv_ms)]
    return _guardar(fig, out_dir, 'fig_oe2a_complementaria', serie)


FIGURAS = {'OE1': ('fig_oe1', fig_oe1), 'OE2-B': ('fig_oe2', fig_oe2), 'OE3': ('fig_oe3', fig_oe3), 'OE4': ('fig_oe4', fig_oe4), 'OE5': ('fig_oe5', fig_oe5)}
