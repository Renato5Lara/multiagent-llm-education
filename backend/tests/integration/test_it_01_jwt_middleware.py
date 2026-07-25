"""IT-01 -- Integracion JWT <-> Middleware de autenticacion.

Componentes reales: app/core/security.py (emision/verificacion JWT) y
app/api/deps.py (get_current_user / get_current_docente / get_current_admin)
como guardia de las rutas protegidas, contra el servidor uvicorn real.
"""
import requests

from tests.integration.conftest import BASE_URL, auth_header


def test_ruta_protegida_sin_token_es_rechazada_antes_de_tocar_la_bd():
    print(f"[IT-01] GET {BASE_URL}/api/students/my-courses sin token")
    resp = requests.get(f"{BASE_URL}/api/students/my-courses", timeout=10)
    print(f"[IT-01] status={resp.status_code} body={resp.text[:200]}")
    assert resp.status_code == 401, (
        "El middleware de dependencias (get_current_user) debe rechazar la "
        "peticion antes de que cualquier consulta a la BD se ejecute"
    )


def test_ruta_protegida_con_token_invalido_es_rechazada(estudiante_session):
    print("[IT-01] GET /api/students/my-courses con token manipulado")
    header = {"Authorization": "Bearer " + estudiante_session["access_token"][:-5] + "XXXXX"}
    resp = requests.get(f"{BASE_URL}/api/students/my-courses", headers=header, timeout=10)
    print(f"[IT-01] status={resp.status_code} body={resp.text[:200]}")
    assert resp.status_code == 401


def test_ruta_protegida_con_token_valido_consulta_la_bd_real(estudiante_session):
    print("[IT-01] GET /api/students/my-courses con token real emitido por /api/auth/login")
    resp = requests.get(
        f"{BASE_URL}/api/students/my-courses", headers=auth_header(estudiante_session), timeout=10
    )
    print(f"[IT-01] status={resp.status_code} cursos_devueltos={len(resp.json()) if resp.status_code == 200 else 'N/A'}")
    assert resp.status_code == 200
    cuerpo = resp.json()
    assert isinstance(cuerpo, list), "get_current_user resolvio el usuario real y la ruta devolvio datos reales de PostgreSQL"
