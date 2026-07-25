"""IT-08 -- Integracion Frontend <-> Backend (contrato de autenticacion).

A diferencia de e2e/tests/test_e2e_01_login.py (que valida el RECORRIDO del
usuario), este caso valida el CONTRATO de integracion entre el cliente
Vite/React real y la API real: que el JWT emitido por
POST /api/auth/login sea efectivamente el mismo token que el frontend
persiste y reutiliza para autorizar la siguiente peticion.

Requiere el frontend real (Vite, puerto 5173) y el backend real (puerto
8000) corriendo. Se omite automaticamente si el frontend no esta arriba,
igual que el resto de la suite de integracion se omite sin backend/Postgres.
"""
import os
import sys
import time

import pytest
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from e2e.config import CHROME_BINARY  # noqa: E402
from tests.integration.conftest import BASE_URL  # noqa: E402

FRONTEND_URL = "http://localhost:5173"


def _frontend_disponible() -> bool:
    try:
        requests.get(FRONTEND_URL, timeout=3)
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _frontend_disponible(), reason="Requiere el frontend real en localhost:5173")


@pytest.fixture
def driver():
    opts = Options()
    opts.binary_location = CHROME_BINARY
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1424,900")
    d = webdriver.Chrome(options=opts)
    yield d
    d.quit()


def test_el_frontend_persiste_y_reutiliza_el_jwt_real_emitido_por_el_backend(driver):
    print(f"[IT-08] GET {FRONTEND_URL}/login (Vite real)")
    driver.get(f"{FRONTEND_URL}/login")
    time.sleep(1)
    driver.find_element(By.ID, "identifier").send_keys("docente@upao.edu.pe")
    driver.find_element(By.ID, "password").send_keys("Docente2026!")

    print(f"[IT-08] Submit -> el frontend debe llamar POST {BASE_URL}/api/auth/login por su cuenta")
    driver.find_element(By.CSS_SELECTOR, "button[type=submit]").click()
    time.sleep(2.5)

    print(f"[IT-08] URL final tras el login real: {driver.current_url}")
    assert "/docente" in driver.current_url, "El frontend debio redirigir segun el rol devuelto por el backend real"

    # frontend/src/stores/authStore.ts persiste con zustand/middleware bajo la
    # clave real "upao-auth" (JSON con la forma {state: {accessToken, ...}}),
    # no bajo una clave literal "token".
    raw = driver.execute_script("return window.localStorage.getItem('upao-auth')")
    print(f"[IT-08] localStorage['upao-auth'] presente: {bool(raw)}")
    token_frontend = None
    if raw:
        import json
        try:
            parsed = json.loads(raw)
            token_frontend = parsed.get("state", {}).get("token")
        except Exception as exc:
            print(f"[IT-08] No se pudo parsear upao-auth: {exc}")
    print(f"[IT-08] token extraido del store real del frontend: {'presente' if token_frontend else 'ausente'}")
    assert token_frontend, "El frontend debio persistir el JWT real recibido del backend en localStorage"

    print("[IT-08] Reutilizando ESE MISMO token para llamar directamente a la API (bypass del frontend)")
    resp = requests.get(
        f"{BASE_URL}/api/students/my-courses",
        headers={"Authorization": f"Bearer {token_frontend}"},
        timeout=10,
    )
    print(f"[IT-08] GET /api/students/my-courses con el token del frontend -> status={resp.status_code}")
    # Docente no tiene permiso sobre esta ruta de estudiante: lo relevante no es
    # el codigo exacto sino que NO sea 401 -- confirma que el backend acepto el
    # token como valido (fallo por autorizacion de rol, no por autenticacion).
    assert resp.status_code != 401, "El token real persistido por el frontend debe ser aceptado como valido por el backend"
