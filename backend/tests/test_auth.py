"""
Tests de autenticación.
Cubre: login exitoso, login fallido, bloqueo tras 3 intentos, get_me.
"""

from tests.conftest import auth_header


class TestLogin:
    """Tests para el endpoint POST /api/auth/login."""

    def test_login_exitoso(self, client, admin_user):
        """Login con credenciales correctas retorna token."""
        resp = client.post("/api/auth/login", json={
            "email": "admin@test.com", "password": "Admin123!",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == "admin@test.com"

    def test_login_password_incorrecto(self, client, admin_user):
        """Login con contraseña incorrecta retorna 401."""
        resp = client.post("/api/auth/login", json={
            "email": "admin@test.com", "password": "WrongPass!",
        })
        assert resp.status_code == 401
        assert "Credenciales incorrectas" in resp.json()["detail"]

    def test_login_email_inexistente(self, client):
        """Login con email no registrado retorna 401."""
        resp = client.post("/api/auth/login", json={
            "email": "noexiste@test.com", "password": "Pass123!",
        })
        assert resp.status_code == 401

    def test_bloqueo_tras_3_intentos(self, client, admin_user):
        """Cuenta se bloquea tras 3 intentos fallidos."""
        for _ in range(3):
            client.post("/api/auth/login", json={
                "email": "admin@test.com", "password": "WrongPass!",
            })

        # El cuarto intento debe ser bloqueado
        resp = client.post("/api/auth/login", json={
            "email": "admin@test.com", "password": "Admin123!",
        })
        assert resp.status_code == 429
        assert "bloqueada" in resp.json()["detail"].lower()


class TestMe:
    """Tests para el endpoint GET /api/auth/me."""

    def test_get_me_autenticado(self, client, admin_token):
        """Retorna datos del usuario autenticado."""
        resp = client.get("/api/auth/me", headers=auth_header(admin_token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "admin@test.com"
        assert data["role"] == "admin"

    def test_get_me_sin_token(self, client):
        """Sin token retorna 401."""
        resp = client.get("/api/auth/me")
        assert resp.status_code == 401

    def test_get_me_token_invalido(self, client):
        """Con token inválido retorna 401."""
        resp = client.get("/api/auth/me", headers=auth_header("token-falso"))
        assert resp.status_code == 401


class TestRefreshLogout:
    """Tests para refresh y logout."""

    def test_refresh_token(self, client, admin_token):
        """Refresh retorna un nuevo token válido."""
        resp = client.post("/api/auth/refresh", headers=auth_header(admin_token))
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    def test_logout(self, client, admin_token):
        """Logout retorna mensaje exitoso."""
        resp = client.post("/api/auth/logout", headers=auth_header(admin_token))
        assert resp.status_code == 200
        assert "Sesión cerrada" in resp.json()["message"]

    def test_recover_password(self, client):
        """Recover siempre retorna éxito (no revela si el email existe)."""
        resp = client.post("/api/auth/recover", json={"email": "test@test.com"})
        assert resp.status_code == 200
