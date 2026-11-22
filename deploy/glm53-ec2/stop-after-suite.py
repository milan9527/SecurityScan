#!/usr/bin/env python3
"""Durable service cleanup: stop (never terminate) the retained test GPU."""
import datetime
import json
import os
from pathlib import Path

import boto3


def main():
    instance = "i-0b33a1d2ee1a2065f"
    out = Path(os.environ["STRIX_REPORT_DIR"])
    client = boto3.client("ec2", region_name="ap-south-1")
    try:
        response = client.stop_instances(InstanceIds=[instance])
        (out / "gpu-stop-request.json").write_text(json.dumps({
            "requested_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "instances": response["StoppingInstances"],
        }, indent=2))
        client.get_waiter("instance_stopped").wait(
            InstanceIds=[instance], WaiterConfig={"Delay": 15, "MaxAttempts": 80})
        status_path = Path(__file__).resolve().parents[2] / "reports/glm53-superagent/resource-status.json"
        status = json.loads(status_path.read_text())
        status.update(
            observed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            state="stopped", source="EC2 instance_stopped waiter",
            stop_reason="Full test suite exited; retained GPU stopped automatically.")
        temp = status_path.with_suffix(".tmp")
        temp.write_text(json.dumps(status, indent=2) + "\n")
        temp.replace(status_path)
        (out / "gpu-stopped.json").write_text(json.dumps(status, indent=2))
    finally:
        client.close()


if __name__ == "__main__":
    main()
