#!/usr/bin/env bash
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
SCAN=$(cd "$HERE/../../.." && pwd)
OUT="${STRIX_REPORT_DIR:?Set STRIX_REPORT_DIR to an absolute report directory}"
mkdir -p "$OUT"
export LLM_API_BASE="${LLM_API_BASE:-http://127.0.0.1:18000/v1}"
finish() {
  code=$?
  printf '{"exit_code":%s,"finished_utc":"%s"}\n' "$code" "$(date -u +%FT%TZ)" > "$OUT/suite-status.json"
}
trap finish EXIT
printf '%s\n' "$$" > "$OUT/suite.pid"
deadline=$((SECONDS+2400))
until curl --fail --silent --max-time 5 "$LLM_API_BASE/models" > "$OUT/readiness.json"; do
  if (( SECONDS >= deadline )); then echo "Model readiness timed out"; exit 1; fi
  sleep 20
done
VERIFY_OUTPUT_DIR="$OUT" python3 "$HERE/../verify-inference.py"
python3 "$HERE/stream-benchmark.py" --base "$LLM_API_BASE" \
  --out "$OUT/stream-metrics.jsonl" --cases-json "$SCAN/reports/glm53-superagent/source-cases.json" \
  --repeats 3 --max-tokens 8192 --variant mtp --warm-all
bash "$HERE/run-full-superagent.sh"
