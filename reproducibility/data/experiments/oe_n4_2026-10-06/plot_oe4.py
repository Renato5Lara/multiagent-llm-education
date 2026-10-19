"""Gráficos OE4 a partir de resumen_oe4.json (requiere matplotlib; el análisis usa el entorno del proyecto)."""
import json
from pathlib import Path

LOADS = [1, 5, 10, 25, 50, 100]
HERE = Path(__file__).parent
table = json.loads((HERE / "resumen_oe4.json").read_text(encoding="utf-8"))["table"]
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

for fname, key, ylabel, ref in (("oe4_usuarios_vs_tconv.png", "tconv_http_ms", "T_conv por corrida (ms)", None), ("oe4_usuarios_vs_p95.png", "p95_ms", "L_resp P95 por corrida (ms)", 2000),
                                ("oe4_usuarios_vs_throughput.png", "throughput_rps", "throughput (req/s)", 20)):
    fig, ax = plt.subplots(figsize=(5, 3.6))
    y = [r[key] for r in table]
    err = [[r[key] - r[key + "_ci95"][0] for r in table], [r[key + "_ci95"][1] - r[key] for r in table]]
    ax.errorbar(LOADS, y, yerr=err, marker="o", capsize=3)
    if ref:
        ax.axhline(ref, ls=":", color="gray")
    ax.set_xscale("log")
    ax.set_xticks(LOADS)
    ax.set_xticklabels(LOADS)
    ax.set_xlabel("usuarios concurrentes")
    ax.set_ylabel(ylabel)
    ax.grid(alpha=.3)
    ax.set_title("OE4 N4 — swarm N=20 (media ± IC95, 10 corridas)", fontsize=8)
    fig.tight_layout()
    fig.savefig(HERE / fname, dpi=130)
    plt.close(fig)
