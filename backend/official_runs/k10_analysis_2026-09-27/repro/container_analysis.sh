set -u
OUT=/out/k10_analysis_2026-09-27; L=/out/run_logs
date -u +%FT%TZ > $L/container_start_utc.txt; python --version > $L/python_version.txt 2>&1
python -m venv /tmp/venv || exit 91
/tmp/venv/bin/pip install -q --no-cache-dir --disable-pip-version-check --no-index --find-links /wh --require-hashes -r /prep/requirements-k10.lock > $L/pip_install.log 2>&1 || exit 92
/tmp/venv/bin/pip freeze > $L/pip_freeze.txt
/tmp/venv/bin/python /aprep/analysis_preflight.py "$OUT" > $L/preflight.log 2>&1; PF=$?; echo $PF > $L/preflight_exit_code.txt
if [ $PF -ne 0 ]; then echo "PRE-FLIGHT FALLÓ (exit $PF): NO se calcula ningún estadístico" >&2; exit 93; fi
date -u +%FT%TZ > $L/analysis_start_utc.txt
/tmp/venv/bin/python /aprep/analysis_driver.py "$OUT" > $L/analysis_stdout.log 2> $L/analysis_stderr.log; RC=$?
date -u +%FT%TZ > $L/analysis_end_utc.txt; echo $RC > $L/analysis_exit_code.txt; exit $RC
