"""Tests de P2 — persistencia experimental. Usa la BD SQLite en memoria
compartida de `tests/conftest.py` (fixture `db`) — no requiere Postgres.
`ExperimentCMGResult` se importa aquí para registrarse en `Base.metadata`
antes de que el fixture llame `create_all()` (mismo patrón que
`EventOutbox`/`SharedMemoryRecord` en `conftest.py`)."""

from __future__ import annotations

import inspect

import pytest

from app.models.concept import Concept
from app.models.course import Course
from app.models.experiment_cmg_result import ExperimentCMGResult  # noqa: F401
from app.models.learning_objective import LearningObjective
from app.services.cmg_evaluation_service import D1Resultado, D2Resultado, D3Resultado, EvaluacionCMG, evaluar_cmg
from app.services.cmg_experiment_repository import RUN_LABELS_VALIDOS, persistir_resultado
from app.services.cmg_generation_service import CMG, CONTROL_CONFIG, EjercicioEstructurado, GenerationConfig, generar_cmg


def _sembrar_curriculo(db) -> tuple[Concept, LearningObjective]:
    curso = Course(id="course-1", code="IS301", name="Fundamentos de la Programación", cycle=1, year=2026)
    objetivo = LearningObjective(id="lo-1", course_id="course-1", title="Bucles", bloom_level=3, order=5)
    concepto = Concept(id="c-1", title="Bucle while", learning_objective_id="lo-1", order=1)
    db.add_all([curso, objetivo, concepto])
    db.commit()
    return concepto, objetivo


def _cmg(config: GenerationConfig) -> CMG:
    return CMG(
        concept_id="c-1", concept_title="Bucle while", learning_objective_id="lo-1",
        bloom_target=3, modalidad=config.modalidad, profundidad=config.profundidad,
        explanation="texto", explanation_source="template",
        code="def f(): return 1", code_source="catalog-v1", tests="assert f() == 1",
        exercise=EjercicioEstructurado("t", "p", "e", 3, ()),
        diagram_mermaid="flowchart LR\nA-->B", diagram_valid=True,
        multimodal_prompts=(), generated_at="2026-09-22T00:00:00+00:00",
    )


def _evaluacion() -> EvaluacionCMG:
    return EvaluacionCMG(
        d1=D1Resultado("checklist-v1", True, True, True, ()),
        d2=D2Resultado("sandbox-v1", True, "success", True, "", ""),
        d3=D3Resultado("checklist-v1", True, True, True, True, ()),
    )


class TestPersistencia:
    def test_persiste_resultado_experimental_y_control_distinguibles(self, db):
        _sembrar_curriculo(db)
        config_exp = GenerationConfig(modalidad="visual", profundidad="fundamentos")

        fila_exp = persistir_resultado(
            db, condition="experimental", configuration_source="multiagent_runtime",
            configuration=config_exp, cmg=_cmg(config_exp), evaluacion=_evaluacion(),
            traceability={"dominada": False, "urgente": True, "margen": "0.07"},
            run_label="pilot_1",
        )
        fila_ctrl = persistir_resultado(
            db, condition="control", configuration_source="fixed_control",
            configuration=CONTROL_CONFIG, cmg=_cmg(CONTROL_CONFIG), evaluacion=_evaluacion(),
            traceability={},
            run_label="pilot_1",
        )
        db.commit()

        filas = db.query(ExperimentCMGResult).filter(ExperimentCMGResult.concept_id == "c-1").all()
        assert len(filas) == 2
        condiciones = {f.condition for f in filas}
        assert condiciones == {"experimental", "control"}

        exp_db = db.query(ExperimentCMGResult).get(fila_exp.id)
        assert exp_db.configuration == {"modalidad": "visual", "profundidad": "fundamentos"}
        assert exp_db.traceability["dominada"] is False
        assert exp_db.d1["passed"] is True
        assert exp_db.run_label == "pilot_1"

        ctrl_db = db.query(ExperimentCMGResult).get(fila_ctrl.id)
        assert ctrl_db.configuration == {"modalidad": "mixta", "profundidad": "aplicacion"}
        assert ctrl_db.traceability == {}  # §19: el control no ejecuta el runtime — sin traza
        assert ctrl_db.run_label == "pilot_1"


class TestRunLabel:
    """R28/R29 — `run_label` es metadato de trazabilidad de oleada,
    ortogonal a VI/VD/condición. Estos tests demuestran que no se
    filtra a ningún componente de dominio."""

    def test_run_label_obligatorio(self, db):
        _sembrar_curriculo(db)
        config = GenerationConfig(modalidad="visual", profundidad="fundamentos")
        with pytest.raises(TypeError):
            persistir_resultado(  # type: ignore[call-arg]
                db, condition="experimental", configuration_source="multiagent_runtime",
                configuration=config, cmg=_cmg(config), evaluacion=_evaluacion(),
                traceability={},
            )

    @pytest.mark.parametrize("run_label", sorted(RUN_LABELS_VALIDOS))
    def test_valores_validos(self, db, run_label):
        _sembrar_curriculo(db)
        config = GenerationConfig(modalidad="visual", profundidad="fundamentos")
        fila = persistir_resultado(
            db, condition="experimental", configuration_source="multiagent_runtime",
            configuration=config, cmg=_cmg(config), evaluacion=_evaluacion(),
            traceability={}, run_label=run_label,
        )
        db.commit()
        assert db.query(ExperimentCMGResult).get(fila.id).run_label == run_label

    def test_valor_invalido_rechazado(self, db):
        _sembrar_curriculo(db)
        config = GenerationConfig(modalidad="visual", profundidad="fundamentos")
        with pytest.raises(ValueError):
            persistir_resultado(
                db, condition="experimental", configuration_source="multiagent_runtime",
                configuration=config, cmg=_cmg(config), evaluacion=_evaluacion(),
                traceability={}, run_label="corrida_3",  # type: ignore[arg-type]
            )

    @pytest.mark.parametrize("run_label", sorted(RUN_LABELS_VALIDOS))
    def test_run_label_no_afecta_d1_d2_d3(self, db, run_label):
        _sembrar_curriculo(db)
        config = GenerationConfig(modalidad="visual", profundidad="fundamentos")
        evaluacion = _evaluacion()
        fila = persistir_resultado(
            db, condition="experimental", configuration_source="multiagent_runtime",
            configuration=config, cmg=_cmg(config), evaluacion=evaluacion,
            traceability={}, run_label=run_label,
        )
        db.commit()
        fila_db = db.query(ExperimentCMGResult).get(fila.id)
        assert fila_db.d1 == evaluacion.d1.to_dict()
        assert fila_db.d2 == evaluacion.d2.to_dict()
        assert fila_db.d3 == evaluacion.d3.to_dict()

    @pytest.mark.parametrize("run_label", sorted(RUN_LABELS_VALIDOS))
    def test_run_label_no_entra_a_configuration_ni_cambia_cmg(self, db, run_label):
        _sembrar_curriculo(db)
        config = GenerationConfig(modalidad="visual", profundidad="fundamentos")
        cmg = _cmg(config)
        fila = persistir_resultado(
            db, condition="experimental", configuration_source="multiagent_runtime",
            configuration=config, cmg=cmg, evaluacion=_evaluacion(),
            traceability={}, run_label=run_label,
        )
        db.commit()
        fila_db = db.query(ExperimentCMGResult).get(fila.id)
        assert "run_label" not in fila_db.configuration
        assert fila_db.cmg == cmg.to_dict()
        assert "run_label" not in fila_db.cmg

    def test_run_label_no_entra_al_evaluador_ni_al_generador(self):
        assert "run_label" not in inspect.signature(evaluar_cmg).parameters
        assert "run_label" not in inspect.signature(generar_cmg).parameters

    def test_run_label_no_crea_tercera_condicion(self, db):
        _sembrar_curriculo(db)
        config = GenerationConfig(modalidad="visual", profundidad="fundamentos")
        for run_label in sorted(RUN_LABELS_VALIDOS):
            persistir_resultado(
                db, condition="experimental", configuration_source="multiagent_runtime",
                configuration=config, cmg=_cmg(config), evaluacion=_evaluacion(),
                traceability={}, run_label=run_label,
            )
        db.commit()
        condiciones = {f.condition for f in db.query(ExperimentCMGResult).all()}
        assert condiciones == {"experimental"}  # nunca aparece un tercer valor derivado de run_label
