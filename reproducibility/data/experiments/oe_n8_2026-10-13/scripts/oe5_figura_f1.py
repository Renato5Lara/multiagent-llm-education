"""OE5 — figura de F1_adapt v3 por arquetipo y de precision/recall por modalidad, desde oe5_f1_repro/f1_v3_independent.json (datos medidos; sin valores estimados).
Uso (desde oe_n8_2026-10-13/): python scripts/oe5_figura_f1.py   Salida: oe5_f1_repro/oe5_f1_arquetipo_modalidad.png"""
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

d = json.load(open('oe5_f1_repro/f1_v3_independent.json', encoding='utf-8'))
fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
arq = [('balanced_multimodal', 'Balanced-\nMultimodal'), ('visual_dominant', 'Visual-\nDominant'), ('explanatory_conceptual', 'Explanatory-\nConceptual'), ('logical_syntactic', 'Logical-\nSyntactic')]
v = [d['by_archetype'][k] for k, _ in arq]
b = ax[0].bar([n for _, n in arq], v, color='#1f77b4')
ax[0].axhline(0.85, color='gray', ls='--', label='meta 0,85')
ax[0].axhline(d['f1_adapt_mean'], color='#d62728', ls=':', label='media global 0,8156')
ax[0].legend(fontsize=8, loc='lower right', framealpha=0.95)
for r, x in zip(b, v):
    ax[0].text(r.get_x() + r.get_width() / 2, 0.45, f'{x:.3f}'.replace('.', ','), ha='center', fontsize=9, color='white', fontweight='bold')
ax[0].set_ylim(0, 1.0); ax[0].set_ylabel('F1_adapt v3 (media por caso)'); ax[0].set_title('F1_adapt por arquetipo (1 000 casos)', fontsize=10)
mods = [('code', 'Código'), ('diagram', 'Diagrama'), ('text', 'Texto'), ('audio', 'Audio')]
x = np.arange(4); w = 0.38
p = [d['by_modality'][k]['precision'] for k, _ in mods]; r_ = [d['by_modality'][k]['recall'] for k, _ in mods]
ax[1].bar(x - w / 2, p, w, label='Precisión', color='#2ca02c'); ax[1].bar(x + w / 2, r_, w, label='Recall', color='#ff7f0e')
for i in range(4):
    ax[1].text(x[i] - w / 2, p[i] + 0.01, f'{p[i]:.2f}'.replace('.', ','), ha='center', fontsize=8)
    ax[1].text(x[i] + w / 2, r_[i] + 0.01, f'{r_[i]:.2f}'.replace('.', ','), ha='center', fontsize=8)
ax[1].set_xticks(x); ax[1].set_xticklabels([n for _, n in mods]); ax[1].set_ylim(0, 1.25); ax[1].legend(fontsize=8, loc='upper right', ncol=2)
ax[1].set_title('Precisión y recall por modalidad (agrupando casos)', fontsize=10)
fig.suptitle('OE5: precisión de la adaptación con la especificación v3 provisional (K = 10 réplicas × 100 perfiles)', fontsize=10)
fig.text(0.5, 0.005, 'Datos: oe_n8_2026-10-13/oe5_f1_repro/f1_v3_independent.json (recálculo independiente de oe_n5_2026-10-06) · experimental no oficial · regla v3 provisional', ha='center', fontsize=7)
fig.tight_layout(rect=(0, 0.03, 1, 0.95)); fig.savefig('oe5_f1_repro/oe5_f1_arquetipo_modalidad.png', dpi=200)
