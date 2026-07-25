"""E2E-02 -- Onboarding del estudiante nuevo (arranque en frio).

Proceso de negocio validado: un estudiante sin historial (has_diagnostic=false)
debe ver el CTA "Comenzar diagnostico" en su dashboard y, al pulsarlo, llegar
a la vista real de diagnostico -- el punto de entrada de toda la adaptacion
multimodal que sustenta la hipotesis de tesis.
"""
from selenium.webdriver.common.by import By

from e2e.config import USERS
from e2e.pages.authenticated_page import AuthenticatedPage
from e2e.utils.screenshots import capture

CASE = "E2E-02"


def test_onboarding_diagnostico_desde_dashboard(driver):
    page = AuthenticatedPage(driver)
    creds = USERS["estudiante_e2e2"]  # cuenta desechable "sin historial"
    page.login_as(creds["identifier"], creds["password"], "/estudiante")
    capture(driver, CASE, "dashboard_estudiante_nuevo")

    assert "estudiante" in page.current_url

    boton_diagnostico = page.wait.until(
        lambda d: next(
            (b for b in d.find_elements(By.TAG_NAME, "button") if "diagn" in b.text.lower()),
            None,
        )
    )
    assert boton_diagnostico is not None, "No se encontro el CTA 'Comenzar diagnostico' en el dashboard"
    capture(driver, CASE, "cta_comenzar_diagnostico_visible")

    boton_diagnostico.click()
    page.wait_url_contains("/estudiante/diagnostic/")
    page.settle(1.5)
    capture(driver, CASE, "vista_diagnostico_cargada")

    assert "/estudiante/diagnostic/" in page.current_url
    botones = page.find_all(By.TAG_NAME, "button")
    assert len(botones) > 0, "La vista de diagnostico cargo sin ningun control interactivo"
