#!/usr/bin/env bash
# Run on the H200 host after the original glm53 container has exited.
# Preserve its compiled caches and failure evidence; do not stop the EC2 host.
set -euo pipefail
test "$(docker inspect -f '{{.State.Running}}' glm53)" = false
stamp=$(date -u +%Y%m%dT%H%M%SZ)
archive="/opt/h200/recovery-$stamp"
mkdir -p "$archive"
docker logs glm53 >"$archive/server.log" 2>&1
docker inspect glm53 >"$archive/container.json"
image="glm53-h200-cached:$stamp"
docker commit glm53 "$image" >"$archive/image-id.txt"
docker rename glm53 "glm53-failed-$stamp"
docker run -d --restart no --name glm53 --gpus all --ipc=host --network=host \
  --ulimit memlock=-1 --ulimit stack=67108864 \
  -v /model-cache:/root/.cache/huggingface \
  "$image" \
  python3 -m sglang.launch_server \
  --model-path zai-org/GLM-5.3 --served-model-name glm-5.3 \
  --revision ba32f8c19c8738e2c57c71798c601d477a7bf844 \
  --tp-size 8 --trust-remote-code \
  --speculative-algorithm EAGLE --speculative-num-steps 3 \
  --speculative-eagle-topk 1 --speculative-num-draft-tokens 4 \
  --kv-cache-dtype fp8_e4m3 \
  --tool-call-parser glm47 --reasoning-parser glm45 \
  --context-length 262144 --max-running-requests 2 \
  --mem-fraction-static 0.80 --chunked-prefill-size 8192 \
  --watchdog-timeout 1800 --host 0.0.0.0 --port 8000
printf 'Failure evidence: %s\n' "$archive"
