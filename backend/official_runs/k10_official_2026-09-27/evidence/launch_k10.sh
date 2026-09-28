#!/usr/bin/env bash
set -u
REPO="/var/home/rlara/Documentos/2026-20/Tesis II/Aplicacion_Proyecto/multiagent-llm-education"; IMG=9e87977b867847e186d066f531ef783b006d582a985c341c269446088d90f2c4; STAGING="/home/rlara/k10_staging_2026-09-27"; EV="/home/rlara/k10_evidence_2026-09-27"
date -Is > "$EV/host_start.txt"; date -u +%FT%TZ > "$EV/host_start_utc.txt"
podman run --rm --pull=never --network=none --security-opt label=disable --userns=keep-id \
  -e PYTHONDONTWRITEBYTECODE=1 -e HOME=/tmp -e PYTHONPATH=/work/backend \
  -v "$REPO":/work:ro -v "$HOME/k10_prep":/prep:ro -v "$HOME/k10_prep/wheelhouse":/wh:ro -v "$STAGING":/out -v "$EV":/ev \
  -w /work/backend $IMG bash /ev/container_run.sh
RC=$?
echo $RC > "$EV/host_podman_exit_code.txt"; date -Is > "$EV/host_end.txt"; date -u +%FT%TZ > "$EV/host_end_utc.txt"
exit $RC
