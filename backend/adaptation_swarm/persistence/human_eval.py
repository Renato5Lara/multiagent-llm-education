"""Registro de participantes, respuestas SUS y valoraciones del panel (validaciones de entrada estrictas). NO inserta
datos por sí mismo: solo lo hace cuando una persona real aporta respuestas (CSV/CLI)."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from sqlalchemy import select

from app.models.swarm_human_evaluation import GoldPanelArchetypeRating, GoldPanelRating, SusParticipant, SusResponse

from adaptation_swarm.gold.rubric import GOLD_TABLE, RULE_VERSION
from adaptation_swarm.gold.rubric_v2 import PANEL_PROTOCOL_VERSION, get_rule, official_version
from adaptation_swarm.metrics.gold_panel import ARCHETYPES, EXPECTED_SETS, analyze_archetype_panel
from adaptation_swarm.metrics.sus import analyze_gold_panel, analyze_sus, study_status, sus_score

ROLES = ("docente_programacion", "ingeniero_software")
INSTRUMENT_VERSION = "sus-brooke-1996-es"
TASK_SCRIPT_VERSION = "task-script-v1"
# Versión OFICIAL de gold-v2 (gold + inclusión + agregación + protocolo del panel) cuyo gold valida el panel por arquetipo. Registrar el juicio NO aprueba la regla.
PANEL_RULE_VERSION = official_version(get_rule("gold-v2-cand-A", "incl-ge1"))
HISTORIC_PANEL_LABEL = "[HISTÓRICO gold-v1 - NO OFICIAL]"


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

    def add_archetype_rating(self, pseudonym: str, archetype: str, approves: bool, comment: str | None = None, *, rule_version: str = PANEL_RULE_VERSION) -> None:
        with self._sf() as s:
            s.add(self._archetype_row(s, pseudonym, archetype, approves, comment, rule_version))
            s.commit()

    @staticmethod
    def _archetype_row(session, pseudonym: str, archetype: str, approves: bool, comment: str | None, rule_version: str) -> GoldPanelArchetypeRating:
        if archetype not in ARCHETYPES:
            raise ValueError(f"arquetipo inexistente: {archetype!r}; válidos: {ARCHETYPES}")
        part = session.scalars(select(SusParticipant).where(SusParticipant.pseudonym == pseudonym)).one()
        return GoldPanelArchetypeRating(participant_id=part.id, rule_version=rule_version, archetype=archetype, approves=bool(approves), comment=comment)

    def archetype_votes(self, rule_version: str = PANEL_RULE_VERSION) -> dict[str, list[bool]]:
        votes: dict[str, list[bool]] = {a: [] for a in ARCHETYPES}
        with self._sf() as s:
            for r in s.scalars(select(GoldPanelArchetypeRating).where(GoldPanelArchetypeRating.rule_version == rule_version)):
                votes[r.archetype].append(r.approves)
        return votes

    def archetype_votes_by_evaluator(self, rule_version: str = PANEL_RULE_VERSION) -> list[dict]:
        """Voto de cada evaluador por arquetipo (seudónimo, arquetipo, aprueba), en orden estable: permite reconstruir la matriz absoluta y todos los estadísticos."""
        with self._sf() as s:
            rows = [(s.get(SusParticipant, r.participant_id).pseudonym, r.archetype, bool(r.approves)) for r in
                    s.scalars(select(GoldPanelArchetypeRating).where(GoldPanelArchetypeRating.rule_version == rule_version))]
        order = {a: i for i, a in enumerate(ARCHETYPES)}
        return [{"pseudonym": p, "archetype": a, "approves": v} for p, a, v in sorted(rows, key=lambda x: (order[x[1]], x[0]))]

    def archetype_panel_result(self, rule_version: str = PANEL_RULE_VERSION) -> dict:
        """Resultado del panel por arquetipo (AC1, acuerdo crudo, matriz absoluta, aprobación por arquetipo, decisión) más los votos individuales que lo sustentan."""
        votes = self.archetype_votes(rule_version)
        return {**analyze_archetype_panel(votes, rule_version), "votes_by_evaluator": self.archetype_votes_by_evaluator(rule_version)}

    def export_archetype_panel(self, out_dir: Path, rule_version: str = PANEL_RULE_VERSION) -> Path:
        """Exporta a un directorio NUEVO: `archetype_panel_result.json` (resultado completo), `archetype_votes_matrix.csv` (matriz absoluta) y `archetype_votes_by_evaluator.csv`."""
        result = self.archetype_panel_result(rule_version)
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=False)
        with (out / "archetype_panel_result.json").open("x", encoding="utf-8") as fh:
            fh.write(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True) + "\n")
        if "votes_matrix" in result:
            with (out / "archetype_votes_matrix.csv").open("x", newline="", encoding="utf-8") as fh:
                w = csv.writer(fh)
                w.writerow(["archetype", "approve", "reject", "total", "approval_rate", "majority_status"])
                for r in result["votes_matrix"]:
                    w.writerow([r["archetype"], r["approve"], r["reject"], r["total"], f"{r['approval_rate']:.4f}", r["majority_status"]])
        with (out / "archetype_votes_by_evaluator.csv").open("x", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["pseudonym", "archetype", "approves"])
            for r in result["votes_by_evaluator"]:
                w.writerow([r["pseudonym"], r["archetype"], "yes" if r["approves"] else "no"])
        return out

    def import_archetype_csv(self, src: Path) -> int:
        """Importa juicios del panel por arquetipo (plantilla `gold_panel_archetype_template.csv`); el participante ya debe existir. Todo o nada: valida antes de insertar e inserta en UNA transacción.
        Si `expected_set_shown` viene informado debe coincidir con el conjunto esperado del arquetipo (protege contra una plantilla desalineada)."""
        rows = []
        with src.open(newline="", encoding="utf-8") as fh:
            for n, r in enumerate(csv.DictReader(fh), start=2):
                if not (r.get("pseudonym") or "").strip() and not (r.get("approves") or "").strip():
                    continue
                approves = (r.get("approves") or "").strip().lower()
                if approves not in {"yes", "no"} or not (r.get("pseudonym") or "").strip():
                    raise ValueError(f"fila {n}: `pseudonym` y `approves` (yes/no) son obligatorios")
                arch = (r.get("archetype") or "").strip()
                if arch not in ARCHETYPES:
                    raise ValueError(f"fila {n}: arquetipo inexistente {arch!r}")
                shown = (r.get("expected_set_shown") or "").strip()
                if shown and shown != "+".join(EXPECTED_SETS[arch]):
                    raise ValueError(f"fila {n}: `expected_set_shown` {shown!r} no coincide con el conjunto esperado de {arch}")
                rows.append((r["pseudonym"].strip(), arch, approves == "yes", (r.get("comment") or "").strip() or None))
        with self._sf() as s:                      # UNA transacción: cualquier error ⇒ rollback completo
            try:
                for pseud, arch, approves, comment in rows:
                    s.add(self._archetype_row(s, pseud, arch, approves, comment, PANEL_RULE_VERSION))
                    s.flush()
                s.commit()
            except Exception:
                s.rollback()
                raise
        return len(rows)

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
                "sus": analyze_sus(scores).to_dict(),
                # Protocolo OFICIAL vigente (gold-v2): 4 arquetipos, Gwet AC1 único estadístico, mayoría aprobatoria, empate = rechazo.
                "archetype_panel": {**analyze_archetype_panel(self.archetype_votes(), PANEL_RULE_VERSION), "official": True, "protocol": PANEL_PROTOCOL_VERSION},
                # Panel HISTÓRICO de gold-v1 (20 celdas, Fleiss κ): se conserva como evidencia, NO es parte del protocolo oficial. Sus cálculos no cambian; solo se rotula.
                "gold_panel": {**analyze_gold_panel(self.gold_votes()), "official": False, "label": HISTORIC_PANEL_LABEL,
                               "protocol": "gold-v1 (20 celdas arquetipo×dificultad, Fleiss κ)"}}

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
