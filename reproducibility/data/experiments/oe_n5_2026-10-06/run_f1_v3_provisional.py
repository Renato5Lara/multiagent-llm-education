"""OE5 — precisión de la adaptación: F1_adapt con la definición v3 (4×4 con audio, agregación `samples`, K = 10, semilla maestra de K = 10, 100 perfiles, biblioteca vigente).
Ejecución PROVISIONAL: la regla v3 NO está aprobada/sellada (APPROVED_RULE_VERSIONS vacío), por eso no es oficial y no declara RNF-03. No mezcla resultados con K = 10 v2.
Uso (desde backend/, con el entorno de pruebas aislado): ../.venv/Scripts/python.exe experiments/oe_n5_2026-10-06/run_f1_v3_provisional.py"""
from __future__ import annotations

import json
from pathlib import Path

from adaptation_swarm.analysis import evaluation_v3 as ev3
from adaptation_swarm.analysis import replicas_v3 as rp3
from adaptation_swarm.gold import rubric_v3

HERE = Path(__file__).parent
LIBRARY_VERSION = "lib-v10-5dd83cd4"                       # la misma biblioteca de OE1–OE4 (N1–N4)
rule = rubric_v3.get_rule(rubric_v3.GOLD_RULE_VERSION, rubric_v3.INCLUSION_RULE_ID)     # única regla v3 registrada: gold-v3-multimodal + incl-rel20
plan = rp3.build_plan_v3(master_seed=rp3.K10_MASTER_SEED, k=rp3.K_OFFICIAL, library_version=LIBRARY_VERSION, rule=rule)    # PROVISIONAL (official=False)
assert plan["status"] == "PROVISIONAL"
out = HERE / "f1_v3_provisional"
print(json.dumps(rp3.run_replicas_v3(plan, out), default=str)[:400])
evaluation = ev3.evaluate_dir_v3(out, official=False)
(HERE / "f1_v3_provisional_evaluation.json").write_text(json.dumps(evaluation, indent=1, sort_keys=True, default=str), encoding="utf-8")
print(list(evaluation.keys()))
