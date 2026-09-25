"""Alinea los `concepts.id` de una base NUEVA con los del dataset del PoC.

La migración de datos `d6e7f8a9b0c1` genera los 32 UUID de `concepts` al ejecutarse, así que dos bases construidas desde
cero no comparten ids; el dataset sintético y la biblioteca M1 referencian los ids de la base de referencia. Este
comando exporta (`export`) o restaura (`restore`) el mapa título→id (`datasets/synthetic_profiles/concepts-v1.json`).

    python -m adaptation_swarm.tools.concept_ids export     # desde la base de referencia
    DATABASE_URL=... python -m adaptation_swarm.tools.concept_ids restore   # en una base nueva (tras alembic upgrade head)
"""

import json
import sys
from pathlib import Path

from sqlalchemy import text

from app.db.session import SessionLocal

MAP = Path(__file__).resolve().parents[3] / "datasets" / "synthetic_profiles" / "concepts-v1.json"
_FK_TABLES = ("experiment_cmg_results",)      # tablas con FK a concepts.id (vacías en una base nueva)


def export() -> int:
    with SessionLocal() as s:
        rows = s.execute(text("select c.id, c.title, lo.title, c.\"order\" from concepts c join learning_objectives lo "
                              "on lo.id = c.learning_objective_id order by lo.\"order\", c.\"order\"")).all()
    MAP.write_text(json.dumps([{"id": r[0], "title": r[1], "module": r[2], "order": r[3]} for r in rows],
                              ensure_ascii=False, indent=1), encoding="utf-8")
    return len(rows)


def restore() -> int:
    wanted = {(c["module"], c["title"]): c["id"] for c in json.loads(MAP.read_text(encoding="utf-8"))}
    n = 0
    with SessionLocal() as s:
        for t in _FK_TABLES:
            if s.execute(text(f"select count(*) from {t}")).scalar():
                raise SystemExit(f"{t} no está vacía: no se pueden reasignar ids de forma segura")
        current = s.execute(text("select c.id, c.title, lo.title from concepts c join learning_objectives lo "
                                 "on lo.id = c.learning_objective_id")).all()
        if len(current) != len(wanted):
            raise SystemExit(f"la base tiene {len(current)} conceptos, el mapa {len(wanted)}")
        for cid, title, module in current:
            new = wanted.get((module, title))
            if new is None:
                raise SystemExit(f"concepto sin correspondencia: {module} / {title}")
            if new != cid:
                s.execute(text("update concepts set id = :n where id = :o"), {"n": new, "o": cid})
                n += 1
        s.commit()
    return n


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "export":
        print(f"{export()} conceptos exportados a {MAP}")
    elif cmd == "restore":
        print(f"{restore()} ids reasignados")
    else:
        raise SystemExit(__doc__)
