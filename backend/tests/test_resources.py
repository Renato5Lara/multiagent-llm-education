"""
Tests de recursos legacy.
La arquitectura docente actual no permite subida ni gestion manual de contenido.
"""

import io

from tests.conftest import auth_header


class TestLegacyResourceWorkflowDisabled:
    def _create_course(self, client, token):
        resp = client.post("/api/courses", headers=auth_header(token), json={
            "code": "RES-01", "name": "Curso Recursos", "cycle": 1, "year": 2026,
        })
        return resp.json()["id"]

    def test_upload_manual_desactivado(self, client, docente_token):
        cid = self._create_course(client, docente_token)
        files = {"file": ("test.pdf", io.BytesIO(b"%PDF-1.4 test content"), "application/pdf")}
        resp = client.post(
            f"/api/courses/{cid}/resources",
            headers=auth_header(docente_token),
            files=files,
        )
        assert resp.status_code == 410
        assert "Pedagogical Swarm Orchestration" in resp.json()["detail"]

    def test_download_recurso_inexistente(self, client, docente_token):
        resp = client.get("/api/resources/no-existe/download", headers=auth_header(docente_token))
        assert resp.status_code == 404

    def test_eliminacion_manual_desactivada(self, client, docente_token):
        resp = client.delete("/api/resources/no-existe", headers=auth_header(docente_token))
        assert resp.status_code == 410

    def test_asociacion_manual_desactivada(self, client, docente_token):
        resp = client.post(
            "/api/resources/no-existe/objectives",
            headers=auth_header(docente_token),
            json={"objective_ids": ["obj-1"], "relevance_score": 1.0},
        )
        assert resp.status_code == 410
