#!/usr/bin/env bash
set -euo pipefail
# Run as root on the GPU host, with these three files in the same directory.
# Stop active scans and hold a bounded console experiment lease before invoking.
cd "$(dirname "$0")"
original="${1:-glm53-mtp-ablation}"
mountpoint -q /model-cache
mountpoint -q /opt/dlami/nvme
install -d -m 700 /var/lib/glm53-nvme
install -m 755 nvme-start.py /usr/local/sbin/glm53-nvme-start
install -m 644 glm53-nvme.service /etc/systemd/system/glm53-nvme.service
python3 -m py_compile /usr/local/sbin/glm53-nvme-start
if [[ ! -f /var/lib/glm53-nvme/original.json ]]; then
  /usr/local/sbin/glm53-nvme-start --capture "$original"
fi
systemctl daemon-reload
systemctl enable --now glm53-nvme.service
