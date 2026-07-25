"""Configuracion centralizada de la suite E2E."""
import os

FRONTEND_URL = os.environ.get("E2E_FRONTEND_URL", "http://localhost:5173")
BACKEND_URL = os.environ.get("E2E_BACKEND_URL", "http://localhost:8000")

CHROME_BINARY = os.environ.get(
    "E2E_CHROME_BINARY", r"C:\Program Files\Google\Chrome\Application\chrome.exe"
)

DEFAULT_TIMEOUT = 15
WINDOW_SIZE = (1440, 960)

# Credenciales reales de backend/seed.py (base de datos de desarrollo, no fixtures de pytest)
USERS = {
    "admin": {"identifier": "admin@upao.edu.pe", "password": "Admin2026!"},
    "docente": {"identifier": "docente@upao.edu.pe", "password": "Docente2026!"},
    # Cuenta desechable "sin historial" sembrada especificamente para E2E (backend/seed.py)
    "estudiante_e2e": {"identifier": "estudiante.e2e@upao.edu.pe", "password": "Student2026!"},
    "estudiante_e2e2": {"identifier": "estudiante.e2e2@upao.edu.pe", "password": "Student2026!"},
    "estudiante_e2e3": {"identifier": "estudiante.e2e3@upao.edu.pe", "password": "Student2026!"},
    "estudiante_con_historial": {"identifier": "estudiante3@upao.edu.pe", "password": "Student2026!"},
}

EVIDENCE_DIR = os.path.join(os.path.dirname(__file__), "evidence")
