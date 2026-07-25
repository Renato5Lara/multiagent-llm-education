"""E2E-01 -- Autenticacion multi-rol.

Proceso de negocio validado: el ingreso al sistema es el punto de entrada
obligatorio de los 3 actores (estudiante, docente, administrador). Sin un
login funcional ningun otro recorrido es alcanzable.
"""
from selenium.webdriver.common.by import By

from e2e.config import USERS
from e2e.pages.login_page import LoginPage
from e2e.utils.screenshots import capture

CASE = "E2E-01"


def test_login_redirects_por_rol(driver):
    page = LoginPage(driver)
    page.open_login()
    capture(driver, CASE, "pantalla_login_inicial")

    casos_rol = [
        ("estudiante", USERS["estudiante_e2e"], "/estudiante"),
        ("docente", USERS["docente"], "/docente"),
        ("admin", USERS["admin"], "/admin"),
    ]

    for rol, creds, ruta_esperada in casos_rol:
        page.open_login()
        page.login(creds["identifier"], creds["password"])
        page.wait_url_contains(ruta_esperada)
        page.settle()
        capture(driver, CASE, f"post_login_{rol}")
        assert ruta_esperada in page.current_url, (
            f"Tras iniciar sesion como {rol} se esperaba una URL que contenga "
            f"'{ruta_esperada}', se obtuvo '{page.current_url}'"
        )
        driver.delete_all_cookies()
        driver.execute_script("window.localStorage.clear(); window.sessionStorage.clear();")


def test_login_credenciales_invalidas(driver):
    page = LoginPage(driver)
    page.open_login()
    page.login("estudiante.e2e@upao.edu.pe", "clave-incorrecta-a-proposito")
    page.wait_text_present("ncorrect")  # cubre "incorrectas"/"Incorrect" segun copy real
    capture(driver, CASE, "credenciales_invalidas")
    assert "/login" in page.current_url


def test_ruta_inexistente_muestra_404(driver):
    """No se ejecuta el bloqueo de cuenta tras 3 intentos fallidos (auth_service):
    reutiliza cuentas de otros casos de esta misma suite y un bloqueo real de
    5 minutos interferiria con el resto de la ejecucion. Se documenta como
    limitacion deliberada, no como omision silenciosa."""
    page = LoginPage(driver)
    page.open("/una-ruta-que-no-existe-jamas")
    page.settle(0.8)
    capture(driver, CASE, "ruta_inexistente_404")
    assert page.text_present("404") or "no encontrada" in page.driver.page_source.lower() or \
        "not found" in page.driver.page_source.lower()
