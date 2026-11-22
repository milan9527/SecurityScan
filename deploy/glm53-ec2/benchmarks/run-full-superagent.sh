#!/usr/bin/env bash
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
SCAN=$(cd "$HERE/../../.." && pwd)
TARGET="${STRIX_TARGET:-/home/ec2-user/bedrock/agentcore-superagent-update}"
OUT="${STRIX_REPORT_DIR:-$SCAN/reports/glm53-superagent/full-$(date -u +%Y%m%dT%H%M%SZ)}"
mkdir -p "$OUT"
exec 9>"$SCAN/reports/glm53-superagent/full-scan.lock"
flock -n 9 || { echo "A full scan is already running"; exit 1; }
export STRIX_LLM=openai/glm-5.3 STRIX_API_TYPE=chat_completions
export LLM_API_BASE="${LLM_API_BASE:-http://127.0.0.1:18000/v1}" LLM_API_KEY=EMPTY
export LLM_EXTRA_BODY='{"max_tokens":32768,"chat_template_kwargs":{"reasoning_effort":"low"}}'
export STRIX_CONTEXT_TOKENS=262144 STRIX_OUTPUT_TOKENS=32768
export STRIX_PROMPT_CACHE=false LLM_DISABLE_STREAMING=true
export LLM_PREFLIGHT_TIMEOUT=180 LLM_TIMEOUT=600 STRIX_TELEMETRY=false
export STRIX_RUN_RECORD_TIMINGS=true
export STRIX_LLM_INPUT_COST_PER_MTOK=0 STRIX_LLM_OUTPUT_COST_PER_MTOK=0
start=$(date +%s)
finish() {
  status=$?
  end=$(date +%s)
  printf '{"start_epoch":%s,"end_epoch":%s,"elapsed_s":%s,"exit_code":%s,"mode":"deep","ttft_measured":false}\n' \
    "$start" "$end" "$((end-start))" "$status" > "$OUT/status.json.tmp"
  mv "$OUT/status.json.tmp" "$OUT/status.json"
}
trap finish EXIT
printf '%s\n' "$$" > "$OUT/runner.pid"
curl --fail --silent --show-error --max-time 15 "$LLM_API_BASE/models" > "$OUT/models.json"
git -C "$TARGET" rev-parse HEAD > "$OUT/target-sha.txt"
git -C "$TARGET" status --short > "$OUT/target-worktree-status.txt"
git -C "$TARGET" diff --binary HEAD | sha256sum > "$OUT/target-tracked-diff.sha256"
cd "$SCAN/strix-src"
timeout --signal=TERM --kill-after=60s 10800s .venv/bin/strix \
  -n -t "$TARGET" --scan-mode deep --scope-mode full --max-turns 150 \
  --instruction-file "${STRIX_INSTRUCTION_FILE:-$HERE/superagent/full.txt}" > "$OUT/strix.log" 2>&1
