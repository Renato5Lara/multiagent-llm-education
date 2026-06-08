"""
Integration tests for the complete student flow:
- Login rate limiting
- Enrollment activation
- Module entry + session creation
- Content viewer
- Progress tracking
"""
import threading
import time
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from app.middleware.rate_limit import AuthRateLimiter
from app.services.session_service import start_module_session, end_session


# ═══════════════════════════════════════════════════════════════
# RATE LIMITER TESTS
# ═══════════════════════════════════════════════════════════════


class TestAuthRateLimiter:
    def test_allows_within_limit(self):
        limiter = AuthRateLimiter(max_requests=3, window_seconds=60)
        for _ in range(3):
            assert limiter.is_allowed("192.168.1.1") is True
            limiter.increment("192.168.1.1")

    def test_blocks_exceeding_limit(self):
        limiter = AuthRateLimiter(max_requests=3, window_seconds=60)
        for _ in range(3):
            assert limiter.is_allowed("10.0.0.1") is True
            limiter.increment("10.0.0.1")
        assert limiter.is_allowed("10.0.0.1") is False
        assert limiter.get_remaining("10.0.0.1") == 0

    def test_different_ips_independent(self):
        limiter = AuthRateLimiter(max_requests=2, window_seconds=60)
        for _ in range(2):
            assert limiter.is_allowed("A") is True
            limiter.increment("A")
        assert limiter.is_allowed("A") is False
        assert limiter.is_allowed("B") is True  # Different IP not affected

    def test_window_expires(self):
        limiter = AuthRateLimiter(max_requests=2, window_seconds=0.1)
        assert limiter.is_allowed("expire-test") is True
        limiter.increment("expire-test")
        assert limiter.is_allowed("expire-test") is True
        limiter.increment("expire-test")
        assert limiter.is_allowed("expire-test") is False
        time.sleep(0.15)
        assert limiter.is_allowed("expire-test") is True  # Window expired


# ═══════════════════════════════════════════════════════════════
# LEARNING SESSION TESTS
# ═══════════════════════════════════════════════════════════════


def test_learning_session_end():
    """Test end_session calculates duration properly without DB."""
    from app.models.learning_session import LearningSession
    from datetime import datetime, timedelta, timezone

    session = LearningSession(
        id="test-end",
        student_id="s1",
        course_id="c1",
        status="active",
        started_at=datetime.now(timezone.utc) - timedelta(minutes=5),
    )
    session.end()
    assert session.status == "completed"
    assert session.ended_at is not None
    assert session.duration_minutes > 0
    assert round(session.duration_minutes) >= 5


def test_rate_limiter_thread_safety():
    """Test that rate limiter works correctly with concurrent requests."""
    limiter = AuthRateLimiter(max_requests=50, window_seconds=60)
    results = []
    errors = []

    def attempt(ip: str):
        try:
            if limiter.is_allowed(ip):
                results.append(True)
                limiter.increment(ip)
            else:
                results.append(False)
        except Exception as e:
            errors.append(e)

    threads = []
    for _ in range(100):
        t = threading.Thread(target=attempt, args=("thread-ip",))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    assert len(errors) == 0
    # 50 should pass, 50 should be blocked
    assert sum(results) == 50
    assert len(results) == 100


# ═══════════════════════════════════════════════════════════════
# START MODULE SESSION TESTS
# ═══════════════════════════════════════════════════════════════


def test_start_module_session_no_module(db):
    pytest.skip("DB-002: session_service is async; needs async def test")


def test_start_module_session_not_owned(db):
    pytest.skip("DB-002: session_service is async; needs async def test")


def test_end_session_not_found():
    """Should fail gracefully when session doesn't exist."""
    pytest.skip("DB-002: session_service is async; needs async def test")
