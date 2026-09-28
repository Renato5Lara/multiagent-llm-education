set -u
D=2026-09-27; RUN=k10_official_$D; OUT=/out/$RUN
date -u +%FT%TZ > /ev/container_start_utc.txt
python --version > /ev/python_version.txt 2>&1
(cd /prep && sha256sum -c SHA256SUMS) > /ev/prep_sha256sums_check.txt 2>&1 || { echo "FALLO checksums de ~/k10_prep" >&2; exit 90; }
python -m venv /tmp/venv || exit 91
/tmp/venv/bin/pip install -q --no-cache-dir --disable-pip-version-check --no-index --find-links /wh --require-hashes -r /prep/requirements-k10.lock > /ev/pip_install.log 2>&1 || exit 92
/tmp/venv/bin/pip freeze > /ev/pip_freeze.txt
/tmp/venv/bin/python /prep/k10_preflight.py "$OUT" > /ev/preflight.log 2>&1; PF=$?
echo $PF > /ev/preflight_exit_code.txt
if [ $PF -ne 0 ]; then echo "PRE-FLIGHT FALLÓ (exit $PF): K=10 NO se ejecuta" >&2; exit 93; fi
date -u +%FT%TZ > /ev/run_start_utc.txt
/tmp/venv/bin/python -m adaptation_swarm.analysis.replicas run \
  --master-seed 26092601 \
  --k 10 \
  --library-version lib-v10-5dd83cd4 \
  --gold-rule gold-v2-cand-A \
  --inclusion-rule incl-ge1 \
  --out-dir "$OUT" > /ev/run_stdout.log 2> /ev/run_stderr.log
RC=$?
date -u +%FT%TZ > /ev/run_end_utc.txt
echo $RC > /ev/run_exit_code.txt
exit $RC
