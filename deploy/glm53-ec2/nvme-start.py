#!/usr/bin/env python3
"""Stage the durable HF cache on DLAMI instance store before starting GLM."""
import datetime
from concurrent.futures import ThreadPoolExecutor
import http.client
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.request

SOURCE = Path("/model-cache")
MOUNT = Path("/opt/dlami/nvme")
CACHE = MOUNT / "glm53-hf"
STATE = Path("/var/lib/glm53-nvme")
NAME = "glm53-nvme"


def run(*args, **kwargs):
    return subprocess.run(args, check=True, **kwargs)


def event(phase, **fields):
    data = {"at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "phase": phase, **fields}
    with (STATE / "timings.jsonl").open("a") as f:
        f.write(json.dumps(data) + "\n")
    print(json.dumps(data), flush=True)


def docker_api(method, path, body=None):
    connection = http.client.HTTPConnection("localhost")
    connection.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    connection.sock.connect("/var/run/docker.sock")
    connection.request(method, path, json.dumps(body) if body else None,
                       {"Content-Type": "application/json"})
    response = connection.getresponse()
    payload = response.read()
    if response.status >= 300:
        raise RuntimeError(f"Docker API status {response.status}: {payload!r}")
    connection.close()
    return json.loads(payload) if payload else {}


def main():
    STATE.mkdir(mode=0o700, exist_ok=True)
    if len(sys.argv) == 3 and sys.argv[1] == "--capture":
        original = sys.argv[2]
        backup = STATE / "original.json"
        if backup.exists():
            raise RuntimeError("Original configuration already saved; refusing to overwrite")
        config = docker_api("GET", f"/containers/{original}/json")
        fd = os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as f:
            json.dump(config, f)
        event("original_saved", container=original)
        return

    started = time.monotonic()
    run("mountpoint", "-q", str(SOURCE))
    run("mountpoint", "-q", str(MOUNT))
    if SOURCE.stat().st_dev == MOUNT.stat().st_dev:
        raise RuntimeError("NVMe and durable source must be different filesystems")
    original = json.loads((STATE / "original.json").read_text())
    original_name = original["Name"].lstrip("/")
    # Disable Docker boot auto-start: systemd owns staging and startup order.
    run("docker", "update", "--restart=no", original_name)
    run("docker", "stop", "-t", "30", original_name)
    event("staging_started", source=str(SOURCE), destination=str(CACHE))
    CACHE.mkdir(exist_ok=True)
    staging_started = time.monotonic()
    source_hub = SOURCE / "hub"
    files = [p for p in source_hub.rglob("*") if p.is_file() and not p.is_symlink()]
    def copy_file(path):
        destination = CACHE / "hub" / path.relative_to(source_hub)
        destination.parent.mkdir(parents=True, exist_ok=True)
        run("rsync", "-a", "--partial", str(path), str(destination))
    # Each worker owns a separate file. The final pass preserves snapshot symlinks.
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(copy_file, files))
    # rsync preserves relative HF snapshot -> blob symlinks and retries partial copies.
    # Do not copy xet download caches or touch the authoritative EBS source.
    run("rsync", "-a", "--partial", "--stats", str(SOURCE / "hub"), str(CACHE) + "/")
    run("sync", "-f", str(CACHE))
    copied = time.monotonic()
    event("staging_complete", copy_seconds=round(copied - started, 3),
          staging_seconds=round(copied - staging_started, 3), copy_workers=8)
    existing = subprocess.run(["docker", "inspect", NAME], stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL)
    if existing.returncode:
        config = dict(original["Config"])
        host = dict(original["HostConfig"])
        host["Binds"] = [
            f"{CACHE}:/root/.cache/huggingface"
            if item.split(":")[1] == "/root/.cache/huggingface" else item
            for item in host["Binds"]
        ]
        host["RestartPolicy"] = {"Name": "no", "MaximumRetryCount": 0}
        config["HostConfig"] = host
        docker_api("POST", f"/containers/create?name={NAME}", config)
    run("docker", "start", NAME)
    event("model_start")
    deadline = time.monotonic() + 3600
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen("http://127.0.0.1:8000/v1/models", timeout=3) as r:
                models = json.load(r)
            if any(m["id"] == "glm-5.3" for m in models.get("data", [])):
                event("ready", load_seconds=round(time.monotonic() - copied, 3),
                      total_seconds=round(time.monotonic() - started, 3))
                run("docker", "wait", NAME)
                raise RuntimeError("Model container exited")
        except (OSError, ValueError):
            pass
        status = docker_api("GET", f"/containers/{NAME}/json")["State"]
        if not status["Running"]:
            raise RuntimeError(f"Model exited with code {status['ExitCode']}")
        time.sleep(10)
    run("docker", "stop", "-t", "30", NAME)
    raise TimeoutError("Model was not ready after 3600 seconds")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        event("failed", error=str(error))
        raise
