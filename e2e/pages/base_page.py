"""Pagina base del Page Object Model: esperas explicitas y navegacion comun."""
import time

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

from e2e.config import FRONTEND_URL, DEFAULT_TIMEOUT


class BasePage:
    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(driver, DEFAULT_TIMEOUT)

    def open(self, path: str = "/"):
        self.driver.get(f"{FRONTEND_URL}{path}")
        return self

    def find(self, by, value):
        return self.wait.until(EC.presence_of_element_located((by, value)))

    def find_clickable(self, by, value):
        return self.wait.until(EC.element_to_be_clickable((by, value)))

    def find_all(self, by, value):
        return self.driver.find_elements(by, value)

    def wait_url_contains(self, fragment: str):
        return self.wait.until(EC.url_contains(fragment))

    def text_present(self, text: str) -> bool:
        return text in self.driver.find_element(By.TAG_NAME, "body").text

    def wait_text_present(self, text: str):
        return self.wait.until(lambda d: text in d.find_element(By.TAG_NAME, "body").text)

    def wait_until_not_present(self, text: str, timeout: float = 20):
        WebDriverWait(self.driver, timeout).until_not(
            lambda d: text in d.find_element(By.TAG_NAME, "body").text
        )
        return self

    def settle(self, seconds: float = 1.2):
        """Deja tiempo real a las llamadas async (fetch de datos, skeletons) antes de capturar."""
        time.sleep(seconds)
        return self

    @property
    def current_url(self):
        return self.driver.current_url
