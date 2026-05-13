"""
Tests de CRUD de usuarios.
Cubre: listar, crear, obtener, actualizar, eliminar, bulk CSV, cambio de rol.
"""

from tests.conftest import auth_header


class TestUserCRUD:
    """Tests CRUD de usuarios."""

    def test_listar_usuarios(self, client, admin_token):
        resp = client.get("/api/users", headers=auth_header(admin_token))
        assert resp.status_code == 200
        data = resp.json()
        assert "users" in data
        assert "total" in data

    def test_crear_usuario(self, client, admin_token):
        resp = client.post("/api/users", headers=auth_header(admin_token), json={
            "email": "nuevo@test.com", "password": "Nuevo123!",
            "first_name": "Nuevo", "last_name": "Usuario", "role": "estudiante",
        })
        assert resp.status_code == 201
        assert resp.json()["email"] == "nuevo@test.com"

    def test_crear_usuario_email_duplicado(self, client, admin_token, admin_user):
        resp = client.post("/api/users", headers=auth_header(admin_token), json={
            "email": "admin@test.com", "password": "Pass123!",
            "first_name": "Dup", "last_name": "User", "role": "estudiante",
        })
        assert resp.status_code == 409

    def test_obtener_usuario(self, client, admin_token, admin_user):
        resp = client.get(f"/api/users/{admin_user.id}", headers=auth_header(admin_token))
        assert resp.status_code == 200
        assert resp.json()["email"] == "admin@test.com"

    def test_obtener_usuario_inexistente(self, client, admin_token):
        resp = client.get("/api/users/id-no-existe", headers=auth_header(admin_token))
        assert resp.status_code == 404

    def test_actualizar_usuario(self, client, admin_token, docente_user):
        resp = client.put(f"/api/users/{docente_user.id}", headers=auth_header(admin_token), json={
            "first_name": "Actualizado",
        })
        assert resp.status_code == 200
        assert resp.json()["first_name"] == "Actualizado"

    def test_eliminar_usuario(self, client, admin_token, docente_user):
        resp = client.delete(f"/api/users/{docente_user.id}", headers=auth_header(admin_token))
        assert resp.status_code == 200
        assert resp.json()["is_active"] is False

    def test_no_eliminar_a_si_mismo(self, client, admin_token, admin_user):
        resp = client.delete(f"/api/users/{admin_user.id}", headers=auth_header(admin_token))
        assert resp.status_code == 400

    def test_filtrar_por_rol(self, client, admin_token, docente_user):
        resp = client.get("/api/users?role=docente", headers=auth_header(admin_token))
        assert resp.status_code == 200
        users = resp.json()["users"]
        assert all(u["role"] == "docente" for u in users)


class TestBulkCSV:
    """Tests de carga masiva CSV."""

    def test_bulk_csv_exitoso(self, client, admin_token):
        csv_content = "email,first_name,last_name,role,institutional_code\n"
        csv_content += "bulk1@test.com,Ana,García,estudiante,EST001\n"
        csv_content += "bulk2@test.com,Carlos,López,estudiante,EST002\n"

        import io
        files = {"file": ("users.csv", io.BytesIO(csv_content.encode()), "text/csv")}
        resp = client.post("/api/users/bulk", headers=auth_header(admin_token), files=files)
        assert resp.status_code == 201
        assert resp.json()["success"] == 2

    def test_bulk_csv_con_errores(self, client, admin_token):
        csv_content = "email,first_name,last_name,role,institutional_code\n"
        csv_content += "err1@test.com,Ana,García,rol_invalido,EST001\n"

        import io
        files = {"file": ("users.csv", io.BytesIO(csv_content.encode()), "text/csv")}
        resp = client.post("/api/users/bulk", headers=auth_header(admin_token), files=files)
        assert resp.status_code == 201
        assert len(resp.json()["errors"]) > 0


class TestCambioRol:
    """Tests de cambio de rol."""

    def test_cambiar_rol(self, client, admin_token, docente_user):
        resp = client.patch(
            f"/api/users/{docente_user.id}/role",
            headers=auth_header(admin_token),
            json={"role": "investigador"},
        )
        assert resp.status_code == 200
        assert resp.json()["role"] == "investigador"

    def test_no_admin_no_puede_cambiar_rol(self, client, docente_token, admin_user):
        resp = client.patch(
            f"/api/users/{admin_user.id}/role",
            headers=auth_header(docente_token),
            json={"role": "estudiante"},
        )
        assert resp.status_code == 403
