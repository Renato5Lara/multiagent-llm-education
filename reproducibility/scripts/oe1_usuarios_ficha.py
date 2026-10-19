"""Ficha reproducible: asociación entre el número de usuarios y el puntaje de cumplimiento del OE1 (Tabla 6, última fila).

Entradas: data/experiments/oe_n1_2026-10-05/oe1_report/oe1_report.json (relationship.per_condition: compliance_score por condición; derivado del propio arnés)
y el número de usuarios, que está codificado en el nombre de cada condición (token `c<k>`). Misma pregunta analítica para ambas medidas (n = 14 condiciones; unidad = condición).
Salidas: outputs/oe1_usuarios_ficha.json. Comprueba además cuál de las dos medidas es la publicada en la Tabla 6.
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]


def main():
    rep = json.loads((ROOT / "data/experiments/oe_n1_2026-10-05/oe1_report/oe1_report.json").read_text(encoding="utf-8"))
    per = rep["relationship"]["per_condition"]
    conds = sorted(per)
    score = np.array([per[c]["compliance_score"] for c in conds], float)
    users = np.array([next(int(t[1:]) for t in c.split("|") if t.startswith("c") and t[1:].isdigit()) for c in conds], float)
    sp = stats.spearmanr(users, score)
    kd = stats.kendalltau(users, score)
    tablas = json.loads((ROOT / "data/metadata/informe_D2.9.7_tablas.json").read_text(encoding="utf-8"))["tables"]
    fila = next(r for r in tablas[6]["rows"] if r[0].startswith("Usuarios"))
    verif = json.loads((ROOT / "data/experiments/oe_n8_2026-10-13/oe1_verify/oe1_verify.json").read_text(encoding="utf-8"))["asociacion_carga_vs_puntaje"]
    n = len(conds)
    c, d = 0, 0
    for i in range(n):
        for j in range(i + 1, n):
            s = np.sign(users[i] - users[j]) * np.sign(score[i] - score[j])
            c += s > 0
            d += s < 0
    out = dict(
        pregunta="asociación monótona entre usuarios (carga) y puntaje de cumplimiento por condición",
        n_condiciones=n, usuarios_distintos=sorted(set(users.tolist())), puntajes_distintos=sorted(set(np.round(score, 4).tolist())),
        empates=dict(en_usuarios=int(n - len(set(users.tolist()))), en_puntaje=int(n - len(set(np.round(score, 4).tolist())))),
        spearman=dict(rho=float(sp.statistic), p=float(sp.pvalue), definicion="correlación de Pearson de los rangos (rangos medios en empates); p bilateral"),
        kendall_tau_b=dict(tau=float(kd.statistic), p=float(kd.pvalue), definicion="(concordantes − discordantes)/sqrt((n0 − n1)(n0 − n2)), corrige empates; p bilateral asintótico con empates", concordantes=int(c), discordantes=int(d)),
        medida_publicada_en_tabla_6=dict(fila=fila, spearman_publicado=fila[1], kendall_publicado=fila[2], coincide_spearman_con_oe1_verify=bool(abs(verif["spearman_rho"] - float(sp.statistic)) < 1e-9)),
        relacion_entre_medidas="ρ y τb miden la misma asociación monótona en escalas distintas (con pocos puntajes distintos y empates ρ suele ser mayor en valor absoluto que τb; en las otras filas de la Tabla 6 ρ = −0,69 y τb = −0,51): no son contradictorios y no se sustituyen",
        conclusion_admisible="en las 14 condiciones, a mayor número de usuarios menor puntaje de cumplimiento (asociación monótona negativa moderada: ρ = −0,61, τb = −0,51); la tesis publica ρ y marca τb como «no calculado». El puntaje carece de definición aprobada y solo hay 3 valores distintos, por lo que la asociación no es causal",
    )
    (ROOT / "outputs/oe1_usuarios_ficha.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("n_condiciones", "empates", "spearman", "kendall_tau_b", "medida_publicada_en_tabla_6")}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
