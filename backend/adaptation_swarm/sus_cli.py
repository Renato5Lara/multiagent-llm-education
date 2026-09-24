"""CLI de evaluación humana. Uso (desde backend/):
    python -m adaptation_swarm.sus_cli status
    python -m adaptation_swarm.sus_cli add-participant --pseudonym E01 --role docente_programacion --years 8 --consent
    python -m adaptation_swarm.sus_cli add-sus --pseudonym E01 --items 4 2 5 1 4 2 5 1 4 2
    python -m adaptation_swarm.sus_cli add-gold --pseudonym E01 --archetype visual_dominant --difficulty repetitive --agrees yes
    python -m adaptation_swarm.sus_cli import-sus --csv respuestas.csv      # plantilla human_eval/templates/sus_responses_template.csv
    python -m adaptation_swarm.sus_cli import-gold --csv panel.csv          # plantilla human_eval/templates/gold_panel_template.csv
    python -m adaptation_swarm.sus_cli export --out sus_respuestas.csv
`status` muestra «PENDIENTE DE RECOLECCIÓN HUMANA» mientras haya menos de 10 evaluadores reales."""

import argparse
import json
from pathlib import Path

from app.db.session import SessionLocal

from adaptation_swarm.persistence.human_eval import HumanEvalRepository


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status")
    p = sub.add_parser("add-participant"); p.add_argument("--pseudonym", required=True); p.add_argument("--role", required=True)
    p.add_argument("--years", type=int); p.add_argument("--consent", action="store_true")
    p = sub.add_parser("add-sus"); p.add_argument("--pseudonym", required=True); p.add_argument("--items", type=int, nargs=10, required=True)
    p = sub.add_parser("add-gold"); p.add_argument("--pseudonym", required=True); p.add_argument("--archetype", required=True)
    p.add_argument("--difficulty", required=True); p.add_argument("--agrees", choices=["yes", "no"], required=True)
    p.add_argument("--rating", type=int); p.add_argument("--comment")
    for name in ("import-sus", "import-gold"):
        p = sub.add_parser(name); p.add_argument("--csv", required=True)
    p = sub.add_parser("export"); p.add_argument("--out", required=True)
    a = ap.parse_args()
    repo = HumanEvalRepository(SessionLocal)
    if a.cmd == "status":
        print(json.dumps(repo.status_report(), indent=2, ensure_ascii=False))
    elif a.cmd == "add-participant":
        print(repo.register_participant(a.pseudonym, a.role, a.consent, a.years))
    elif a.cmd == "add-sus":
        print(f"SUS = {repo.add_sus_response(a.pseudonym, a.items)}")
    elif a.cmd == "add-gold":
        repo.add_gold_rating(a.pseudonym, a.archetype, a.difficulty, a.agrees == "yes", a.rating, a.comment)
    elif a.cmd == "import-sus":
        print(f"{repo.import_sus_csv(Path(a.csv))} respuestas SUS importadas")
    elif a.cmd == "import-gold":
        print(f"{repo.import_gold_csv(Path(a.csv))} valoraciones del panel importadas")
    elif a.cmd == "export":
        print(repo.export_csv(Path(a.out)))


if __name__ == "__main__":
    main()
