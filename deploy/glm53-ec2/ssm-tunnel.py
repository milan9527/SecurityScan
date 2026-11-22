#!/usr/bin/env python3
"""Keep model traffic private through an SSM session; do not log session tokens."""
import argparse
import json
import signal
import subprocess
import sys

import boto3


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--instance", default="i-0b33a1d2ee1a2065f")
    parser.add_argument("--region", default="ap-south-1")
    parser.add_argument("--local-port", default="18000")
    args = parser.parse_args()
    client = boto3.client("ssm", region_name=args.region)
    request = {
        "Target": args.instance,
        "DocumentName": "AWS-StartPortForwardingSession",
        "Parameters": {"portNumber": ["8000"], "localPortNumber": [args.local_port]},
    }
    session = client.start_session(**request)
    process = None
    try:
        process = subprocess.Popen([
            "session-manager-plugin", json.dumps(session), args.region,
            "StartSession", "", json.dumps(request), client.meta.endpoint_url,
        ])

        def stop(signum, frame):
            raise KeyboardInterrupt

        signal.signal(signal.SIGTERM, stop)
        return process.wait()
    except KeyboardInterrupt:
        return 130
    finally:
        if process and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        try:
            client.terminate_session(SessionId=session["SessionId"])
        except client.exceptions.ValidationException:
            # The plugin may have already terminated its session on SIGTERM.
            pass
        finally:
            client.close()


if __name__ == "__main__":
    sys.exit(main())
