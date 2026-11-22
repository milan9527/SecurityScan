#!/usr/bin/env bash
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
SCAN=$(cd "$HERE/../../.." && pwd)
TARGET="${STRIX_TARGET:-/home/ec2-user/bedrock/agentcore-superagent-update}"
OUT="$SCAN/reports/glm53-superagent/$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$OUT"
export STRIX_LLM=openai/glm-5.3 STRIX_API_TYPE=chat_completions
export LLM_API_BASE="${LLM_API_BASE:-http://127.0.0.1:18000/v1}" LLM_API_KEY=EMPTY
export LLM_EXTRA_BODY='{"max_tokens":32768,"chat_template_kwargs":{"reasoning_effort":"low"}}'
export STRIX_CONTEXT_TOKENS=262144 STRIX_OUTPUT_TOKENS=32768
export STRIX_PROMPT_CACHE=false LLM_DISABLE_STREAMING=true
export LLM_PREFLIGHT_TIMEOUT=180 LLM_TIMEOUT=600 STRIX_TELEMETRY=false
export STRIX_RUN_RECORD_TIMINGS=true
export STRIX_LLM_INPUT_COST_PER_MTOK=0 STRIX_LLM_OUTPUT_COST_PER_MTOK=0
curl --fail --silent --max-time 10 "$LLM_API_BASE/models" > "$OUT/models.json"
git -C "$TARGET" rev-parse HEAD > "$OUT/target-sha.txt"
cd "$SCAN/strix-src"
for scenario in auth paths webhook tools; do
  start=$(date +%s)
  set +e
  timeout --signal=TERM --kill-after=30s 2400s .venv/bin/strix \
    -n -t "$TARGET" --scan-mode quick --scope-mode full --max-turns 45 \
    --instruction-file "$HERE/superagent/$scenario.txt" \
    > "$OUT/strix-$scenario.log" 2>&1
  status=$?
  set -e
  end=$(date +%s)
  printf '{"scenario":"%s","start_epoch":%s,"end_epoch":%s,"elapsed_s":%s,"exit_code":%s}\n' \
    "$scenario" "$start" "$end" "$((end-start))" "$status" >> "$OUT/timing.jsonl"
  # Fatal errors need diagnosis before spending time on further scenarios.
  if [[ "$status" != 0 && "$status" != 2 ]]; then exit "$status"; fi
done
