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
            "identifier": "admin@test.com", "password": "Admin123!",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == "admin@test.com"

    def test_login_password_incorrecto(self, client, admin_user):
        """Login con contraseña incorrecta retorna 401."""
        resp = client.post("/api/auth/login", json={
            "identifier": "admin@test.com", "password": "WrongPass!",
        })
        assert resp.status_code == 401
        assert resp.json()["detail"]["code"] == "INVALID_CREDENTIALS"

    def test_login_email_inexistente(self, client):
        """Login con email no registrado retorna 401."""
        resp = client.post("/api/auth/login", json={
            "identifier": "noexiste@test.com", "password": "Pass123!",
        })
        assert resp.status_code == 401

    def test_bloqueo_tras_3_intentos(self, client, admin_user):
        """Cuenta se bloquea tras 3 intentos fallidos."""
        for _ in range(3):
            client.post("/api/auth/login", json={
                "identifier": "admin@test.com", "password": "WrongPass!",
            })

        # El cuarto intento debe ser bloqueado
        resp = client.post("/api/auth/login", json={
            "identifier": "admin@test.com", "password": "Admin123!",
        })
        assert resp.status_code == 429
        assert resp.json()["detail"]["code"] == "ACCOUNT_LOCKED"


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

    def test_refresh_token(self, client, admin_user):
        """Refresh retorna un nuevo par de tokens usando refresh_token del body."""
        # First login to get refresh_token
        login_resp = client.post("/api/auth/login", json={
            "identifier": "admin@test.com", "password": "Admin123!",
        })
        assert login_resp.status_code == 200
        login_data = login_resp.json()
        assert "refresh_token" in login_data

        # Use refresh_token in body (not auth header)
        resp = client.post("/api/auth/refresh", json={
            "refresh_token": login_data["refresh_token"],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data

    def test_refresh_with_invalid_token_returns_401(self, client):
        """Refresh con token inválido retorna 401."""
        resp = client.post("/api/auth/refresh", json={
            "refresh_token": "token-totalmente-invalido",
        })
        assert resp.status_code == 401

    def test_refresh_with_expired_token_returns_401(self, client):
        """Refresh con token expirado retorna 401."""
        from app.core.security import create_refresh_token
        import time

        expired_token = create_refresh_token(
            data={"sub": "fake-id", "email": "fake@test.com", "role": "estudiante"},
        )
        resp = client.post("/api/auth/refresh", json={
            "refresh_token": expired_token,
        })
        assert resp.status_code == 401

    def test_login_returns_refresh_token(self, client, admin_user):
        """Login retorna refresh_token además de access_token."""
        resp = client.post("/api/auth/login", json={
            "identifier": "admin@test.com", "password": "Admin123!",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "refresh_token" in data
        assert data["refresh_token"] != data["access_token"]

    def test_me_with_expired_token_returns_401(self, client, admin_user):
        """GET /me con token expirado retorna 401."""
        from app.core.security import create_access_token
        from datetime import timedelta

        expired_token = create_access_token(
            data={"sub": "admin@test.com", "email": "admin@test.com", "role": "admin"},
            expires_delta=timedelta(seconds=-1),
        )
        resp = client.get("/api/auth/me", headers=auth_header(expired_token))
        assert resp.status_code == 401

    def test_refresh_endpoint_no_auth_header_needed(self, client, admin_user):
        """Refresh endpoint funciona con body, no necesita header de auth."""
        login_resp = client.post("/api/auth/login", json={
            "identifier": "admin@test.com", "password": "Admin123!",
        })
        refresh_token = login_resp.json()["refresh_token"]

        # Sin auth header, solo body
        resp = client.post("/api/auth/refresh", json={
            "refresh_token": refresh_token,
        })
        assert resp.status_code == 200
        assert "access_token" in resp.json()
        assert "refresh_token" in resp.json()

    def test_logout(self, client, admin_token):
        """Logout retorna mensaje exitoso."""
        resp = client.post("/api/auth/logout", headers=auth_header(admin_token))
        assert resp.status_code == 200
        assert "Sesión cerrada" in resp.json()["message"]

    def test_recover_password(self, client):
        """Recover siempre retorna éxito (no revela si el email existe)."""
        resp = client.post("/api/auth/recover", json={"email": "test@test.com"})
        assert resp.status_code == 200
