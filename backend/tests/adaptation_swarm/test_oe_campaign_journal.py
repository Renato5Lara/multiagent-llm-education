"""Persistencia incremental de las campañas HTTP (diario `RunJournal`): cada corrida terminada queda en disco de forma atómica; una interrupción no pierde lo ya medido;
reanudar no duplica ni vuelve a medir; los fallos se registran con su estado. Sin servicios: do_run y ensure_server son simulados (los datos simulados NO son resultados)."""
import argparse
import json

import pytest

from adaptation_swarm.oe import http_campaign as hc

IDS = [f"p{i}" for i in range(100)]


def _runs():
    return hc.plan("oe2", runs=2, base_seed=1, users=[1], particles=[20], systems=["swarm", "decision_table"], order="sequential", campaign_id="J", profile_ids=IDS)


def _prov(runs):
    args = argparse.Namespace(experiment="oe2", campaign_id="J", runs=2, users=[1], particles=[20], systems=["swarm", "decision_table"], warmup=10.0, window=60.0, base_seed=1, order="sequential",
                              persist_policy="off", official=False)
    return hc.provenance(args, runs)


def _ok_run(r, w, win):
    rows = [{"t_end_epoch_s": 1000 + i / 10, "response_ms": 100.0, "ok": True, "timeout": False, "error_kind": "", "decision_ms": 1.0, "t_conv_ms": 1.0 if r["system"] == "swarm" else None,
             "metrics_ok": True, "profile_id": IDS[i % 100], "user_index": 0, "seq_pos": i} for i in range(900)]
    return rows, [{"t_epoch_s": 1000.0 + s, "loadgen_cpu_percent": 20.0} for s in range(95)]


def _execute(runs, prov, journal, do_run=_ok_run, done=None):
    return hc.execute(runs, prov, warmup=10, window=60, do_run=do_run, ensure_server=lambda n, p: None, log=lambda m: None, profile_ids=IDS, journal=journal, done=done)


def test_every_finished_run_is_written_to_disk_before_the_next_one_starts(tmp_path):
    runs = _runs()
    j = hc.RunJournal(tmp_path / "c.journal", "J")
    seen = []

    def do_run(r, w, win):
        seen.append(len(j.entries()))                 # entradas ya en disco cuando empieza esta corrida
        return _ok_run(r, w, win)
    _execute(runs, _prov(runs), j, do_run)
    assert seen == list(range(len(runs)))             # 0, 1, 2, 3: lo anterior ya estaba persistido
    assert [e["state"] for e in j.entries()] == ["completed"] * len(runs)
    assert j.summary()["final_state_counts"]["completed"] == len(runs)


def test_an_interruption_keeps_everything_measured_and_marks_the_run_in_progress(tmp_path):
    runs = _runs()
    j = hc.RunJournal(tmp_path / "c.journal", "J")
    calls = []

    def do_run(r, w, win):
        calls.append(r["run_id"])
        if len(calls) == 3:
            raise KeyboardInterrupt("corte")
        return _ok_run(r, w, win)
    with pytest.raises(KeyboardInterrupt):
        _execute(runs, _prov(runs), j, do_run)
    states = [(e["run_id"], e["state"]) for e in j.entries()]
    assert [s for _, s in states] == ["completed", "completed", "interrupted"]
    assert set(j.reusable()) == {runs[0]["run_id"], runs[1]["run_id"]}              # las 2 medidas se pueden recuperar con su registro completo
    assert all("p95_ms" in rec for rec in j.reusable().values())


def test_a_failed_load_is_recorded_and_the_campaign_continues(tmp_path):
    runs = _runs()
    j = hc.RunJournal(tmp_path / "c.journal", "J")

    def do_run(r, w, win):
        if r["run_id"] == runs[1]["run_id"]:
            raise RuntimeError("locust exit 1")
        return _ok_run(r, w, win)
    recs = _execute(runs, _prov(runs), j, do_run)
    assert len(recs) == len(runs) - 1                                              # la fallida no inventa registro
    s = j.summary()
    assert s["final_state_counts"]["failed"] == 1 and s["failed_run_ids"] == [runs[1]["run_id"]]


def test_resume_reuses_measured_runs_without_duplicates_and_reruns_only_the_missing(tmp_path):
    runs = _runs()
    prov = _prov(runs)
    j = hc.RunJournal(tmp_path / "c.journal", "J")
    n = {"calls": 0}

    def flaky(r, w, win):
        n["calls"] += 1
        if n["calls"] == 3:
            raise KeyboardInterrupt
        return _ok_run(r, w, win)
    with pytest.raises(KeyboardInterrupt):
        _execute(runs, prov, j, flaky)
    reran = []

    def do_run(r, w, win):
        reran.append(r["run_id"])
        return _ok_run(r, w, win)
    recs = _execute(runs, prov, j, do_run, done=j.reusable())
    assert reran == [r["run_id"] for r in runs[2:]]                               # solo las faltantes
    assert [r["run_id"] for r in recs] == [r["run_id"] for r in runs]            # todas, en el orden del plan, sin duplicados
    assert len({r["run_id"] for r in recs}) == len(runs)
    final = j.summary()["final_state_counts"]
    assert final["completed"] == len(runs) and final["interrupted"] == 0         # la última entrada de cada run_id manda


def test_a_truncated_last_line_is_ignored_and_never_counts_as_a_run(tmp_path):
    runs = _runs()
    j = hc.RunJournal(tmp_path / "c.journal", "J")
    _execute(runs[:2], _prov(runs), j)
    with j.path.open("a", encoding="utf-8") as fh:
        fh.write('{"state": "completed", "run_id": "X", "rec')                    # corte a mitad de escritura
    assert len(j.entries()) == 2 and set(j.reusable()) == {runs[0]["run_id"], runs[1]["run_id"]}
    json.loads(j.path.read_text(encoding="utf-8").splitlines()[0])


def test_an_invalid_window_is_journaled_as_invalid_and_kept_but_flagged(tmp_path):
    runs = _runs()
    j = hc.RunJournal(tmp_path / "c.journal", "J")
    short = lambda r, w, win: (_ok_run(r, w, win)[0][:50], [])                    # pocas respuestas: ventana < 60 s
    recs = _execute(runs[:1], _prov(runs), j, short)
    assert [e["state"] for e in j.entries()] == ["invalid"] and recs[0]["status"] != "ok"
    assert j.summary()["final_state_counts"]["invalid"] == 1 and j.reusable()                 # se conserva para la trazabilidad; el análisis ya filtra por `comparable`


def test_unknown_states_are_rejected(tmp_path):
    with pytest.raises(ValueError):
        hc.RunJournal(tmp_path, "J").append("done", "r")
