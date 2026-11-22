#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
git submodule update --init strix-src
for patch in strix_bedrock_params.patch strix_context_budget.patch; do
  if git -C strix-src apply --reverse --check "../$patch" 2>/dev/null; then
    echo "$patch already applied."
  else
    git -C strix-src apply --check "../$patch"
    git -C strix-src apply "../$patch"
  fi
done
cd strix-src
uv sync
