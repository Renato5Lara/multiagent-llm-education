"""Recorrido E2E real y completo del runtime — un único comando, sin
navegador, contra el stack real (HTTP + PostgreSQL + LangGraph + OpenAI
en las capacidades que lo usan). Cubre las cuatro Plataformas Operativas
cerradas hasta ahora: Runtime del estudiante, Boundary, Observabilidad
(traza, estado, memoria, replay), HITL (intervención docente +
resolución de escalada).

Requisitos:
  - Servidor real corriendo:
      cd backend && PYTHONPATH=.:runtime uvicorn app.main:app --port 8000
  - PostgreSQL real accesible (mismo que usa el servidor).
  - Usuarios semilla de seed.py ya creados (estudiante3@upao.edu.pe,
    docente@upao.edu.pe) — override con E2E_ESTUDIANTE_EMAIL /
    E2E_DOCENTE_EMAIL si tu seed usa otros.

Uso:
  cd backend && PYTHONPATH=.:runtime python3 e2e/runtime_completo.py
  cd backend && PYTHONPATH=.:runtime python3 e2e/runtime_completo.py --only replay
  cd backend && PYTHONPATH=.:runtime python3 e2e/runtime_completo.py --only hitl

`--only <categoria>` corre la cadena de categorías previas necesarias
(comparten estado — Replay necesita lo que Boundary/Observabilidad ya
dejaron listo) y se detiene después de la pedida: no es aislamiento
verdadero, es "validar hasta aquí" sin correr el resto.

Cada categoría corre de forma independiente: si una falla, las
siguientes igual se intentan (y probablemente fallen en cascada de forma
informativa — nunca se ocultan). El resumen final (estilo de proyectos
grandes: Kubernetes, Temporal, CockroachDB) es la referencia rápida del
estado de la plataforma, con una métrica corta por categoría — solo lo
que el propio paso ya medía (conteos, duración), nunca un número
inventado; el detalle completo de cada paso queda arriba, impreso en
vivo.

No reemplaza la validación en navegador real (la UI puede tener bugs que
un cliente HTTP no revela) — es el paso previo, rápido y repetible, que
esta suite corre antes de esa validación visual (CLAUDE.md, actualización
2026-07-12 tercera).
"""

from __future__ import annotations

import argparse
import os
import time
from decimal import Decimal
from typing import Any

from e2e.cliente import ClienteE2E, verificar_servidor_activo

ESTUDIANTE_EMAIL = os.environ.get("E2E_ESTUDIANTE_EMAIL", "estudiante3@upao.edu.pe")
ESTUDIANTE_PASSWORD = os.environ.get("E2E_ESTUDIANTE_PASSWORD", "Student2026!")
DOCENTE_EMAIL = os.environ.get("E2E_DOCENTE_EMAIL", "docente@upao.edu.pe")
DOCENTE_PASSWORD = os.environ.get("E2E_DOCENTE_PASSWORD", "Docente2026!")

_SUFIJO = str(int(time.time()))

# (nombre, detalle, ok, duracion_ms) — el detalle es siempre algo que la
# propia categoría ya midió (conteos reales de su respuesta HTTP), nunca
# un número estimado o inventado para que la tabla se vea completa.
_RESULTADOS: list[tuple[str, str, bool, float]] = []


def _ok(mensaje: str) -> None:
    print(f"    ✓ {mensaje}")


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


def _categoria(nombre: str, ctx: dict[str, Any], fn) -> None:
    """Corre una categoría, registra PASS/FAIL y SIGUE con la próxima —
    un fallo no detiene el recorrido completo (cada categoría es
    evidencia independiente sobre una capacidad distinta de la
    plataforma; ocultar las que vienen después de la primera falla
    escondería información, no la protege). `fn` devuelve una métrica
    corta (str) de lo que ya midió — no se inventa nada aquí."""
    print(f"\n— {nombre}")
    inicio = time.perf_counter()
    try:
        detalle = fn(ctx) or ""
    except Exception as exc:  # noqa: BLE001 — se reporta, nunca se oculta
        duracion_ms = (time.perf_counter() - inicio) * 1000
        print(f"    ✗ FAIL: {exc}")
        _RESULTADOS.append((nombre, str(exc), False, duracion_ms))
    else:
        duracion_ms = (time.perf_counter() - inicio) * 1000
        _RESULTADOS.append((nombre, detalle, True, duracion_ms))


def _postgres(ctx: dict[str, Any]) -> str:
    verificar_servidor_activo()
    _ok("servidor activo")
    ctx["cliente"] = cliente = ClienteE2E()
    estudiante = cliente.login(ESTUDIANTE_EMAIL, ESTUDIANTE_PASSWORD)
    _ok(f"login como {estudiante['email']}")
    ctx["session_id"] = session_id = f"e2e-{_SUFIJO}"
    ctx["identidad"] = cliente.abrir_sesion(session_id)
    _ok(f"sesión {session_id} abierta y persistida — escritura real en Postgres")
    return f"sesión {session_id} escrita"


def _runtime(ctx: dict[str, Any]) -> str:
    cliente: ClienteE2E = ctx["cliente"]
    entrega = cliente.registrar_hecho(
        ctx["identidad"], {"competencia": "COMP-2", "items_incorrectos": [3, 4, 8]}
    )
    assert entrega.get("asunto"), "el walkthrough no llegó a producir una Entrega"
    ctx["entrega"] = entrega
    _ok(f"walkthrough real corrió — entrega: {entrega['asunto']}")
    return f"entrega={entrega['asunto']}"


def _boundary(ctx: dict[str, Any]) -> str:
    cliente: ClienteE2E = ctx["cliente"]
    docente = cliente.login(DOCENTE_EMAIL, DOCENTE_PASSWORD)
    _ok(f"login como {docente['email']}")
    estado = cliente.estado(ctx["session_id"])
    assert estado["facts"] and estado["claims"]
    ctx["estado"] = estado
    _ok("el docente lee /estado de la sesión del estudiante por el Boundary (RFC-0009 §1)")
    return "lectura cross-rol vía Boundary OK"


def _observabilidad(ctx: dict[str, Any]) -> str:
    cliente: ClienteE2E = ctx["cliente"]
    traza = cliente.traza(ctx["session_id"])
    assert traza and traza[0]["eventos"][0]["tipo"] == "FactRegistrado"
    ctx["traza"] = traza
    _ok(f"traza: {len(traza)} transiciones, T1={traza[0]['eventos'][0]['tipo']}")
    _ok(f"estado: {len(ctx['estado']['facts'])} facts, {len(ctx['estado']['claims'])} claims")
    return f"{len(traza)} transiciones, {len(ctx['estado']['facts'])}F/{len(ctx['estado']['claims'])}C"


def _replay(ctx: dict[str, Any]) -> str:
    cliente: ClienteE2E = ctx["cliente"]
    replay = cliente.replay(ctx["session_id"])
    assert len(replay) == len(ctx["traza"])
    assert replay[-1]["estado"] == ctx["estado"]
    _ok(f"replay: {len(replay)} pasos, último coincide con /estado")
    return f"{len(replay)} pasos"


def _memory(ctx: dict[str, Any]) -> str:
    cliente: ClienteE2E = ctx["cliente"]
    cliente.login(ESTUDIANTE_EMAIL, ESTUDIANTE_PASSWORD)
    session_id_cierre = f"e2e-{_SUFIJO}-cierre"
    identidad_cierre = cliente.abrir_sesion(session_id_cierre)
    cliente.registrar_hecho(
        identidad_cierre,
        {"competencia": "COMP-2", "items_incorrectos": [1]},
        cerrar_sesion=True,
    )
    session_id_siguiente = f"e2e-{_SUFIJO}-siguiente"
    cliente.abrir_sesion(session_id_siguiente)
    memoria = cliente.memoria(session_id_siguiente)
    assert memoria is not None
    assert memoria["session_id"] == session_id_cierre
    _ok(f"memoria consolidada por {memoria['session_id']}, leída por la sesión siguiente")
    return f"consolidada por {memoria['session_id']}"


def _hitl(ctx: dict[str, Any]) -> str:
    cliente: ClienteE2E = ctx["cliente"]
    session_id = ctx["session_id"]

    cliente.login(DOCENTE_EMAIL, DOCENTE_PASSWORD)
    cliente.hecho_docente(
        session_id,
        {"competencia": "COMP-2", "items_incorrectos": [7]},
        human_reason="observé confusión persistente en clase",
    )
    ultimo_paso = cliente.traza(session_id)[-1]
    assert any(e["datos"].get("origen") == "humano" for e in ultimo_paso["eventos"])
    _ok("intervención espontánea: fact con origen=humano visible en la traza real")

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
    ctx["estado_hitl"] = estado_final = cliente.estado(session_id_hitl)
    cierre = next(d for d in estado_final["deliberaciones"] if d.get("enlaza_a") == escalada_id)
    assert cierre["resultado"]["regla"] == "decision-humana"
    assert any(dec["origen"] == cierre["id"] for dec in estado_final["decisiones"])
    _ok("escalada resuelta y decisión derivada — el runtime continuó solo")
    return "1 intervención espontánea, 1 escalada resuelta"


def _llm(ctx: dict[str, Any]) -> str:
    # El claim de Adaptar (asunto "modalidad(...)") solo existe si un
    # proveedor LLM real corrió — nunca lo produce un reducer ni un
    # productor de reglas (ADR-0007). No se cuentan llamadas HTTP a
    # OpenAI/Tavily porque este cliente no las instrumenta — reportar un
    # número no medido sería inventarlo.
    estado = ctx.get("estado_hitl") or ctx["estado"]
    claims_adaptar = [c for c in estado["claims"] if str(c.get("asunto", "")).startswith("modalidad(")]
    assert claims_adaptar, "ningún claim de Adaptar — ¿el proveedor LLM real corrió?"
    _ok(f"Adaptar produjo {len(claims_adaptar)} claim(s) vía LLM real: {claims_adaptar[-1]['asunto']}")
    return f"Adaptar: {len(claims_adaptar)} claim(s) reales"


def _resumen() -> bool:
    ancho = 46
    print("\n" + "=" * ancho)
    print("RUNTIME PLATFORM CHECK")
    print("=" * ancho + "\n")
    for nombre, detalle, ok, duracion_ms in _RESULTADOS:
        estado = "PASS" if ok else "FAIL"
        cola = f"({detalle}, {duracion_ms:.0f} ms)" if ok else f"— {detalle}"
        print(f"{nombre:.<20} {estado} {cola}")
    total_ok = sum(1 for _, _, ok, _ in _RESULTADOS if ok)
    total = len(_RESULTADOS)
    print(f"\nTotal:\n{total_ok}/{total} PASS")
    print("=" * ancho)
    return total_ok == total


# Orden fijo: cada categoría depende del estado que dejan las
# anteriores (mismo ctx compartido) — "--only X" corre la cadena hasta
# X inclusive, nunca X en aislamiento verdadero.
_CATEGORIAS: list[tuple[str, Any]] = [
    ("Postgres", _postgres),
    ("Runtime", _runtime),
    ("Boundary", _boundary),
    ("Observabilidad", _observabilidad),
    ("Replay", _replay),
    ("Memory", _memory),
    ("HITL", _hitl),
    ("LLM", _llm),
]


def main(solo: str | None = None) -> bool:
    print("Recorrido E2E — Runtime LangGraph (real, sin mocks)")
    categorias = _CATEGORIAS
    if solo is not None:
        nombres = [nombre for nombre, _ in _CATEGORIAS]
        objetivo = next((n for n in nombres if n.lower() == solo.lower()), None)
        if objetivo is None:
            raise SystemExit(f"--only {solo!r} inválido — opciones: {', '.join(nombres)}")
        indice = nombres.index(objetivo)
        categorias = _CATEGORIAS[: indice + 1]
        print(f"(--only {objetivo}: corriendo {', '.join(n for n, _ in categorias)})")

    ctx: dict[str, Any] = {}
    for nombre, fn in categorias:
        _categoria(nombre, ctx, fn)
    return _resumen()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--only",
        metavar="CATEGORIA",
        help="corre solo hasta esta categoría (Postgres, Runtime, Boundary, "
        "Observabilidad, Replay, Memory, HITL, LLM)",
    )
    argumentos = parser.parse_args()
    raise SystemExit(0 if main(solo=argumentos.only) else 1)
