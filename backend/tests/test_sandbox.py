from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from app.agents.programmer_agent import ProgrammerAgent
from app.agents.reviewer_agent import ReviewerAgent
from app.sandbox import SandboxLimits, SandboxRequest, SandboxResult, SandboxRunner, SandboxStatus
from app.sandbox.policy import SandboxPolicy


class FakeProcess:
    def __init__(self, stdout: str = "", stderr: str = "", returncode: int = 0):
        self._stdout = stdout.encode("utf-8")
        self._stderr = stderr.encode("utf-8")
        self.returncode = returncode

    async def communicate(self):
        return self._stdout, self._stderr


def sandbox_stdout(payload: dict, visible: str = "") -> str:
    return visible + "\n===SANDBOX_RESULT===" + json.dumps(payload)


class TestSandboxPolicy:
    def test_blocks_dangerous_imports(self):
        violations = SandboxPolicy().validate("import os\nos.system('echo nope')\n")
        assert any(v.rule == "restricted_import" and v.symbol == "os" for v in violations)
        assert any(v.rule == "restricted_call" and v.symbol == "os.system" for v in violations)

    @pytest.mark.parametrize("code,symbol", [
        ("import subprocess\n", "subprocess"),
        ("import socket\n", "socket"),
        ("import requests\n", "requests"),
        ("from urllib import request\n", "urllib"),
        ("import shutil\n", "shutil"),
        ("from pathlib import Path\n", "pathlib"),
        ("import multiprocessing\n", "multiprocessing"),
        ("import builtins\n", "builtins"),
        ("import threading\n", "threading"),
        ("open('x.txt', 'w')\n", "open"),
        ("eval('1 + 1')\n", "eval"),
        ("__import__('os')\n", "__import__"),
        ("globals()\n", "globals"),
        ("getattr([], 'append')\n", "getattr"),
    ])
    def test_blocks_required_security_surface(self, code, symbol):
        violations = SandboxPolicy().validate(code)
        assert any(v.symbol == symbol for v in violations)

    def test_allows_normal_educational_code(self):
        code = "def buscar(xs, x):\n    return xs.index(x) if x in xs else -1\nassert buscar([1, 2], 2) == 1"
        assert SandboxPolicy().validate(code) == []

    def test_reports_syntax_errors_as_violations(self):
        violations = SandboxPolicy().validate("def bad(:\n    pass")
        assert violations[0].rule == "syntax"


class TestSandboxRunner:
    @pytest.mark.asyncio
    async def test_returns_security_violation_before_docker(self):
        runner = SandboxRunner()
        result = await runner.run(SandboxRequest(code="import socket\n"))
        assert result.status == SandboxStatus.SECURITY_VIOLATION
        assert not result.success
        assert result.violations[0].symbol == "socket"

    @pytest.mark.asyncio
    async def test_returns_infrastructure_error_when_docker_missing(self, monkeypatch):
        monkeypatch.setattr("app.sandbox.runner.shutil.which", lambda _: None)
        runner = SandboxRunner()
        result = await runner.run(SandboxRequest(code="print('ok')"))
        assert result.status == SandboxStatus.INFRASTRUCTURE_ERROR
        assert "Docker CLI" in result.stderr

    @pytest.mark.asyncio
    async def test_executes_with_hardened_docker_flags(self, monkeypatch):
        monkeypatch.setattr("app.sandbox.runner.shutil.which", lambda _: "docker")
        captured = {}

        async def fake_create_subprocess_exec(*cmd, **kwargs):
            captured["cmd"] = list(cmd)
            payload = {
                "status": "success",
                "success": True,
                "stdout": "42\n",
                "stderr": "",
                "traceback": "",
                "execution_time_ms": 12.5,
                "memory_usage_mb": 18.25,
                "metrics": {"timeout_seconds": 10},
            }
            return FakeProcess(sandbox_stdout(payload), "", 0)

        monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create_subprocess_exec)
        runner = SandboxRunner(image="sandbox:test")
        result = await runner.run(SandboxRequest(code="print(42)"))

        cmd = captured["cmd"]
        assert result.status == SandboxStatus.SUCCESS
        assert result.success
        assert result.stdout == "42\n"
        assert "--network" in cmd and "none" in cmd
        assert "--memory" in cmd and "512m" in cmd
        assert "--read-only" in cmd
        assert "--cap-drop" in cmd and "ALL" in cmd
        assert "--security-opt" in cmd and "no-new-privileges" in cmd
        assert "--pids-limit" in cmd

    @pytest.mark.asyncio
    async def test_parses_runtime_error_traceback(self, monkeypatch):
        monkeypatch.setattr("app.sandbox.runner.shutil.which", lambda _: "docker")

        async def fake_create_subprocess_exec(*cmd, **kwargs):
            payload = {
                "status": "runtime_error",
                "success": False,
                "stdout": "",
                "stderr": "",
                "traceback": "Traceback: AssertionError",
                "execution_time_ms": 3.0,
                "memory_usage_mb": 10.0,
                "metrics": {},
            }
            return FakeProcess(sandbox_stdout(payload), "", 1)

        monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create_subprocess_exec)
        result = await SandboxRunner().run(SandboxRequest(code="assert False"))
        assert result.status == SandboxStatus.RUNTIME_ERROR
        assert "AssertionError" in result.traceback

    @pytest.mark.asyncio
    async def test_docker_daemon_error_is_infrastructure_error(self, monkeypatch):
        monkeypatch.setattr("app.sandbox.runner.shutil.which", lambda _: "docker")

        async def fake_create_subprocess_exec(*cmd, **kwargs):
            return FakeProcess(
                "",
                "ERROR: failed to connect to the docker API; is the docker daemon running?",
                125,
            )

        monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create_subprocess_exec)
        result = await SandboxRunner().run(SandboxRequest(code="print('ok')"))
        assert result.status == SandboxStatus.INFRASTRUCTURE_ERROR
        assert result.exit_code == 125

    @pytest.mark.asyncio
    async def test_auto_build_failure_is_infrastructure_error(self, monkeypatch):
        monkeypatch.setattr("app.sandbox.runner.shutil.which", lambda _: "docker")

        async def fake_build_image(self):
            raise RuntimeError("Could not build sandbox image: daemon unavailable")

        monkeypatch.setattr(SandboxRunner, "build_image", fake_build_image)
        result = await SandboxRunner(auto_build=True).run(SandboxRequest(code="print('ok')"))

        assert result.status == SandboxStatus.INFRASTRUCTURE_ERROR
        assert not result.success
        assert "daemon unavailable" in result.stderr
        assert result.metadata["sandbox"] == "docker_build_failed"

    @pytest.mark.asyncio
    async def test_host_timeout_kills_container(self, monkeypatch):
        monkeypatch.setattr("app.sandbox.runner.shutil.which", lambda _: "docker")
        calls = []

        async def fake_create_subprocess_exec(*cmd, **kwargs):
            calls.append(list(cmd))
            if "rm" in cmd:
                return FakeProcess("", "", 0)

            class HangingProcess:
                returncode = None

                async def communicate(self):
                    await asyncio.sleep(30)
                    return b"", b""

            return HangingProcess()

        monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create_subprocess_exec)
        result = await SandboxRunner().run(
            SandboxRequest(code="while True:\n    pass", limits=SandboxLimits(timeout_seconds=1))
        )
        assert result.status == SandboxStatus.TIMEOUT
        assert result.timed_out
        assert any("rm" in cmd for cmd in calls)

    def test_dockerfile_contains_defense_in_depth_controls(self):
        dockerfile = Path("app/sandbox/docker/Dockerfile")
        content = dockerfile.read_text(encoding="utf-8")
        assert "USER sandbox:sandbox" in content
        assert "PYTHONDONTWRITEBYTECODE" in content


class TestSandboxApi:
    def test_stream_endpoint_emits_observable_lifecycle(self, client, monkeypatch):
        async def fake_run(request):
            return SandboxResult(
                status=SandboxStatus.SUCCESS,
                success=True,
                stdout="ok\n",
                execution_time_ms=1.5,
                memory_usage_mb=12.0,
                metadata=request.metadata,
            )

        monkeypatch.setattr("app.api.routes.sandbox.runner.run", fake_run)

        with client.stream(
            "POST",
            "/api/sandbox/execute/stream",
            json={"code": "print('ok')", "metadata": {"trace_id": "t-sandbox"}},
        ) as response:
            body = response.read().decode("utf-8")

        assert response.status_code == 200
        assert "event: sandbox.start" in body
        assert "event: sandbox.complete" in body
        assert '"success": true' in body
        assert "t-sandbox" in body


class TestProgrammerReviewerLoop:
    @pytest.mark.asyncio
    async def test_reviewer_approves_valid_programmer_code(self):
        sandbox = AsyncMock()
        sandbox.run.return_value.status = SandboxStatus.SUCCESS
        sandbox.run.return_value.success = True
        sandbox.run.return_value.to_replay_payload.return_value = {"status": "success", "success": True}

        reviewer = ReviewerAgent(sandbox=sandbox, programmer=ProgrammerAgent())
        result = await reviewer.review_until_validated(
            topic="Arreglos en programacion",
            objectives=["comprender recorrido", "comprender busqueda", "comprender insercion"],
        )
        assert result.approved
        assert len(result.iterations) == 1
        assert "def recorrer" in result.final_code

    @pytest.mark.asyncio
    async def test_reviewer_caps_iterations_at_four(self):
        sandbox = AsyncMock()
        sandbox_result = AsyncMock()
        sandbox_result.status = SandboxStatus.RUNTIME_ERROR
        sandbox_result.success = False
        sandbox_result.traceback = "AssertionError"
        sandbox_result.stderr = ""
        sandbox_result.to_replay_payload.return_value = {"status": "runtime_error", "success": False}
        sandbox.run.return_value = sandbox_result

        reviewer = ReviewerAgent(sandbox=sandbox, programmer=ProgrammerAgent(), max_iterations=99)
        result = await reviewer.review_until_validated(topic="Arreglos", objectives=[])
        assert not result.approved
        assert len(result.iterations) == 4
