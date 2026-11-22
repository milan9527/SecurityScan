#!/usr/bin/env bash
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
SCAN=$(cd "$HERE/../../.." && pwd)
OUT=${STRIX_REPORT_DIR:?Set STRIX_REPORT_DIR}
TARGET=${STRIX_TARGET:?Set STRIX_TARGET}
mkdir -p "$OUT"
exec 8>"$SCAN/reports/glm53-superagent/h200-scan.lock"
flock -n 8 || exit 1
python3 "$HERE/../ssm-tunnel.py" --instance i-09c41bc239b10b001 --region ap-northeast-1 --local-port 18000 >"$OUT/tunnel.log" 2>&1 &
tunnel=$!
python3 "$HERE/stream-metrics-proxy.py" --out "$OUT/wire-metrics.jsonl" >"$OUT/proxy.log" 2>&1 &
proxy=$!
cleanup() { kill "$proxy" "$tunnel" 2>/dev/null || true; }
trap cleanup EXIT
touch "$OUT/wire-metrics.jsonl"
printf 'waiting_for_model\n' >"$OUT/phase.txt"
ready=false
for ((i=0; i<240; i++)); do
  kill -0 "$tunnel" "$proxy" || { printf 'transport_failed\n' >"$OUT/phase.txt"; exit 1; }
  if curl -fsS --max-time 5 http://127.0.0.1:18001/health > /dev/null 2>&1; then
    ready=true
    break
  fi
  sleep 15
done
if [[ "$ready" != true ]]; then
  printf 'model_ready_timeout\n' >"$OUT/phase.txt"
  exit 1
fi
printf 'scanning\n' >"$OUT/phase.txt"
set +e
STRIX_TARGET="$TARGET" STRIX_REPORT_DIR="$OUT" LLM_DISABLE_STREAMING=false \
LLM_API_BASE=http://127.0.0.1:18001/v1 bash "$HERE/run-full-superagent.sh"
scan_exit=$?
set -e
python3 "$HERE/collect-h200-scan.py" --out "$OUT" --runs "$SCAN/strix-src/strix_runs" --target "$TARGET"
printf 'finished_exit_%s\n' "$scan_exit" >"$OUT/phase.txt"
exit "$scan_exit"
