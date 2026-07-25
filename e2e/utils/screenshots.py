"""Utilidad de captura de evidencia real durante la ejecucion de Selenium."""
import os
import re

from e2e.config import EVIDENCE_DIR


def _slug(text: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]+", "_", text).strip("_")


def capture(driver, case_id: str, step_name: str) -> str:
    """Guarda una captura PNG real del estado actual del navegador.

    Devuelve la ruta absoluta del archivo generado. Cada llamada corresponde
    a un paso real ya ejecutado contra el sistema en vivo (frontend+backend).
    """
    case_dir = os.path.join(EVIDENCE_DIR, case_id)
    os.makedirs(case_dir, exist_ok=True)
    existing = len([f for f in os.listdir(case_dir) if f.endswith(".png")])
    filename = f"{existing + 1:02d}_{_slug(step_name)}.png"
    path = os.path.join(case_dir, filename)
    driver.save_screenshot(path)
    return path
