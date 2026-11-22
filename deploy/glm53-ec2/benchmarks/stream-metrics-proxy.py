#!/usr/bin/env python3
"""Private benchmark proxy: measure SSE output arrival, never persist payloads."""
import argparse
import http.client
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--port", type=int, default=18001)
parser.add_argument("--upstream-port", type=int, default=18000)
parser.add_argument("--out", type=Path, required=True)
args = parser.parse_args()
args.out.parent.mkdir(parents=True, exist_ok=True)
lock = threading.Lock()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        self.forward()

    def do_POST(self):
        self.forward()

    def forward(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
        if self.command == "POST" and self.path.endswith("/chat/completions"):
            payload = json.loads(body)
            if payload.get("stream"):
                payload.setdefault("stream_options", {})["include_usage"] = True
                body = json.dumps(payload).encode()
        started = time.monotonic()
        record = {"start_epoch": time.time(), "path": self.path,
                  "ttft_ms": None, "visible_ttft_ms": None, "usage": None}
        conn = http.client.HTTPConnection("127.0.0.1", args.upstream_port, timeout=600)
        try:
            headers = {k: v for k, v in self.headers.items()
                       if k.lower() not in {"host", "connection", "content-length"}}
            conn.request(self.command, self.path, body=body, headers=headers)
            response = conn.getresponse()
            record["status"] = response.status
            self.send_response(response.status)
            for key, value in response.getheaders():
                if key.lower() not in {"transfer-encoding", "connection", "content-length"}:
                    self.send_header(key, value)
            self.send_header("Connection", "close")
            self.end_headers()
            self.close_connection = True
            streaming = "text/event-stream" in response.getheader("Content-Type", "")
            record["streaming"] = streaming
            record["stream_done"] = False
            while True:
                chunk = response.readline() if streaming else response.read(65536)
                if not chunk:
                    break
                elapsed = (time.monotonic() - started) * 1000
                if streaming and chunk.startswith(b"data:"):
                    data = chunk[5:].strip()
                    if data == b"[DONE]":
                        record["stream_done"] = True
                    if data and data != b"[DONE]":
                        event = json.loads(data)
                        if event.get("usage"):
                            record["usage"] = event["usage"]
                        for choice in event.get("choices", []):
                            delta = choice.get("delta") or {}
                            visible = bool(delta.get("content"))
                            output = visible or bool(delta.get("reasoning_content") or
                                                     delta.get("reasoning") or
                                                     delta.get("tool_calls"))
                            if output and record["ttft_ms"] is None:
                                record["ttft_ms"] = elapsed
                            if visible and record["visible_ttft_ms"] is None:
                                record["visible_ttft_ms"] = elapsed
                self.wfile.write(chunk)
                self.wfile.flush()
            record["completed"] = not streaming or record["stream_done"]
        except Exception as exc:
            record["completed"] = False
            record["error_type"] = type(exc).__name__
        finally:
            record["e2e_ms"] = (time.monotonic() - started) * 1000
            record["end_epoch"] = time.time()
            conn.close()
            if self.command == "POST":
                with lock, args.out.open("a") as f:
                    f.write(json.dumps(record) + "\n")


ThreadingHTTPServer(("127.0.0.1", args.port), Handler).serve_forever()
