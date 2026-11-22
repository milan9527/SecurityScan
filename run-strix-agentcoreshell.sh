#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/strix-src"
export STRIX_LLM=bedrock/converse/us.zai.glm-5.3
export AWS_REGION=us-east-1 AWS_DEFAULT_REGION=us-east-1
export LLM_EXTRA_BODY='{"service_tier":"flex","max_tokens":32768}'
export STRIX_PROMPT_CACHE=false
export LLM_DISABLE_STREAMING=true
export LLM_PREFLIGHT_TIMEOUT=180
export LLM_TIMEOUT=240
export STRIX_TELEMETRY=false
exec timeout --signal=TERM --kill-after=30s 1200s .venv/bin/strix \
  -n -t /home/ec2-user/bedrock/AgentcoreShell --scan-mode quick --scope-mode full \
  --max-budget 3 --max-turns 18 --instruction-file ../strix-agentcoreshell-instructions.txt
