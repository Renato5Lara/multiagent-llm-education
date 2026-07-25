"""Page Object de /login (frontend/src/pages/Login.tsx)."""
from selenium.webdriver.common.by import By

from e2e.pages.base_page import BasePage


class LoginPage(BasePage):
    IDENTIFIER = (By.ID, "identifier")
    PASSWORD = (By.ID, "password")
    SUBMIT = (By.CSS_SELECTOR, "button[type='submit']")

    def open_login(self):
        self.open("/login")
        self.find(*self.IDENTIFIER)
        return self

    def login(self, identifier: str, password: str):
        self.find(*self.IDENTIFIER).clear()
        self.driver.find_element(*self.IDENTIFIER).send_keys(identifier)
        self.driver.find_element(*self.PASSWORD).clear()
        self.driver.find_element(*self.PASSWORD).send_keys(password)
        self.find_clickable(*self.SUBMIT).click()
        return self

    def error_message_text(self) -> str:
        body = self.driver.find_element(By.TAG_NAME, "body").text
        return body
