#!/usr/bin/env bash
set -euo pipefail
# Run as root on the GPU host, with these three files in the same directory.
# Default: configure the next boot without interrupting active scans.
# Use --now only when scans are idle and immediate migration is intended.
cd "$(dirname "$0")"
original="${1:-glm53-mtp-ablation}"
activation="${2:---next-boot}"
[[ "$activation" == "--next-boot" || "$activation" == "--now" ]] || {
  echo "Usage: $0 [original-container] [--next-boot|--now]" >&2
  exit 2
}
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
systemctl enable glm53-nvme.service
# Updating restart policy does not stop the running container. Avoid its EBS
# auto-start racing NVMe staging on the next boot.
docker update --restart=no "$original"
if [[ "$activation" == "--now" ]]; then
  systemctl start glm53-nvme.service
fi
