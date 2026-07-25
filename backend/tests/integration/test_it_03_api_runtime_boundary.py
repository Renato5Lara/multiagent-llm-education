"""IT-03 -- Integracion API <-> Runtime (Platform Boundary, RFC-0010).

Componentes reales: app/api/routes/runtime.py -> runtime.boundary ->
runtime.engine.graph (LangGraph) -> PostgreSQL (esquema `runtime`), contra
el servidor uvicorn real, con autenticacion JWT real (no overrides de
dependencia como en el equivalente unitario tests/test_runtime_boundary_http.py,
que si reutiliza el mismo patron de payload confirmado en ese archivo).
"""
import uuid

import requests

from tests.integration.conftest import BASE_URL, auth_header


def test_abrir_sesion_registrar_hecho_y_consultar_traza_via_http_real(estudiante_session):
    session_id = f"s-it03-{uuid.uuid4().hex[:8]}"
    headers = auth_header(estudiante_session)

    print(f"[IT-03] POST {BASE_URL}/api/runtime/sessions session_id={session_id}")
    abierta = requests.post(
        f"{BASE_URL}/api/runtime/sessions", json={"session_id": session_id}, headers=headers, timeout=15
    )
    print(f"[IT-03] status={abierta.status_code} body={abierta.text[:300]}")
    assert abierta.status_code == 200, abierta.text
    identidad = abierta.json()
    assert identidad["session_id"] == session_id

    print("[IT-03] POST /api/runtime/hechos (hecho de tipo instrumento)")
    entregado = requests.post(
        f"{BASE_URL}/api/runtime/hechos",
        json={
            "identidad": identidad,
            "contenido": {"competencia": "COMP-2", "items_incorrectos": [3, 4, 8]},
            "origen": "instrumento",
        },
        headers=headers,
        timeout=30,
    )
    print(f"[IT-03] status={entregado.status_code} body={entregado.text[:400]}")
    assert entregado.status_code == 200, entregado.text
    entrega = entregado.json()
    assert entrega["asunto"] is not None, "El Boundary debio producir una entrega con asunto real"

    print(f"[IT-03] GET /api/runtime/sessions/{session_id}/traza")
    traza = requests.get(f"{BASE_URL}/api/runtime/sessions/{session_id}/traza", headers=headers, timeout=15)
    print(f"[IT-03] status={traza.status_code} pasos={len(traza.json()) if traza.status_code == 200 else 'N/A'}")
    assert traza.status_code == 200
    pasos = traza.json()
    assert len(pasos) > 0
    assert pasos[0]["eventos"][0]["tipo"] == "FactRegistrado"
    assert pasos[0]["eventos"][0]["datos"]["autor"] == "boundary", (
        "RFC-0010 regla 1: el Boundary traduce, no reatribuye el hecho a una capacidad de dominio"
    )
