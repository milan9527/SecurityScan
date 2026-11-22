#!/usr/bin/env bash
set -euo pipefail
DEPLOY_DIR="$(cd "$(dirname "$0")" && pwd)"
SCAN_DIR="$(cd "$DEPLOY_DIR/../.." && pwd)"
export STRIX_LLM=openai/glm-5.3
export STRIX_API_TYPE=chat_completions
export LLM_API_BASE="${LLM_API_BASE:-http://127.0.0.1:18000/v1}"
export LLM_API_KEY=EMPTY
export LLM_EXTRA_BODY='{"max_tokens":32768,"chat_template_kwargs":{"reasoning_effort":"high"}}'
export STRIX_PROMPT_CACHE=false
export LLM_DISABLE_STREAMING=true
export LLM_PREFLIGHT_TIMEOUT=180
export LLM_TIMEOUT=600
export STRIX_TELEMETRY=false
export STRIX_LLM_INPUT_COST_PER_MTOK=0
export STRIX_LLM_OUTPUT_COST_PER_MTOK=0
curl --fail --silent --max-time 10 "$LLM_API_BASE/models"
cd "$SCAN_DIR/strix-src"
exec timeout --signal=TERM --kill-after=30s 2400s .venv/bin/strix \
  -n -t /home/ec2-user/bedrock/AgentcoreShell --scan-mode quick --scope-mode full \
  --max-turns "${STRIX_MAX_TURNS:-60}" --instruction-file "$SCAN_DIR/strix-agentcoreshell-instructions.txt"
