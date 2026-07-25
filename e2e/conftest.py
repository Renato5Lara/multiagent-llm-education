"""Fixtures compartidas de la suite E2E (Selenium WebDriver, Chrome real del sistema)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from e2e.config import CHROME_BINARY, WINDOW_SIZE


def _build_driver():
    opts = Options()
    opts.binary_location = CHROME_BINARY
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument(f"--window-size={WINDOW_SIZE[0]},{WINDOW_SIZE[1]}")
    opts.add_argument("--lang=es-PE")
    driver = webdriver.Chrome(options=opts)
    driver.set_window_size(*WINDOW_SIZE)
    return driver


@pytest.fixture
def driver():
    d = _build_driver()
    yield d
    d.quit()
