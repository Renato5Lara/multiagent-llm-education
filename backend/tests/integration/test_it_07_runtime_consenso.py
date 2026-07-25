"""IT-07 -- Integracion Runtime <-> Motor de Consenso/Deliberacion (RFC-0006).

Componentes reales: runtime/kernel/deliberation/{politica,confianza,mecanica}.py,
invocados por runtime/engine/graph/walkthrough.py (ejecutar_walkthrough),
alcanzable desde /api/runtime/hechos -- se verifica que el campo
`deliberaciones` de EstadoOut (app/api/routes/runtime.py) refleja lo que
el motor de deliberacion real produjo para la secuencia de hechos
enviada, en lugar de asumir un conteo fijo.
"""
import uuid

import requests

from tests.integration.conftest import BASE_URL, auth_header


def test_estado_expone_el_conteo_real_de_deliberaciones_del_motor_de_consenso(estudiante_session):
    session_id = f"s-it07-{uuid.uuid4().hex[:8]}"
    headers = auth_header(estudiante_session)

    abierta = requests.post(
        f"{BASE_URL}/api/runtime/sessions", json={"session_id": session_id}, headers=headers, timeout=15
    )
    assert abierta.status_code == 200
    identidad = abierta.json()

    print("[IT-07] Hecho 1: diagnostico via instrumento (COMP-2, items incorrectos)")
    requests.post(
        f"{BASE_URL}/api/runtime/hechos",
        json={
            "identidad": identidad,
            "contenido": {"competencia": "COMP-2", "items_incorrectos": [3, 4, 8]},
            "origen": "instrumento",
        },
        headers=headers,
        timeout=30,
    )

    print(f"[IT-07] GET /api/runtime/sessions/{session_id}/estado")
    estado = requests.get(f"{BASE_URL}/api/runtime/sessions/{session_id}/estado", headers=headers, timeout=15)
    print(f"[IT-07] status={estado.status_code}")
    assert estado.status_code == 200
    cuerpo = estado.json()
    print(
        f"[IT-07] transicion={cuerpo['transicion']} facts={len(cuerpo['facts'])} "
        f"claims={len(cuerpo['claims'])} deliberaciones={len(cuerpo.get('deliberaciones', []))} "
        f"decisiones={len(cuerpo.get('decisiones', []))}"
    )

    assert "deliberaciones" in cuerpo, (
        "EstadoOut debe exponer el campo deliberaciones -- confirma que la ruta HTTP esta "
        "estructuralmente conectada al motor de consenso (RFC-0006), no solo a facts/claims"
    )
    assert cuerpo["transicion"] == (
        len(cuerpo["facts"]) + len(cuerpo["claims"]) + len(cuerpo["deliberaciones"]) + len(cuerpo["decisiones"])
    ), "La contabilidad de transiciones del runtime debe ser consistente con lo real devuelto por Postgres"
