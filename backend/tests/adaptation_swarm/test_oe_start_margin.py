"""Regresión: la duración total de Locust = warmup + window + start_margin. El margen por defecto (5 s) conserva el comportamiento histórico (campañas N2/N4);
ampliarlo no cambia los umbrales de ventana (≥ 10 s de calentamiento, ≥ 60 s de ventana) y permite que una primera respuesta lenta (> 5 s) no invalide la corrida."""
import subprocess
from pathlib import Path

import pytest

from adaptation_swarm.oe import http_campaign as hc
from adaptation_swarm.oe import http_window


def _capture_total(monkeypatch, **kw):
    seen = []
    monkeypatch.setattr(hc.subprocess, "run", lambda cmd, env=None, **k: seen.append(cmd[cmd.index("-t") + 1]) or subprocess.CompletedProcess(cmd, 0))
    monkeypatch.setattr(hc.http_window, "read_raw", lambda p: [])
    monkeypatch.setattr(hc.http_window, "read_cpu", lambda p: [])
    run = hc.locust_runner("http://x", Path("l.py"), Path("p.py"), Path("."), "python", **kw)
    run({"run_id": "r", "seed": 1, "system": "swarm", "load": 1}, 10.0, 60.0)
    return seen[0]


def test_default_margin_keeps_historical_total_duration(monkeypatch):
    assert _capture_total(monkeypatch) == "75s"


def test_wider_margin_extends_only_total_duration(monkeypatch):
    assert _capture_total(monkeypatch, start_margin_s=20.0) == "90s"
    assert http_window.WARMUP_S_MIN == 10.0 and http_window.WINDOW_S_MIN == 60.0


@pytest.mark.parametrize("first_response_s, margin, expect_valid", [(8.0, 5.0, False), (8.0, 20.0, True)])
def test_slow_first_response_needs_margin_for_the_minimum_window(first_response_s, margin, expect_valid):
    total = 10.0 + 60.0 + margin
    raw = [{"t_end_epoch_s": 1000.0 + first_response_s + i, "response_ms": 100.0, "ok": True, "timeout": False, "t_conv_ms": None, "metrics_ok": True, "error_kind": "",
            "decision_ms": None, "profile_id": None, "user_index": None, "seq_pos": None} for i in range(int(total - first_response_s))]
    out = http_window.summarize_run(raw, [], users=100, system="swarm", run_id="r")
    assert (out.get("status") != "invalid_window_shorter_than_min") is expect_valid
