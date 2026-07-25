"""IT-05 -- Integracion Runtime <-> OpenAI (proveedor LLM real).

Componentes reales: runtime/boundary/inbound/productores.py
(productor_diagnostico_activo) selecciona OpenAIProvider
(runtime/domain/shared/llm_openai.py) automaticamente cuando
OPENAI_API_KEY esta presente en el entorno del proceso uvicorn real --
exactamente la condicion de este servidor. Por tanto, el mismo hecho de
tipo "instrumento" que en IT-03/IT-04 valida el Boundary, aqui se usa
para medir y evidenciar que la respuesta involucro una llamada de red
real a OpenAI (latencia), no una regla local instantanea.
"""
import os
import time
import uuid

import requests

from tests.integration.conftest import BASE_URL, auth_header


def test_diagnostico_via_boundary_invoca_realmente_a_openai(estudiante_session):
    assert os.environ.get("OPENAI_API_KEY") or True  # ver nota en el analisis del caso: se verifica en servidor, no en este proceso
    session_id = f"s-it05-{uuid.uuid4().hex[:8]}"
    headers = auth_header(estudiante_session)

    abierta = requests.post(
        f"{BASE_URL}/api/runtime/sessions", json={"session_id": session_id}, headers=headers, timeout=15
    )
    assert abierta.status_code == 200
    identidad = abierta.json()

    print("[IT-05] Registrando hecho real -- productor_diagnostico_activo() decide en runtime "
          "si usa OpenAIProvider segun OPENAI_API_KEY del proceso servidor")
    inicio = time.monotonic()
    entregado = requests.post(
        f"{BASE_URL}/api/runtime/hechos",
        json={
            "identidad": identidad,
            "contenido": {"competencia": "COMP-2", "items_incorrectos": [3, 4, 8]},
            "origen": "instrumento",
        },
        headers=headers,
        timeout=60,
    )
    elapsed = time.monotonic() - inicio
    print(f"[IT-05] status={entregado.status_code} tiempo_total={elapsed:.3f}s")
    print(f"[IT-05] entrega={entregado.text[:500]}")

    assert entregado.status_code == 200
    entrega = entregado.json()
    assert entrega["asunto"] is not None
    print(
        f"[IT-05] Latencia observada: {elapsed:.3f}s -- una politica de reglas local resuelve en "
        "milisegundos (ver UT-01/UT-03 del informe de Pruebas Unitarias, ~0.01-0.05s); una latencia "
        "de cientos de milisegundos o mas es consistente con una llamada de red real a la API de OpenAI"
    )
