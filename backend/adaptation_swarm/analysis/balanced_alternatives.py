"""Informe COMPARATIVO de alternativas explícitas para el gold de Balanced-Multimodal y la regla de inclusión (respuesta del asesor, 2026-09-25: D1, D2).

TODO resultado de este informe es PROVISIONAL y EXPLORATORIO: se calcula sobre las corridas históricas ya conocidas (post-hoc), NINGUNA regla está aprobada por el asesor, y no
sirve para declarar cumplimiento de RNF-03 ni para elegir la regla mirando cuál «da mejor F1». La regla oficial se aprueba por criterio metodológico ANTES de la corrida nueva
(`gold/rubric_v2.APPROVED_RULE_VERSIONS`) y se aplica a réplicas nuevas.

Balanced es parte del diseño aprobado de n = 100 (25 de los 100 perfiles): el informe NUNCA lo excluye; compara cómo cambia el resultado según cómo se DEFINE su gold y cuándo una
modalidad cuenta como «incluida». Familias comparadas:
    · conjunto de modalidades esperadas       (gold-v2-cand-A: Balanced espera las cuatro);
    · tolerancia de empate                    (gold-v2-cand-B-tol…: conjunto esperado desde el centroide; tol 0.05 equivale a A con centroids-v1, tol 0.35 es un límite amplio);
    · regla de inclusión/exclusión            (incl-ge1, incl-ge2, incl-top-tol0, incl-top-tol1);
    · clase «balanceada»                      (alternativa de UNA etiqueta con una quinta clase; NO cumple el 4×4 pedido, se incluye solo para comparar);
y, como referencia de compatibilidad, la definición histórica (gold-v1 + modalidad dominante), que reproduce exactamente la evidencia congelada.

Solo lee los JSON congelados (no los modifica); escribe únicamente en un directorio NUEVO (nunca dentro de resultados congelados, datasets ni paquetes de evidencia).

    python -m adaptation_swarm.analysis.balanced_alternatives --out-dir NUEVO [--runs corrida-poc-1 corrida-poc-2]
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from adaptation_swarm.gold import rubric as gold_v1
from adaptation_swarm.gold.f1_multilabel import METRIC_VERSION, cases_from_records, multilabel_report
from adaptation_swarm.gold.labels_v2 import emphasis_from_S
from adaptation_swarm.gold.rubric_v2 import GOLD_RULES, INCLUSION_RULES, EvaluationRule, LegacyDominantRule, MultilabelRule
from adaptation_swarm.profiles.models import Archetype, Difficulty
from adaptation_swarm.pso.space import MODALITIES
from adaptation_swarm.tools import isolated_env as iso

REPORT_VERSION = "balanced-alternatives-v1"
RESULTS = iso.BACK / "experiments" / "results"
DEFAULT_RUNS = ("corrida-poc-1", "corrida-poc-2")
BANNER = ("PROVISIONAL — análisis EXPLORATORIO post-hoc sobre corridas históricas. NO es evidencia confirmatoria ni cumplimiento de RNF-03. "
          "Ninguna regla está aprobada por el asesor. Balanced forma parte del diseño n = 100 y no se excluye.")
FIVE_CLASSES = MODALITIES + ("balanced",)


def load_records(label: str, results: Path = RESULTS) -> tuple[list[dict], dict]:
    path = results / f"adaptation_swarm_{label}.json"
    raw = path.read_bytes()
    cases = [c for c in json.loads(raw)["cases"] if c["status"] == "completed"]
    return cases, {"file": path.name, "sha256": hashlib.sha256(raw).hexdigest(), "n_cases": len(cases)}


def five_class_report(records: list[dict]) -> dict:
    """Alternativa de UNA etiqueta con clase «balanceada»: gold = «balanced» para el arquetipo Balanced y la dominante de gold-v1 para el resto; predicho = «balanced» si los 4
    énfasis son iguales y, si no, la modalidad dominante con el desempate histórico. Matriz 5×5; no es el 4×4 pedido por el asesor."""
    idx = {c: i for i, c in enumerate(FIVE_CLASSES)}
    cm = np.zeros((5, 5), dtype=int)
    for r in records:
        arch = Archetype(r["archetype"])
        gold = "balanced" if arch is Archetype.BALANCED_MULTIMODAL else gold_v1.expected_dominant(arch, Difficulty(r["difficulty"]))
        e = emphasis_from_S(r["g_best_S"])
        pred = "balanced" if max(e) == min(e) else gold_v1.predicted_dominant(e)
        cm[idx[gold], idx[pred]] += 1
    f1s = []
    per = {}
    for c in FIVE_CLASSES:
        i = idx[c]
        tp, fp, fn = int(cm[i, i]), int(cm[:, i].sum() - cm[i, i]), int(cm[i, :].sum() - cm[i, i])
        p = None if tp + fp == 0 else tp / (tp + fp)
        rc = None if tp + fn == 0 else tp / (tp + fn)
        f1 = None if (p is None and rc is None) else 0.0 if (p is None or rc is None or p + rc == 0) else 2 * p * rc / (p + rc)
        per[c] = {"precision": p, "recall": rc, "f1": f1, "support": tp + fn}
        if f1 is not None:
            f1s.append(f1)
    return {"classes": list(FIVE_CLASSES), "matrix_5x5": cm.tolist(), "per_class": per, "macro_f1_defined": float(np.mean(f1s)), "accuracy": float(np.trace(cm) / cm.sum())}


def alternatives() -> list[dict]:
    """Alternativas comparadas (todas PROVISIONALES). La primera es la definición histórica, solo de referencia."""
    out = [{"id": LegacyDominantRule.rule_version, "family": "histórica (referencia de compatibilidad)", "rule": LegacyDominantRule(),
            "description": "gold-v1 + modalidad dominante con desempate; reproduce la evidencia congelada"}]
    fam = {"gold-v2-cand-A": "conjunto de modalidades esperadas", "gold-v2-cand-B-tol0.05": "tolerancia de empate (0.05)", "gold-v2-cand-B-tol0.35": "tolerancia de empate (0.35)"}
    for gv, g in GOLD_RULES.items():
        for iv, inc in INCLUSION_RULES.items():
            rule = MultilabelRule(g, inc)
            out.append({"id": rule.rule_version, "family": f"{fam[gv]} × inclusión", "rule": rule, "description": f"{g.description} Inclusión: {inc.description}."})
    return out


def _metrics(records: list[dict], rule: EvaluationRule) -> dict:
    rep = multilabel_report(cases_from_records(records, rule), rule)
    by_arch: dict[str, list[float]] = {}
    changed_vs_v1 = {}
    for r, pc in zip(records, rep.per_case):
        if pc["f1"] is not None:
            by_arch.setdefault(r["archetype"], []).append(pc["f1"])
        v1 = [gold_v1.expected_dominant(Archetype(r["archetype"]), Difficulty(r["difficulty"]))]
        if pc["gold"] != v1:
            changed_vs_v1[r["archetype"]] = changed_vs_v1.get(r["archetype"], 0) + 1
    sizes = {}
    for pc in rep.per_case:
        sizes[len(pc["predicted"])] = sizes.get(len(pc["predicted"]), 0) + 1
    return {"macro_defined": rep.macro_defined, "macro_all4": rep.macro_all4, "micro_f1": rep.micro["f1"], "samples_f1": rep.samples["f1"], "exact_match": rep.exact_match,
            "per_modality": {m: {k: d[k] for k in ("tp", "fp", "fn", "precision", "recall", "f1", "support")} for m, d in rep.per_modality.items()},
            "matrix_4x4": rep.matrix_4x4, "n_cases": rep.n_cases, "n_empty_predicted": rep.n_empty_predicted, "predicted_set_size_distribution": {str(k): v for k, v in sorted(sizes.items())},
            "gold_differs_from_v1_by_archetype": changed_vs_v1, "n_gold_differs_from_v1": sum(changed_vs_v1.values()),
            "samples_f1_by_archetype": {a: float(np.mean(v)) for a, v in sorted(by_arch.items())},
            "_signature": hashlib.sha256(json.dumps([[pc["gold"], pc["predicted"]] for pc in rep.per_case]).encode()).hexdigest()}


def build_report(runs: tuple[str, ...] = DEFAULT_RUNS, results: Path = RESULTS) -> dict:
    data = {label: load_records(label, results) for label in runs}
    alts = []
    seen: dict[str, dict[str, str]] = {}
    for a in alternatives():
        per_run = {label: _metrics(recs, a["rule"]) for label, (recs, _src) in data.items()}
        sig = "|".join(per_run[l]["_signature"] for l in runs)
        equivalent_to = seen.get(sig)
        seen.setdefault(sig, a["id"])
        for m in per_run.values():
            m.pop("_signature")
        alts.append({"id": a["id"], "family": a["family"], "description": a["description"], "status": "PROVISIONAL", "official": False, "equivalent_to": equivalent_to, "per_run": per_run})
    five = {label: five_class_report(recs) for label, (recs, _src) in data.items()}
    alts.append({"id": "five-class-balanced", "family": "clase «balanceada» (una etiqueta, 5 clases; no es el 4×4)", "status": "PROVISIONAL", "official": False, "equivalent_to": None,
                 "description": "Quinta clase «balanced»; solo para comparar, no cumple la inclusión/exclusión 4×4", "per_run": five})
    return {"report_version": REPORT_VERSION, "metric_version": METRIC_VERSION, "status": "PROVISIONAL", "official": False, "banner": BANNER,
            "source": {label: src for label, (_r, src) in data.items()}, "n_alternatives": len(alts), "alternatives": alts,
            "notes": ["Ninguna alternativa está aprobada (`rubric_v2.APPROVED_RULE_VERSIONS` vacío).",
                      "No se excluye ningún arquetipo: Balanced pertenece al diseño aprobado de n = 100.",
                      "Las corridas históricas usan gold-v1 y modalidad dominante; estos cálculos NO las reemplazan ni las modifican.",
                      "Elegir una regla por su F1 sería una decisión post-hoc: la regla se aprueba antes de la corrida nueva."]}


def to_markdown(rep: dict) -> str:
    L = [f"# Alternativas para el gold de Balanced y la regla de inclusión — {rep['status']}", "", f"> **{rep['banner']}**", ""]
    for label in rep["source"]:
        L += [f"## {label} (sha256 {rep['source'][label]['sha256'][:12]}…, {rep['source'][label]['n_cases']} casos)", "",
              "| alternativa | familia | macro (definido) | micro | por caso | coincidencia exacta | predicho vacío | gold ≠ v1 | equivalente a |", "|---|---|---|---|---|---|---|---|---|"]
        for a in rep["alternatives"]:
            m = a["per_run"][label]
            if "macro_defined" in m:
                f = lambda v: "—" if v is None else f"{v:.3f}"
                L.append(f"| `{a['id']}` | {a['family']} | {f(m['macro_defined'])} | {f(m['micro_f1'])} | {f(m['samples_f1'])} | {f(m['exact_match'])} | {m['n_empty_predicted']} | {m['n_gold_differs_from_v1']} | {a['equivalent_to'] or ''} |")
            else:
                L.append(f"| `{a['id']}` | {a['family']} | {m['macro_f1_defined']:.3f} | — | — | {m['accuracy']:.3f} | — | — | |")
        L.append("")
    L += ["## Cautelas"] + [f"- {n}" for n in rep["notes"]] + [""]
    return "\n".join(L)


def write_report(rep: dict, out_dir: Path) -> Path:
    out = Path(out_dir)
    iso.check_new_output_targets([out / "balanced_alternatives_PROVISIONAL.json", out / "balanced_alternatives_PROVISIONAL.md"])
    out.mkdir(parents=True, exist_ok=False)
    for name, data in (("balanced_alternatives_PROVISIONAL.json", json.dumps(rep, indent=1, sort_keys=True, ensure_ascii=False)), ("balanced_alternatives_PROVISIONAL.md", to_markdown(rep))):
        with (out / name).open("x", encoding="utf-8") as fh:
            fh.write(data)
    return out


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out-dir", required=True, help="directorio NUEVO (fuera de resultados congelados, datasets y paquetes de evidencia)")
    ap.add_argument("--runs", nargs="+", default=list(DEFAULT_RUNS))
    a = ap.parse_args(argv)
    out = iso.require_out_dir(a.out_dir)
    iso.check_new_output_targets([out / "balanced_alternatives_PROVISIONAL.json", out / "balanced_alternatives_PROVISIONAL.md"])
    rep = build_report(tuple(a.runs))
    print(f"{rep['banner']}\ninforme en {write_report(rep, out)}")


if __name__ == "__main__":
    main()
