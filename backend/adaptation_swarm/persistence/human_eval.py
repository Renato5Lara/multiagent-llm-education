"""Registro de participantes, respuestas SUS y valoraciones del panel (validaciones de entrada estrictas). NO inserta
datos por sí mismo: solo lo hace cuando una persona real aporta respuestas (CSV/CLI)."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from sqlalchemy import select

from app.models.swarm_human_evaluation import GoldPanelRating, SusParticipant, SusResponse

from adaptation_swarm.gold.rubric import GOLD_TABLE, RULE_VERSION
from adaptation_swarm.metrics.sus import analyze_gold_panel, analyze_sus, study_status, sus_score

ROLES = ("docente_programacion", "ingeniero_software")
INSTRUMENT_VERSION = "sus-brooke-1996-es"
TASK_SCRIPT_VERSION = "task-script-v1"


class HumanEvalRepository:
    def __init__(self, session_factory):
        self._sf = session_factory

    @staticmethod
    def _validated_participant(pseudonym: str, role: str, consent: bool, years_experience: int | None) -> SusParticipant:
        if not consent:
            raise ValueError("sin consentimiento no se registra al participante")
        if not pseudonym or "@" in pseudonym or " " in pseudonym.strip():
            raise ValueError("usar un seudónimo (sin nombre, espacios ni correo)")
        return SusParticipant(pseudonym=pseudonym, role=role, consent=True, years_experience=years_experience)

    @staticmethod
    def _sus_row(session, pseudonym: str, items: list[int], instrument_version: str, task_script_version: str) -> tuple[SusResponse, float]:
        score = sus_score(items)
        part = session.scalars(select(SusParticipant).where(SusParticipant.pseudonym == pseudonym)).one()
        return SusResponse(participant_id=part.id, instrument_version=instrument_version, task_script_version=task_script_version,
                           score=int(round(score * 2)), **{f"item_{i + 1}": int(v) for i, v in enumerate(items)}), score

    @staticmethod
    def _gold_row(session, pseudonym: str, archetype: str, difficulty: str, agrees: bool, rating: int | None,
                  comment: str | None) -> GoldPanelRating:
        if not any(a.value == archetype and d.value == difficulty for (a, d) in GOLD_TABLE):
            raise ValueError("celda (arquetipo, dificultad) inexistente en la tabla gold")
        part = session.scalars(select(SusParticipant).where(SusParticipant.pseudonym == pseudonym)).one()
        return GoldPanelRating(participant_id=part.id, rule_version=RULE_VERSION, archetype=archetype, difficulty=difficulty,
                               agrees=agrees, rating=rating, comment=comment)

    def register_participant(self, pseudonym: str, role: str, consent: bool, years_experience: int | None = None) -> str:
        participant = self._validated_participant(pseudonym, role, consent, years_experience)
        with self._sf() as s:
            s.add(participant)
            s.commit()
            return participant.id

    def add_sus_response(self, pseudonym: str, items: list[int], *, instrument_version: str = INSTRUMENT_VERSION,
                         task_script_version: str = TASK_SCRIPT_VERSION) -> float:
        with self._sf() as s:
            row, score = self._sus_row(s, pseudonym, items, instrument_version, task_script_version)
            s.add(row)
            s.commit()
        return score

    def add_gold_rating(self, pseudonym: str, archetype: str, difficulty: str, agrees: bool, rating: int | None = None,
                        comment: str | None = None) -> None:
        with self._sf() as s:
            s.add(self._gold_row(s, pseudonym, archetype, difficulty, agrees, rating, comment))
            s.commit()

    def sus_scores(self) -> list[float]:
        with self._sf() as s:
            return [r.score / 2.0 for r in s.scalars(select(SusResponse))]

    def gold_votes(self) -> dict[tuple[str, str], list[bool]]:
        votes: dict[tuple[str, str], list[bool]] = {}
        with self._sf() as s:
            for r in s.scalars(select(GoldPanelRating).where(GoldPanelRating.rule_version == RULE_VERSION)):
                votes.setdefault((r.archetype, r.difficulty), []).append(r.agrees)
        return votes

    def status_report(self) -> dict[str, Any]:
        with self._sf() as s:
            n_part = len(list(s.scalars(select(SusParticipant.id))))
        scores = self.sus_scores()
        return {"participants": n_part, "sus_responses": len(scores), "sus_status": study_status(len(scores)),
                "sus": analyze_sus(scores).to_dict(), "gold_panel": analyze_gold_panel(self.gold_votes())}

    def import_sus_csv(self, src: Path) -> int:
        """Importa participantes + respuestas SUS desde la plantilla. Todo o nada: valida todas las filas antes de insertar
        e inserta en UNA transacción (rollback completo ante cualquier error).
        Las filas totalmente vacías (plantilla sin rellenar) se ignoran; una fila incompleta aborta la importación."""
        rows = []
        with src.open(newline="", encoding="utf-8") as fh:
            for n, r in enumerate(csv.DictReader(fh), start=2):
                if not any((v or "").strip() for v in r.values()):
                    continue
                consent = (r.get("consent") or "").strip().lower() in {"1", "true", "yes", "si", "sí"}
                try:
                    items = [int(r[f"item_{i}"]) for i in range(1, 11)]
                    years = int(r["years_experience"]) if (r.get("years_experience") or "").strip() else None
                    sus_score(items)
                except (ValueError, KeyError, TypeError) as e:
                    raise ValueError(f"fila {n}: {e}") from e
                if not consent or not (r.get("pseudonym") or "").strip():
                    raise ValueError(f"fila {n}: faltan el seudónimo o el consentimiento")
                if (r.get("role") or "").strip() not in ROLES:
                    raise ValueError(f"fila {n}: rol debe ser uno de {ROLES}")
                rows.append((r["pseudonym"].strip(), r["role"].strip(), years, items))
        with self._sf() as s:                      # UNA transacción: cualquier error ⇒ rollback completo
            try:
                for pseud, role, years, items in rows:
                    s.add(self._validated_participant(pseud, role, True, years))
                    s.flush()                  # el participante debe existir para enlazar su respuesta
                    response, _ = self._sus_row(s, pseud, items, INSTRUMENT_VERSION, TASK_SCRIPT_VERSION)
                    s.add(response)
                    s.flush()                  # fuerza aquí las violaciones de unicidad/CHECK
                s.commit()
            except Exception:
                s.rollback()
                raise
        return len(rows)

    def import_gold_csv(self, src: Path) -> int:
        """Importa valoraciones del panel (plantilla `gold_panel_template.csv`); el participante ya debe existir.
        Misma garantía: validación previa completa e inserción en UNA transacción (rollback completo ante cualquier error)."""
        rows = []
        with src.open(newline="", encoding="utf-8") as fh:
            for n, r in enumerate(csv.DictReader(fh), start=2):
                if not (r.get("pseudonym") or "").strip() and not (r.get("agrees") or "").strip():
                    continue
                agrees = (r.get("agrees") or "").strip().lower()
                if agrees not in {"yes", "no"} or not (r.get("pseudonym") or "").strip():
                    raise ValueError(f"fila {n}: `pseudonym` y `agrees` (yes/no) son obligatorios")
                rating = int(r["rating"]) if (r.get("rating") or "").strip() else None
                if rating is not None and not 1 <= rating <= 5:
                    raise ValueError(f"fila {n}: rating fuera de 1–5")
                rows.append((r["pseudonym"].strip(), r["archetype"], r["difficulty"], agrees == "yes", rating, (r.get("comment") or "").strip() or None))
        with self._sf() as s:                      # UNA transacción: cualquier error ⇒ rollback completo
            try:
                for row in rows:
                    s.add(self._gold_row(s, *row))
                    s.flush()
                s.commit()
            except Exception:
                s.rollback()
                raise
        return len(rows)

    def export_csv(self, out: Path) -> Path:
        with self._sf() as s, out.open("w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["pseudonym", "role", "years_experience"] + [f"item_{i}" for i in range(1, 11)] + ["sus_score"])
            for r in s.scalars(select(SusResponse)):
                p = s.get(SusParticipant, r.participant_id)
                w.writerow([p.pseudonym, p.role, p.years_experience] + [getattr(r, f"item_{i}") for i in range(1, 11)] + [r.score / 2.0])
        return out
