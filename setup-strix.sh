#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
git submodule update --init strix-src
if git -C strix-src apply --reverse --check ../strix_bedrock_params.patch 2>/dev/null; then
  echo 'Bedrock patch already applied.'
else
  git -C strix-src apply --check ../strix_bedrock_params.patch
  git -C strix-src apply ../strix_bedrock_params.patch
fi
cd strix-src
uv sync
