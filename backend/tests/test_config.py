"""
Tests de configuración y manejo de API keys.
Cubre: carga de variables, secretos en logs, degraded mode, health endpoint.
"""

import pytest

from app.core.config import Settings, _mask_key


@pytest.fixture(autouse=True)
def _clear_real_api_key_env(monkeypatch):
    """Some import in the collection chain (runtime.domain.shared.llm_openai)
    calls load_dotenv() at module scope, leaking backend/.env's real keys into
    os.environ for the whole pytest session. _env_file=None alone doesn't
    cover that since it only skips pydantic's own .env read."""
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)


class TestMaskKey:
    def test_empty_key(self):
        assert _mask_key("") == "<empty>"

    def test_short_key(self):
        assert _mask_key("abc") == "<too-short>"

    def test_masked_key(self):
        result = _mask_key("sk-1234567890abcdef")
        assert "sk-12345" in result
        assert "cdef" in result
        assert "1234567890abcdef" not in result


class TestSettingsApiKeys:
    def test_default_keys_are_empty(self):
        s = Settings(ENV="testing", _env_file=None)
        assert s.TAVILY_API_KEY == ""
        assert s.OPENAI_API_KEY == ""
        assert s.has_tavily is False
        assert s.has_openai is False
        assert s.has_llm is False

    def test_has_tavily_true(self):
        s = Settings(TAVILY_API_KEY="tvly-abc123", _env_file=None)
        assert s.has_tavily is True

    def test_has_openai_true(self):
        s = Settings(OPENAI_API_KEY="sk-abc123", _env_file=None)
        assert s.has_openai is True
        assert s.has_llm is True

    def test_has_tavily_whitespace_only(self):
        s = Settings(TAVILY_API_KEY="   ", _env_file=None)
        assert s.has_tavily is False


class TestSecretsSummary:
    def test_summary_missing(self):
        s = Settings(ENV="testing", _env_file=None)
        summary = s.secrets_summary()
        assert summary["tavily"] == "missing"
        assert summary["openai"] == "missing"
        assert "<empty>" in summary["tavily_key_preview"]

    def test_summary_configured(self):
        s = Settings(TAVILY_API_KEY="tvly-abcdef123456", OPENAI_API_KEY="sk-abcdef123456", _env_file=None)
        summary = s.secrets_summary()
        assert summary["tavily"] == "configured"
        assert summary["openai"] == "configured"
        assert "tvly-" in summary["tavily_key_preview"]
        assert "3456" in summary["openai_key_preview"]


class TestValidateApiKeys:
    def test_warnings_when_missing(self):
        s = Settings(ENV="testing", _env_file=None)
        warnings = s.validate_api_keys()
        assert len(warnings) == 2
        assert any("TAVILY_API_KEY" in w for w in warnings)
        assert any("OPENAI_API_KEY" in w for w in warnings)

    def test_no_warnings_when_configured(self):
        s = Settings(
            TAVILY_API_KEY="tvly-abc123",
            OPENAI_API_KEY="sk-abc123",
            _env_file=None,
        )
        warnings = s.validate_api_keys()
        assert len(warnings) == 0

    def test_warning_for_missing_tavily_only(self):
        s = Settings(OPENAI_API_KEY="sk-abc123", _env_file=None)
        warnings = s.validate_api_keys()
        assert len(warnings) == 1
        assert "TAVILY_API_KEY" in warnings[0]


class TestAvailableModalities:
    def test_both_missing(self):
        s = Settings(ENV="testing", _env_file=None)
        assert s.available_modalities == ["deterministic_fallback"]

    def test_tavily_only(self):
        s = Settings(TAVILY_API_KEY="tvly-abc", _env_file=None)
        assert "web_search" in s.available_modalities
        assert "llm_generation" not in s.available_modalities
        assert "deterministic_fallback" in s.available_modalities

    def test_both_configured(self):
        s = Settings(TAVILY_API_KEY="tvly-abc", OPENAI_API_KEY="sk-abc", _env_file=None)
        assert "web_search" in s.available_modalities
        assert "llm_generation" in s.available_modalities
        assert "deterministic_fallback" in s.available_modalities


class TestHealthEndpoint:
    def test_health_returns_degraded_without_keys(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data
        assert "tavily" in data
        assert "openai" in data
        assert "modalities" in data
        assert "deterministic_fallback" in data["modalities"]

    def test_health_includes_api_key_status(self, client):
        resp = client.get("/health")
        data = resp.json()
        assert data["tavily"] in ("available", "missing")
        assert data["openai"] in ("available", "missing")
