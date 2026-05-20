"""
Tests de recursos educativos.
Cubre: upload válido, tipo no permitido, tamaño excedido, download.
"""

import io
from tests.conftest import auth_header


class TestResourceUpload:
    """Tests de subida de recursos."""

    def _create_course(self, client, token):
        resp = client.post("/api/courses", headers=auth_header(token), json={
            "code": "RES-01", "name": "Curso Recursos", "cycle": 1, "year": 2026,
        })
        return resp.json()["id"]

    def test_upload_pdf_valido(self, client, docente_token):
        cid = self._create_course(client, docente_token)
        file_content = b"%PDF-1.4 test content"
        files = {"file": ("test.pdf", io.BytesIO(file_content), "application/pdf")}
        resp = client.post(
            f"/api/courses/{cid}/resources",
            headers=auth_header(docente_token),
            files=files,
        )
        assert resp.status_code == 201
        assert resp.json()["original_filename"] == "test.pdf"
        assert resp.json()["resource_type"] == "pdf"

    def test_upload_tipo_no_permitido(self, client, docente_token):
        cid = self._create_course(client, docente_token)
        files = {"file": ("malware.exe", io.BytesIO(b"bad"), "application/x-executable")}
        resp = client.post(
            f"/api/courses/{cid}/resources",
            headers=auth_header(docente_token),
            files=files,
        )
        assert resp.status_code == 400
        assert "no permitido" in resp.json()["detail"].lower()

    def test_upload_excede_tamano(self, client, docente_token, monkeypatch):
        """Simula un archivo que excede el tamaño máximo."""
        # Reducir el límite para el test
        from app.core import config
        monkeypatch.setattr(config.settings, "MAX_UPLOAD_SIZE_MB", 0)

        cid = self._create_course(client, docente_token)
        files = {"file": ("big.pdf", io.BytesIO(b"%PDF" + b"x" * 1024), "application/pdf")}
        resp = client.post(
            f"/api/courses/{cid}/resources",
            headers=auth_header(docente_token),
            files=files,
        )
        assert resp.status_code == 400
        assert "tamaño" in resp.json()["detail"].lower()


class TestResourceDownload:
    """Tests de descarga de recursos."""

    def test_download_recurso_existente(self, client, docente_token):
        # Crear curso y subir recurso
        resp = client.post("/api/courses", headers=auth_header(docente_token), json={
            "code": "DL-01", "name": "Curso Download", "cycle": 1, "year": 2026,
        })
        cid = resp.json()["id"]

        file_content = b"%PDF-1.4 downloadable content"
        files = {"file": ("download.pdf", io.BytesIO(file_content), "application/pdf")}
        upload_resp = client.post(
            f"/api/courses/{cid}/resources",
            headers=auth_header(docente_token),
            files=files,
        )
        rid = upload_resp.json()["id"]

        # Descargar
        dl_resp = client.get(f"/api/resources/{rid}/download", headers=auth_header(docente_token))
        assert dl_resp.status_code == 200

    def test_download_recurso_inexistente(self, client, docente_token):
        resp = client.get("/api/resources/no-existe/download", headers=auth_header(docente_token))
        assert resp.status_code == 404


class TestResourceDelete:
    """Tests de eliminación de recursos."""

    def test_eliminar_recurso(self, client, docente_token):
        resp = client.post("/api/courses", headers=auth_header(docente_token), json={
            "code": "DEL-01", "name": "Curso Delete", "cycle": 1, "year": 2026,
        })
        cid = resp.json()["id"]

        files = {"file": ("delete_me.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")}
        upload = client.post(f"/api/courses/{cid}/resources", headers=auth_header(docente_token), files=files)
        rid = upload.json()["id"]

        del_resp = client.delete(f"/api/resources/{rid}", headers=auth_header(docente_token))
        assert del_resp.status_code == 204
