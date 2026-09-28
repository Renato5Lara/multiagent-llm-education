#!/usr/bin/env bash
set -u
REPO="/var/home/rlara/Documentos/2026-20/Tesis II/Aplicacion_Proyecto/multiagent-llm-education"; IMG=9e87977b867847e186d066f531ef783b006d582a985c341c269446088d90f2c4; ST="/home/rlara/k10_analysis_staging_2026-09-27"; P="/home/rlara/k10_analysis_prep_2026-09-27"; NOTE="/home/rlara/Documentos/2026-20/Tesis II/Docuemento de tesis/NOTA-PREANALISIS-K10-2026-09-27.md"
date -Is > "$ST/run_logs/host_start.txt"; date -u +%FT%TZ > "$ST/run_logs/host_start_utc.txt"
podman run --rm --pull=never --network=none --security-opt label=disable --userns=keep-id \
  -e PYTHONDONTWRITEBYTECODE=1 -e HOME=/tmp -e PYTHONPATH=/work/backend -e K10_IMAGE_ID=$IMG \
  -v "$REPO":/work:ro -v "$HOME/k10_prep":/prep:ro -v "$HOME/k10_prep/wheelhouse":/wh:ro -v "$P":/aprep:ro -v "$NOTE":/note/NOTA-PREANALISIS-K10-2026-09-27.md:ro -v "$ST":/out \
  -w /work/backend $IMG bash /aprep/container_analysis.sh
RC=$?
echo $RC > "$ST/run_logs/host_podman_exit_code.txt"; date -Is > "$ST/run_logs/host_end.txt"; date -u +%FT%TZ > "$ST/run_logs/host_end_utc.txt"
exit $RC
