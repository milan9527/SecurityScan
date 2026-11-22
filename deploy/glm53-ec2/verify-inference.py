#!/usr/bin/env python3
"""Verify the self-hosted model and tool-call round trip; retain raw evidence."""
import datetime
import json
import os
from pathlib import Path
import urllib.request

base = os.environ.get("LLM_API_BASE", "http://127.0.0.1:18000/v1").rstrip("/")
output = Path(os.environ.get("VERIFY_OUTPUT_DIR", str(
    Path(__file__).resolve().parents[2] / "reports/agentcoreshell-selfhosted")))
output.mkdir(parents=True, exist_ok=True)
evidence = {"time_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "endpoint": base, "deployment": "EC2 SGLang", "model": "glm-5.3"}


def request(path, body=None):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(base + path, data=data,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as response:
        return json.load(response)


try:
    evidence["models"] = request("/models")
    assert any(m["id"] == "glm-5.3" for m in evidence["models"]["data"])
    messages = [{"role": "user", "content":
                 "Call the add tool to add 19 and 23. After receiving the result, reply with the result only."}]
    tools = [{"type": "function", "function": {
        "name": "add", "description": "Add two integers.",
        "parameters": {"type": "object", "properties": {
            "a": {"type": "integer"}, "b": {"type": "integer"}},
            "required": ["a", "b"], "additionalProperties": False}}}]
    payload = {"model": "glm-5.3", "messages": messages, "tools": tools,
               "max_tokens": 2048, "temperature": 0,
               "chat_template_kwargs": {"reasoning_effort": "high"}}
    evidence["tool_response"] = request("/chat/completions", payload)
    message = evidence["tool_response"]["choices"][0]["message"]
    calls = message.get("tool_calls") or []
    assert len(calls) == 1, message
    assert calls[0]["function"]["name"] == "add", calls
    args = json.loads(calls[0]["function"]["arguments"])
    assert args == {"a": 19, "b": 23}, args
    messages.append(message)
    messages.append({"role": "tool", "tool_call_id": calls[0]["id"], "content": "42"})
    evidence["final_response"] = request("/chat/completions", payload)
    assert evidence["final_response"]["choices"][0]["message"]["content"].strip() == "42"
    evidence["passed"] = True
    print("PASS: glm-5.3 identity and tool-call round trip")
except Exception as exc:
    evidence["passed"] = False
    evidence["error"] = repr(exc)
    raise
finally:
    (output / "inference-verification.json").write_text(
        json.dumps(evidence, indent=2, ensure_ascii=False) + "\n")
