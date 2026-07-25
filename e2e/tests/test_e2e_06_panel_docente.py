"""E2E-06 -- Panel Docente.

Proceso de negocio validado: el docente puede navegar su dashboard, sus
cursos, el panel pedagogico y la analitica IA -- las 4 preguntas del
docente que CLAUDE.md declara como segunda prioridad del recorrido.
"""
from e2e.config import USERS
from e2e.pages.authenticated_page import AuthenticatedPage
from e2e.utils.screenshots import capture

CASE = "E2E-06"


def test_recorrido_docente(driver):
    page = AuthenticatedPage(driver)
    creds = USERS["docente"]
    page.login_as(creds["identifier"], creds["password"], "/docente")
    capture(driver, CASE, "dashboard_docente")
    assert page.current_url.rstrip("/").endswith("/docente")

    page.click_sidebar_link("Mis Cursos")
    capture(driver, CASE, "mis_cursos")
    assert "/docente/courses" in page.current_url

    page.click_sidebar_link("Panel Pedagógico")
    capture(driver, CASE, "panel_pedagogico")
    assert "/docente/panel-pedagogico" in page.current_url

    page.click_sidebar_link("Analítica IA")
    capture(driver, CASE, "analitica_ia")
    assert "/docente/analytics" in page.current_url
