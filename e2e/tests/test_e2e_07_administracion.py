"""E2E-07 -- Administracion.

Proceso de negocio validado: el administrador puede supervisar usuarios,
roles y el estado tecnico de la plataforma -- el recorrido minimo del
tercer actor del sistema segun CLAUDE.md.
"""
from e2e.config import USERS
from e2e.pages.authenticated_page import AuthenticatedPage
from e2e.utils.screenshots import capture

CASE = "E2E-07"


def test_recorrido_administrador(driver):
    page = AuthenticatedPage(driver)
    creds = USERS["admin"]
    page.login_as(creds["identifier"], creds["password"], "/admin")
    capture(driver, CASE, "dashboard_admin")
    assert page.current_url.rstrip("/").endswith("/admin")

    page.click_sidebar_link("Usuarios")
    capture(driver, CASE, "gestion_usuarios")
    assert "/admin/users" in page.current_url

    page.click_sidebar_link("Roles")
    capture(driver, CASE, "gestion_roles")
    assert "/admin/roles" in page.current_url

    page.click_sidebar_link("Estado del sistema")
    capture(driver, CASE, "estado_del_sistema")
    assert "/admin/system" in page.current_url
