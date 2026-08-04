"""Fase 3 (preparación de `ADR-0016`) — tolerancia de los consumidores
app-level (`module_orchestration_service`, `pedagogy_runtime_bridge`) a
una deliberación real `Aplazada` (RFC-0006 §4 Parte E) llegada por el
Boundary de producto (`runtime_bridge.registrar_evidencia_evaluacion`),
no solo por el motor.

`v1` (δ=0) nunca produce una `Aplazada` real — es estructuralmente
inalcanzable (mismo argumento que
`tests/runtime/walkthrough/test_parteE_walkthrough_aplazamiento.py`).
Este archivo reutiliza EXACTAMENTE esa técnica (política de prueba con
δ=0.99 registrada en `POLITICAS` vía monkeypatch — el mecanismo es
real, la configuración es del test) para forzar la MISMA `Aplazada`
real, pero atravesando `app/services/runtime_bridge.py` y los dos
consumidores reales de `Entrega` que `ADR-0015 §8` dejó como
precondición de `ADR-0016`.

Auditoría previa a este archivo (misma sesión): ambos consumidores ya
manejan `Entrega(asunto=None, diseno=None)` sin romper — los guards
son de Épica 2 (julio), nunca ejercitados contra una `Aplazada` real
hasta este test. Lo que este archivo prueba no es "¿rompe?" (ya se
sabía que no, por inspección estática) sino la consecuencia semántica
exacta: como ambos consumidores leen solo S1 (`Entrega`, la Propuesta
vigente de Adaptar) y nunca S3 (`estado.deliberaciones`), una
`Aplazada` genuina y "sin evidencia todavía" son indistinguibles desde
su punto de vista — ambas producen la misma `Entrega` vacía. Eso no es
un bug de este test: es el límite exacto de lo que S1 puede expresar
hoy, documentado aquí con evidencia real en vez de inferido.
"""

from __future__ import annotations

import os
from decimal import Decimal

import psycopg2
import pytest

from runtime.kernel.deliberation.politica import POLITICAS, Politica
from runtime.kernel.state.entries import Aplazada

_URL = os.environ.get(
    "RUNTIME_TEST_DATABASE_URL",
    "postgresql://upao_user:upao_pass@localhost:5432/upao_mas_edu",
)


def _pg_disponible() -> bool:
    try:
        psycopg2.connect(_URL, connect_timeout=3).close()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _pg_disponible(), reason="PostgreSQL no disponible (ADR-0005 §3 exige BD real)"
)

_VERSION_POLITICA_TEST = "aplazada-consumidores-test"

_POLITICA_DELTA_REAL = Politica(
    peso_refuerzo=Decimal("0"),
    peso_refutacion=Decimal("0"),
    peso_decaimiento=Decimal("0"),
    theta=Decimal("0"),
    # Mismo criterio que test_parteE_walkthrough_aplazamiento.py: ningún
    # margen real entre dos confianzas de regla alcanza 0.99 — garantiza
    # Aplazada, nunca Resuelta.
    delta=Decimal("0.99"),
)


@pytest.fixture
def _politica_de_prueba(monkeypatch):
    """δ=0.99 sintético — garantiza Aplazada en un solo intento,
    determinista (usado por las dos clases que necesitan la Aplazada
    con certeza). No autouse: la clase que ejercita `POLITICAS["v2"]`
    real (ADR-0012) usa su propio fixture, `_politica_v2_real`."""
    monkeypatch.setitem(POLITICAS, _VERSION_POLITICA_TEST, _POLITICA_DELTA_REAL)
    # `runtime_bridge.py` importa `VERSION_POLITICA` por valor
    # (`from ... import`), no por referencia al módulo — hay que
    # parchear el nombre donde vive de verdad (`_peticion()` lo lee de
    # ahí), no en `runtime_connection`.
    monkeypatch.setattr(
        "app.services.runtime_bridge.VERSION_POLITICA", _VERSION_POLITICA_TEST
    )


@pytest.fixture
def _politica_v2_real(monkeypatch):
    """`POLITICAS["v2"]` tal cual la dejó `ADR-0012` (δ=0.10, θ=0.5) —
    la configuración exacta que `ADR-0016` activaría en producción, sin
    registrar nada nuevo. Con δ real, el resultado (`Resuelta` o
    `Aplazada`) depende de la confianza que el LLM real declare en esta
    corrida — `ADR-0015 §8` ya documentó que no siempre aterriza bajo
    el margen (encontró 0.1131, arriba de 0.10); esta prueba acepta
    ambos desenlaces a propósito, no fuerza ninguno."""
    monkeypatch.setattr("app.services.runtime_bridge.VERSION_POLITICA", "v2")


@pytest.fixture(autouse=True)
def _runtime_env(monkeypatch):
    esquema = f"runtime_aplazada_consumidores_{os.getpid()}"
    monkeypatch.setenv("RUNTIME_DATABASE_URL", _URL)
    monkeypatch.setenv("RUNTIME_DATABASE_SCHEMA", esquema)
    from app.services.runtime_connection import almacenes

    almacenes.cache_clear()
    yield
    with psycopg2.connect(_URL) as conexion, conexion.cursor() as cursor:
        cursor.execute(f"DROP SCHEMA IF EXISTS {esquema} CASCADE")
    almacenes.cache_clear()


def _forzar_aplazada_real(student_id: str, course_id: str):
    """Mismo hecho que `test_parteE_walkthrough_aplazamiento._hecho_del_
    mundo` (D2: Remediar vs Orientar sobre "siguiente-paso(sesion)"),
    pero por el Boundary de producto — con δ=0.99 SIEMPRE cae en
    Aplazada, nunca en Resuelta. Devuelve la `Entrega` que el Boundary
    ya devolvió (regla 2 de RFC-0010: nadie oculta el resultado real)."""
    from app.services.runtime_bridge import registrar_evidencia_evaluacion

    return registrar_evidencia_evaluacion(
        student_id=student_id,
        course_id=course_id,
        titulo_modulo="Condicionales",
        items_incorrectos=[3, 4, 8],
    )


def _estado_de(student_id: str, course_id: str):
    """Verifica la Aplazada de verdad (S3), no solo infiere de la
    ausencia de diseño — la misma evidencia que exige la Regla de
    Cierre E2E antes de confiar en un supuesto."""
    from app.services.runtime_bridge import _peticion
    from app.services.runtime_connection import almacenes
    from runtime.boundary import consultar_estado

    almacen, almacen_memoria = almacenes()
    return consultar_estado(_peticion(student_id, course_id), almacen, almacen_memoria)


class TestModuleOrchestrationAntesAplazadaReal:
    def test_no_rompe_y_conserva_el_bloom_configurado(self, _politica_de_prueba):
        from app.models.student_progress import PathModule
        from app.services.module_orchestration_service import (
            _aplicar_modalidad_desde_entrega,
            _bloom_target_desde_entrega,
            _entrega_a_dict,
        )

        student_id, course_id = "s-aplaza-orch", "c-aplaza-orch"
        entrega = _forzar_aplazada_real(student_id, course_id)

        estado = _estado_de(student_id, course_id)
        aplazadas = [d for d in estado.deliberaciones if isinstance(d.resultado, Aplazada)]
        assert len(aplazadas) == 1, "el fixture no forzó una Aplazada real — el test no prueba nada"
        assert estado.decisiones == ()

        # La Aplazada bloqueó antes de que Adaptar corriera: Entrega vacía,
        # el mismo estado que "estudiante sin evidencia todavía" — no un
        # error, el límite exacto de lo que S1 expresa hoy (ver docstring
        # del módulo).
        assert entrega.diseno is None and entrega.asunto is None

        modulo = PathModule(id="m1", path_id="p1", title="Condicionales", bloom_level=5)
        prompts = [{"modality": "image", "prompt": "x", "enabled": True}]

        assert _bloom_target_desde_entrega(modulo, entrega) == 5  # conserva config, no crashea
        assert _aplicar_modalidad_desde_entrega(prompts, modulo, entrega) == prompts
        assert _entrega_a_dict(entrega) is None


class TestPedagogyRuntimeBridgeAntesAplazadaReal:
    def test_estudiante_con_evidencia_real_pero_aplazada_cuenta_como_sin_evidencia(
        self, db, _politica_de_prueba
    ):
        """Documenta la ambigüedad, no la oculta: `sugerir_prioridad_
        semanal` no rompe, pero `estudiantes_con_evidencia` no distingue
        "nunca evaluó" de "evaluó y la deliberación está aplazada" — el
        docente ve el mismo cero en los dos casos. Registrado como
        hallazgo de esta fase (ver mensaje de commit), no corregido
        aquí: distinguirlos exigiría leer S3, no solo S1 — una capacidad
        nueva, no un fix de este alcance."""
        from app.core.security import get_password_hash
        from app.models.course import Course, CourseStatus
        from app.models.enrollment import Enrollment, EnrollmentStatus
        from app.models.user import User, UserRole
        from app.services.pedagogy_runtime_bridge import sugerir_prioridad_semanal

        student_id, course_id = "s-aplaza-ped", "c-aplaza-ped"
        db.add(Course(
            id=course_id, code="CS101", name="Fundamentos", cycle=1, year=2026,
            status=CourseStatus.PUBLICADO,
        ))
        db.add(User(
            id=student_id, email=f"{student_id}@internal.test",
            hashed_password=get_password_hash("Test123!"),
            first_name="Test", last_name="Student", role=UserRole.ESTUDIANTE,
            is_active=True,
        ))
        db.add(Enrollment(
            id="enr-aplaza-ped", course_id=course_id, student_id=student_id,
            status=EnrollmentStatus.ACTIVO,
        ))
        db.commit()

        _forzar_aplazada_real(student_id, course_id)
        estado = _estado_de(student_id, course_id)
        assert any(isinstance(d.resultado, Aplazada) for d in estado.deliberaciones)

        resultado = sugerir_prioridad_semanal(db, course_id)
        assert resultado.estudiantes_totales == 1
        # La ambigüedad real: 0, no 1 — el estudiante SÍ envió evidencia.
        assert resultado.estudiantes_con_evidencia == 0
        assert resultado.competencia_sugerida is None


class TestConsumidoresConVersionPoliticaV2Real:
    """Flip experimental y acotado a este test: `VERSION_POLITICA="v2"`
    (`ADR-0012`, δ=0.10/θ=0.5 reales, sin registrar nada nuevo) — la
    configuración exacta que `ADR-0016` activaría, no una aproximación.
    No fuerza el desenlace (`Resuelta` o `Aplazada`, ambos válidos según
    la confianza real que declare el LLM en esta corrida) — verifica
    que, sea cual sea, ninguno de los dos consumidores rompe y ambos
    reflejan el estado real, sin inventar una decisión que el runtime
    no tomó."""

    def test_flujo_real_con_v2_ninguno_de_los_dos_consumidores_rompe(
        self, db, _politica_v2_real
    ):
        from app.core.security import get_password_hash
        from app.models.course import Course, CourseStatus
        from app.models.enrollment import Enrollment, EnrollmentStatus
        from app.models.student_progress import PathModule
        from app.models.user import User, UserRole
        from app.services.module_orchestration_service import (
            _aplicar_modalidad_desde_entrega,
            _bloom_target_desde_entrega,
            _entrega_a_dict,
        )
        from app.services.pedagogy_runtime_bridge import sugerir_prioridad_semanal
        from runtime.kernel.state.entries import Resuelta

        student_id, course_id = "s-v2-real", "c-v2-real"
        db.add(Course(
            id=course_id, code="CS101", name="Fundamentos", cycle=1, year=2026,
            status=CourseStatus.PUBLICADO,
        ))
        db.add(User(
            id=student_id, email=f"{student_id}@internal.test",
            hashed_password=get_password_hash("Test123!"),
            first_name="Test", last_name="Student", role=UserRole.ESTUDIANTE,
            is_active=True,
        ))
        db.add(Enrollment(
            id="enr-v2-real", course_id=course_id, student_id=student_id,
            status=EnrollmentStatus.ACTIVO,
        ))
        db.commit()

        entrega = _forzar_aplazada_real(student_id, course_id)
        estado = _estado_de(student_id, course_id)
        assert len(estado.deliberaciones) == 1
        resultado = estado.deliberaciones[0].resultado
        assert isinstance(resultado, (Resuelta, Aplazada))  # nunca Escalada aquí (sin urgencia ni reconvocatoria)

        # Cualquiera de los dos desenlaces es evidencia válida — lo que
        # se verifica es que ambos consumidores lo reflejan sin romper
        # ni inventar un tercer estado.
        if isinstance(resultado, Resuelta):
            assert entrega.diseno is not None and entrega.asunto is not None
        else:
            assert entrega.diseno is None and entrega.asunto is None

        modulo = PathModule(id="m1", path_id="p1", title="Condicionales", bloom_level=5)
        prompts = [{"modality": "image", "prompt": "x", "enabled": True}]
        bloom_target = _bloom_target_desde_entrega(modulo, entrega)
        assert 1 <= bloom_target <= 6
        assert _aplicar_modalidad_desde_entrega(prompts, modulo, entrega) is not None
        entrega_dict = _entrega_a_dict(entrega)
        assert entrega_dict is None or isinstance(entrega_dict, dict)

        sugerencia = sugerir_prioridad_semanal(db, course_id)
        assert sugerencia.estudiantes_totales == 1
        # Con Resuelta, la evidencia SÍ se cuenta; con Aplazada, no —
        # misma ambigüedad ya documentada arriba, ahora bajo v2 real.
        assert sugerencia.estudiantes_con_evidencia == (
            1 if isinstance(resultado, Resuelta) else 0
        )
