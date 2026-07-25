"""E2E-04 -- Tutor IA (asistente conversacional dentro de la Ruta de Aprendizaje).

Proceso de negocio validado: el estudiante puede invocar al Tutor IA en
cualquier punto de su ruta -- valida que el widget conversacional real se
monta, recibe foco y acepta entrada de texto.
"""
from selenium.webdriver.common.by import By

from e2e.config import USERS
from e2e.pages.authenticated_page import AuthenticatedPage
from e2e.utils.screenshots import capture

CASE = "E2E-04"

# Curso con ruta de aprendizaje ya generada para estudiante3 (confirmado via
# GET /api/students/my-courses durante el diseno de esta suite).
CURSO_CON_RUTA = "b1fab2dc-7aef-463b-b4cf-75eee9c86acd"


def test_tutor_ia_se_abre_y_acepta_pregunta(driver):
    page = AuthenticatedPage(driver)
    creds = USERS["estudiante_con_historial"]
    page.login_as(creds["identifier"], creds["password"], "/estudiante")

    page.open(f"/estudiante/path/{CURSO_CON_RUTA}")
    page.settle(1.5)
    capture(driver, CASE, "ruta_de_aprendizaje_antes_de_abrir_tutor")

    boton_tutor = next(
        b for b in page.find_all(By.TAG_NAME, "button") if "tutor ia" in b.text.lower()
    )
    boton_tutor.click()
    page.settle(1.0)
    capture(driver, CASE, "tutor_ia_abierto")

    campo_pregunta = page.find(By.CSS_SELECTOR, "input[placeholder*='duda']")
    assert campo_pregunta.is_displayed(), "El campo de texto del Tutor IA no se renderizo visible"

    campo_pregunta.send_keys("Que es una variable en programacion")
    capture(driver, CASE, "pregunta_escrita_en_tutor")

    assert campo_pregunta.get_attribute("value") == "Que es una variable en programacion"
