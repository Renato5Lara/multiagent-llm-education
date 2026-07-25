"""Pagina base para vistas autenticadas que comparten el Sidebar real
(frontend/src/components/layout/Sidebar.tsx) usado por Admin/Docente/
Estudiante/Evidencia. Encapsula la navegacion por el menu lateral real
en lugar de solo saltar por URL, para probar interaccion real de UI."""
from selenium.webdriver.common.by import By

from e2e.pages.base_page import BasePage
from e2e.pages.login_page import LoginPage


class AuthenticatedPage(BasePage):
    def login_as(self, identifier: str, password: str, wait_url_fragment: str):
        LoginPage(self.driver).open_login().login(identifier, password)
        self.wait_url_contains(wait_url_fragment)
        self.settle()
        return self

    def click_sidebar_link(self, label: str):
        link = self.wait.until(
            lambda d: next(
                (el for el in d.find_elements(By.CSS_SELECTOR, "aside nav a")
                 if el.text.strip() == label),
                None,
            )
        )
        link.click()
        self.settle()
        return self

    def logout_state(self):
        self.driver.delete_all_cookies()
        self.driver.execute_script("window.localStorage.clear(); window.sessionStorage.clear();")
