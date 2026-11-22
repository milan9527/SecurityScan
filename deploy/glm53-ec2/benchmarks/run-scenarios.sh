#!/usr/bin/env bash
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
SCAN=$(cd "$HERE/../../.." && pwd)
export STRIX_LLM=openai/glm-5.3 STRIX_API_TYPE=chat_completions
export LLM_API_BASE="${LLM_API_BASE:-http://127.0.0.1:18000/v1}" LLM_API_KEY=EMPTY
export LLM_EXTRA_BODY='{"max_tokens":32768,"chat_template_kwargs":{"reasoning_effort":"low"}}'
export STRIX_CONTEXT_TOKENS=262144 STRIX_OUTPUT_TOKENS=32768
export STRIX_PROMPT_CACHE=false LLM_DISABLE_STREAMING=true LLM_PREFLIGHT_TIMEOUT=180 LLM_TIMEOUT=600 STRIX_TELEMETRY=false
export STRIX_RUN_RECORD_TIMINGS=true
export STRIX_LLM_INPUT_COST_PER_MTOK=0 STRIX_LLM_OUTPUT_COST_PER_MTOK=0
OUT="$SCAN/reports/glm53-multiscenario/$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$OUT"
cd "$SCAN/strix-src"
for scenario in catalog documents downloads; do
  start=$(date +%s)
  set +e
  timeout --signal=TERM --kill-after=30s 1800s .venv/bin/strix -n -t "$HERE/fixtures/$scenario" --scan-mode quick --scope-mode full --max-turns 30 --instruction-file "$HERE/instructions.txt" > "$OUT/strix-$scenario.log" 2>&1
  status=$?
  set -e
  end=$(date +%s)
  printf '{"scenario":"%s","start_epoch":%s,"end_epoch":%s,"elapsed_s":%s,"exit_code":%s}\n' "$scenario" "$start" "$end" "$((end-start))" "$status" >> "$OUT/strix-timing.jsonl"
done
