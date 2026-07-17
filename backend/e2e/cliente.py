"""Cliente HTTP mínimo para los recorridos E2E — envuelve exactamente los
endpoints reales de `/api/runtime/*` (ADR-0009: HTTP → Boundary →
Runtime), sin atajos internos. Cualquier recorrido nuevo reutiliza esta
pieza en vez de reimplementar login/requests."""

from __future__ import annotations

import os
from typing import Any

import requests

BASE_URL = os.environ.get("E2E_BASE_URL", "http://localhost:8000")


class FalloE2E(RuntimeError):
    """Una respuesta HTTP fuera de lo esperado — el recorrido se detiene
    ruidosamente (mismo espíritu que ADR-0004 E-2: nunca fallar en silencio)."""


def verificar_servidor_activo(base_url: str = BASE_URL) -> None:
    try:
        resp = requests.get(f"{base_url}/docs", timeout=3)
    except requests.exceptions.ConnectionError as exc:
        raise FalloE2E(
            f"No hay servidor en {base_url}. Arráncalo primero:\n"
            f"  cd backend && PYTHONPATH=.:runtime uvicorn app.main:app --port 8000"
        ) from exc
    if resp.status_code != 200:
        raise FalloE2E(f"Servidor en {base_url} respondió {resp.status_code} en /docs")


class ClienteE2E:
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self._sesion = requests.Session()

    def login(self, identifier: str, password: str) -> dict:
        resp = self._sesion.post(
            f"{self.base_url}/api/auth/login",
            json={"identifier": identifier, "password": password},
        )
        self._exigir(resp, 200, "login")
        cuerpo = resp.json()
        self._sesion.headers["Authorization"] = f"Bearer {cuerpo['access_token']}"
        return cuerpo["user"]

    def abrir_sesion(self, session_id: str) -> dict:
        resp = self._sesion.post(
            f"{self.base_url}/api/runtime/sessions", json={"session_id": session_id}
        )
        self._exigir(resp, 200, "abrir_sesion")
        return resp.json()

    def registrar_hecho(
        self,
        identidad: dict,
        contenido: dict,
        origen: str = "instrumento",
        cerrar_sesion: bool = False,
    ) -> dict:
        resp = self._sesion.post(
            f"{self.base_url}/api/runtime/hechos",
            json={
                "identidad": identidad,
                "contenido": contenido,
                "origen": origen,
                "cerrar_sesion": cerrar_sesion,
            },
        )
        self._exigir(resp, 200, "registrar_hecho")
        return resp.json()

    def traza(self, session_id: str) -> list:
        return self._get(f"/api/runtime/sessions/{session_id}/traza")

    def estado(self, session_id: str) -> dict:
        return self._get(f"/api/runtime/sessions/{session_id}/estado")

    def memoria(self, session_id: str) -> dict | None:
        return self._get(f"/api/runtime/sessions/{session_id}/memoria")

    def replay(self, session_id: str) -> list:
        return self._get(f"/api/runtime/sessions/{session_id}/replay")

    def hecho_docente(
        self, session_id: str, contenido: dict, human_reason: str | None = None
    ) -> dict:
        resp = self._sesion.post(
            f"{self.base_url}/api/runtime/sessions/{session_id}/hechos-docente",
            json={"contenido": contenido, "human_reason": human_reason},
        )
        self._exigir(resp, 200, "hecho_docente")
        return resp.json()

    def resolver_escalada(
        self,
        session_id: str,
        escalada_id: str,
        claim_elegido: str,
        human_reason: str | None = None,
    ) -> dict:
        resp = self._sesion.post(
            f"{self.base_url}/api/runtime/sessions/{session_id}/escaladas/resolver",
            json={
                "escalada_id": escalada_id,
                "claim_elegido": claim_elegido,
                "human_reason": human_reason,
            },
        )
        self._exigir(resp, 200, "resolver_escalada")
        return resp.json()

    def listar_cursos(self) -> list[dict]:
        """`GET /api/courses` — consumidor de PLATAFORMA, no de
        `/api/runtime/*` directamente: un docente ve solo sus cursos."""
        return self._get("/api/courses")["courses"]

    def sugerencia_semanal(self, course_id: str) -> dict:
        """`GET /api/pedagogy/courses/{id}/weekly-plans/suggestions` —
        Plataforma Operativa 2 (Inteligencia Docente): lee la decisión
        vigente del Runtime para todo el roster vía
        `runtime_bridge.consultar_decision_vigente` (S1/S3, RFC-0010).
        Prueba la cadena real: Backend HTTP → Boundary → Runtime →
        Persistencia → Respuesta, sin pasar por `/api/runtime/*`."""
        return self._get(f"/api/pedagogy/courses/{course_id}/weekly-plans/suggestions")

    def _get(self, path: str) -> Any:
        resp = self._sesion.get(f"{self.base_url}{path}")
        self._exigir(resp, 200, path)
        return resp.json()

    def _exigir(self, resp: requests.Response, esperado: int, etiqueta: str) -> None:
        if resp.status_code != esperado:
            raise FalloE2E(
                f"{etiqueta}: esperaba {esperado}, recibió {resp.status_code} — {resp.text}"
            )
