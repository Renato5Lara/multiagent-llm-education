"""Recorrido E2E real y completo del runtime — un único comando, sin
navegador, contra el stack real (HTTP + PostgreSQL + LangGraph + OpenAI
en las capacidades que lo usan). Cubre las cuatro Plataformas Operativas
cerradas hasta ahora: Runtime del estudiante, Observabilidad (traza,
estado, memoria, replay), HITL (intervención docente + resolución de
escalada).

Requisitos:
  - Servidor real corriendo:
      cd backend && PYTHONPATH=.:runtime uvicorn app.main:app --port 8000
  - PostgreSQL real accesible (mismo que usa el servidor).
  - Usuarios semilla de seed.py ya creados (estudiante3@upao.edu.pe,
    docente@upao.edu.pe) — override con E2E_ESTUDIANTE_EMAIL /
    E2E_DOCENTE_EMAIL si tu seed usa otros.

Uso:
  cd backend && PYTHONPATH=.:runtime python3 e2e/runtime_completo.py

No reemplaza la validación en navegador real (la UI puede tener bugs que
un cliente HTTP no revela) — es el paso previo, rápido y repetible, que
esta suite corre antes de esa validación visual (CLAUDE.md, actualización
2026-07-12 tercera).
"""

from __future__ import annotations

import os
import time
from decimal import Decimal

from e2e.cliente import ClienteE2E, FalloE2E, verificar_servidor_activo

ESTUDIANTE_EMAIL = os.environ.get("E2E_ESTUDIANTE_EMAIL", "estudiante3@upao.edu.pe")
ESTUDIANTE_PASSWORD = os.environ.get("E2E_ESTUDIANTE_PASSWORD", "Student2026!")
DOCENTE_EMAIL = os.environ.get("E2E_DOCENTE_EMAIL", "docente@upao.edu.pe")
DOCENTE_PASSWORD = os.environ.get("E2E_DOCENTE_PASSWORD", "Docente2026!")

_SUFIJO = str(int(time.time()))


def _paso(titulo: str) -> None:
    print(f"\n— {titulo}")


def _ok(mensaje: str) -> None:
    print(f"  ✓ {mensaje}")


def _sembrar_escalada(identidad_json: dict) -> tuple[str, str]:
    """Escalada + tensión sembradas directamente contra los reducers —
    RFC-0006 §4 (disparador orgánico) no está implementado todavía
    (Plataforma Operativa 4, alcance recortado y aprobado); esta es la
    misma técnica ya usada en tests/runtime/boundary/test_E3_resolver_
    escalada.py, real (Postgres real), no un mock de dominio."""
    from runtime.engine.checkpoint import AlmacenTransiciones, encadenar, reconstruir
    from runtime.kernel.reducers import registrar_claim, registrar_deliberacion, registrar_fact
    from runtime.kernel.state.entries import (
        Capacidad,
        Escalada,
        OrigenProvenance,
        Provenance,
        TipoClaim,
    )
    from runtime.kernel.state.state import Identidad, LearningState
    from runtime.kernel.transitions import TransitionIntent

    identidad = Identidad(**identidad_json)
    url = os.environ.get(
        "RUNTIME_DATABASE_URL", "postgresql://upao_user:upao_pass@localhost:5432/upao_mas_edu"
    )
    esquema = os.environ.get("RUNTIME_DATABASE_SCHEMA", "runtime")
    almacen = AlmacenTransiciones(url, esquema=esquema)

    registros = almacen.leer(identidad.session_id)
    estado = (
        reconstruir(identidad, contexto={}, registros=registros)
        if registros
        else LearningState(identidad=identidad, contexto={})
    )

    def aplicar(op: str, args: dict) -> None:
        nonlocal estado, registros
        fn = {
            "registrar_fact": registrar_fact,
            "registrar_claim": registrar_claim,
            "registrar_deliberacion": registrar_deliberacion,
        }[op]
        resultado = fn(estado, **args)
        assert resultado.__class__.__name__ == "Aplicado", resultado
        intent = TransitionIntent(productor="e2e-seed", operacion=op, argumentos=args, base=0)
        registro = encadenar(identidad, registros, {"intent": intent, "eventos": resultado.eventos})
        almacen.persistir(registro)
        registros = registros + (registro,)
        estado = resultado.estado

    aplicar(
        "registrar_fact",
        {
            "autor": Capacidad.EVALUAR,
            "contenido": {"competencia": "COMP-2", "items_incorrectos": [3]},
            "provenance": Provenance.de(OrigenProvenance.INSTRUMENTO, banco="v2"),
        },
    )
    fact_id = estado.facts[-1].id

    aplicar(
        "registrar_claim",
        {
            "autor": Capacidad.DIAGNOSTICAR,
            "tipo": TipoClaim.INTERPRETACION,
            "asunto": "dominio(COMP-2)",
            "afirmacion": {"dominada": False, "errores": 1},
            "respaldo": (fact_id,),
            "confianza": Decimal("0.75"),
            "provenance": Provenance.de(OrigenProvenance.REGLA, id="scoring-v1"),
        },
    )
    interpretacion_id = estado.claims[-1].id

    aplicar(
        "registrar_claim",
        {
            "autor": Capacidad.REMEDIAR,
            "tipo": TipoClaim.PROPUESTA,
            "asunto": "siguiente-paso(sesion)",
            "afirmacion": {"accion": "reforzar"},
            "respaldo": (interpretacion_id,),
            "confianza": Decimal("0.60"),
            "provenance": Provenance.de(OrigenProvenance.REGLA, id="remediacion-v1"),
        },
    )
    remediar_id = estado.claims[-1].id

    aplicar(
        "registrar_claim",
        {
            "autor": Capacidad.ORIENTAR,
            "tipo": TipoClaim.PROPUESTA,
            "asunto": "siguiente-paso(sesion)",
            "afirmacion": {"accion": "avanzar-con-andamiaje"},
            "respaldo": (interpretacion_id,),
            "confianza": Decimal("0.58"),
            "provenance": Provenance.de(OrigenProvenance.REGLA, id="orientacion-v1"),
        },
    )
    orientar_id = estado.claims[-1].id

    aplicar(
        "registrar_deliberacion",
        {
            "participantes": (remediar_id, orientar_id),
            "resultado": Escalada(destinatario="docente"),
        },
    )
    escalada_id = estado.deliberaciones[-1].id
    return str(escalada_id), str(remediar_id)


def main() -> None:
    print("Recorrido E2E — Runtime LangGraph (real, sin mocks)")
    verificar_servidor_activo()
    _ok("servidor activo")

    cliente = ClienteE2E()

    _paso("Estudiante: login")
    estudiante = cliente.login(ESTUDIANTE_EMAIL, ESTUDIANTE_PASSWORD)
    _ok(f"login como {estudiante['email']}")

    _paso("Estudiante: abrir sesión y registrar evidencia")
    session_id = f"e2e-{_SUFIJO}"
    identidad = cliente.abrir_sesion(session_id)
    _ok(f"sesión {session_id} abierta (version_student_model={identidad['version_student_model']})")

    entrega = cliente.registrar_hecho(
        identidad, {"competencia": "COMP-2", "items_incorrectos": [3, 4, 8]}
    )
    assert entrega.get("asunto"), "el walkthrough no llegó a producir una Entrega"
    _ok(f"entrega: {entrega['asunto']}")

    _paso("Observabilidad: traza, estado, replay")
    traza = cliente.traza(session_id)
    assert traza and traza[0]["eventos"][0]["tipo"] == "FactRegistrado"
    _ok(f"traza: {len(traza)} transiciones, T1={traza[0]['eventos'][0]['tipo']}")

    estado = cliente.estado(session_id)
    assert estado["facts"] and estado["claims"]
    _ok(f"estado: {len(estado['facts'])} facts, {len(estado['claims'])} claims")

    replay = cliente.replay(session_id)
    assert len(replay) == len(traza)
    assert replay[-1]["estado"] == estado
    _ok(f"replay: {len(replay)} pasos, último coincide con /estado")

    # Informativo, no una aserción dura: este estudiante semilla es una
    # cuenta real y persistente (no un esquema desechable de test), así
    # que puede arrastrar memoria consolidada de corridas anteriores de
    # este mismo script. La invariante real (memoria = la versión que la
    # sesión tiene fijada) se prueba abajo con sesiones nuevas y aisladas.
    memoria_antes = cliente.memoria(session_id)
    _ok(f"memoria de {session_id}: {'None (N=0)' if memoria_antes is None else memoria_antes['session_id']}")

    _paso("Cerrar sesión y consolidar memoria")
    session_id_2 = f"e2e-{_SUFIJO}-cierre"
    identidad_2 = cliente.abrir_sesion(session_id_2)
    cliente.registrar_hecho(
        identidad_2,
        {"competencia": "COMP-2", "items_incorrectos": [1]},
        cerrar_sesion=True,
    )
    session_id_3 = f"e2e-{_SUFIJO}-siguiente"
    cliente.abrir_sesion(session_id_3)
    memoria_despues = cliente.memoria(session_id_3)
    assert memoria_despues is not None
    assert memoria_despues["session_id"] == session_id_2
    _ok(f"memoria: consolidada por {memoria_despues['session_id']}, leída por la sesión siguiente")

    _paso("Docente: login y lectura de una sesión ajena")
    docente = cliente.login(DOCENTE_EMAIL, DOCENTE_PASSWORD)
    _ok(f"login como {docente['email']}")
    estado_para_docente = cliente.estado(session_id)
    assert estado_para_docente == estado
    _ok("el docente lee /estado de la sesión del estudiante (RFC-0009 §1)")

    _paso("HITL: intervención espontánea del docente")
    cliente.hecho_docente(
        session_id,
        {"competencia": "COMP-2", "items_incorrectos": [7]},
        human_reason="observé confusión persistente en clase",
    )
    traza_tras_docente = cliente.traza(session_id)
    ultimo_paso = traza_tras_docente[-1]
    assert any(e["datos"].get("origen") == "humano" for e in ultimo_paso["eventos"])
    _ok("fact con origen=humano visible en la traza real")

    _paso("HITL: resolución de una escalada real")
    session_id_hitl = f"e2e-{_SUFIJO}-hitl"
    # /sessions (E1) sigue siendo estudiante-only (solo se abrió la
    # lectura para el docente, no la apertura) — reautenticar antes de
    # abrir, luego volver a docente para resolver.
    cliente.login(ESTUDIANTE_EMAIL, ESTUDIANTE_PASSWORD)
    identidad_hitl = cliente.abrir_sesion(session_id_hitl)
    escalada_id, claim_elegido = _sembrar_escalada(identidad_hitl)
    _ok(f"escalada sembrada: {escalada_id} (participante elegido: {claim_elegido})")

    cliente.login(DOCENTE_EMAIL, DOCENTE_PASSWORD)
    cliente.resolver_escalada(
        session_id_hitl, escalada_id, claim_elegido, human_reason="fatiga observada en clase"
    )
    estado_final = cliente.estado(session_id_hitl)
    cierre = next(d for d in estado_final["deliberaciones"] if d.get("enlaza_a") == escalada_id)
    assert cierre["resultado"]["regla"] == "decision-humana"
    assert any(dec["origen"] == cierre["id"] for dec in estado_final["decisiones"])
    _ok("escalada resuelta y decisión derivada — el runtime continuó solo")

    print("\nPASS — recorrido E2E completo (login → HTTP → Postgres → LangGraph → HITL)")


if __name__ == "__main__":
    try:
        main()
    except (AssertionError, FalloE2E) as exc:
        print(f"\nFAIL — {exc}")
        raise SystemExit(1)
