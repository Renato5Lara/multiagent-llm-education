"""E2E-08 -- Modo Evidencia.

Proceso de negocio validado: la capacidad de observabilidad destinada a la
sustentacion -- el hub de evidencia, el dashboard del investigador y la
Runtime Console deben cargar sin requerir un rol especifico (acceso desde
Admin/Docente segun el sidebar, sin guard de rol propio).
"""
from e2e.config import USERS
from e2e.pages.authenticated_page import AuthenticatedPage
from e2e.utils.screenshots import capture

CASE = "E2E-08"


def test_recorrido_modo_evidencia(driver):
    page = AuthenticatedPage(driver)
    creds = USERS["admin"]
    page.login_as(creds["identifier"], creds["password"], "/admin")

    page.click_sidebar_link("Modo Evidencia")
    page.wait_url_contains("/evidencia")
    page.settle(1.0)
    capture(driver, CASE, "evidence_hub")
    assert "/evidencia" in page.current_url

    page.click_sidebar_link("Dashboard del Investigador")
    page.wait_url_contains("/evidencia/investigacion")
    page.settle(1.2)
    capture(driver, CASE, "dashboard_investigador")
    assert "/evidencia/investigacion" in page.current_url

    page.click_sidebar_link("Runtime Console")
    page.wait_url_contains("/evidencia/runtime")
    page.settle(1.2)
    capture(driver, CASE, "runtime_console")
    assert "/evidencia/runtime" in page.current_url
