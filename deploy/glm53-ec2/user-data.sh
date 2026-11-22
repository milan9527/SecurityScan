#!/bin/bash
set -Eeuo pipefail
exec > >(tee -a /var/log/glm53-bootstrap.log) 2>&1
trap 'echo "Bootstrap failed at line $LINENO"; shutdown -h +10' ERR
# Shutdown stops this persistent Spot instance; EBS is retained.
shutdown -h +240
export DEBIAN_FRONTEND=noninteractive
# Deep Learning AMIs already ship Docker CE and containerd.io. Installing
# Ubuntu's docker.io alongside them creates a containerd package conflict.
if ! command -v docker >/dev/null; then
  apt-get update
  apt-get install -y docker.io
fi
command -v nvidia-ctk
systemctl enable --now docker
nvidia-ctk runtime configure --runtime=docker
systemctl restart docker
nvidia-smi
# A fresh, encrypted EBS data volume avoids formatting any AMI-managed NVMe disks.
for attempt in $(seq 1 60); do
  DATA_DISK=$(find /dev/disk/by-id -name 'nvme-Amazon_Elastic_Block_Store_*' \
    ! -name '*-part*' -exec sh -c 'for d; do if [ "$(blockdev --getsize64 "$d")" = 2199023255552 ]; then readlink -f "$d"; fi; done' sh {} + | sort -u)
  [ -n "$DATA_DISK" ] && break
  sleep 5
done
test -n "$DATA_DISK"
test "$(printf '%s\n' "$DATA_DISK" | wc -l)" -eq 1
if ! blkid "$DATA_DISK"; then mkfs.ext4 -F "$DATA_DISK"; fi
mkdir -p /model-cache
DISK_UUID=$(blkid -s UUID -o value "$DATA_DISK")
printf "UUID=%s /model-cache ext4 defaults,nofail 0 2\n" "$DISK_UUID" >> /etc/fstab
mount /model-cache
mkdir -p /etc/systemd/system/docker.service.d
printf '[Unit]\nRequiresMountsFor=/model-cache\n' > /etc/systemd/system/docker.service.d/model-cache.conf
systemctl daemon-reload
SGLANG_IMAGE=lmsysorg/sglang@sha256:f832b5c39559c9caa900b22ad37c76fcce66470676855c42052102c537812f1f
docker pull "$SGLANG_IMAGE"
docker image inspect "$SGLANG_IMAGE" --format '{{json .RepoDigests}}' > /var/log/glm53-image-digest.json
docker run -d --restart unless-stopped --name glm53 --gpus all --ipc=host --network=host \
  --ulimit memlock=-1 --ulimit stack=67108864 \
  -v /model-cache:/root/.cache/huggingface \
  "$SGLANG_IMAGE" \
  python3 -m sglang.launch_server \
  --model-path zai-org/GLM-5.3 --served-model-name glm-5.3 \
  --revision ba32f8c19c8738e2c57c71798c601d477a7bf844 \
  --tp-size 8 --trust-remote-code \
  --kv-cache-dtype fp8_e4m3 \
  --tool-call-parser glm47 --reasoning-parser glm45 \
  --context-length 262144 --max-running-requests 2 \
  --mem-fraction-static 0.85 --chunked-prefill-size 32768 \
  --watchdog-timeout 1800 --host 0.0.0.0 --port 8000
