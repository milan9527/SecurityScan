"""Harmless local replay; no cloud calls or real git operations."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import types

sys.dont_write_bytecode = True
source = Path(sys.argv[1] if len(sys.argv) > 1 else '/home/ec2-user/bedrock/AgentcoreShell')
stub = types.ModuleType('shell_client')
stub.AgentCoreShell = object
sys.modules['shell_client'] = stub
spec = importlib.util.spec_from_file_location('workflow_under_test', source / 'coding_workflow.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class FakeShell:
    def __init__(self):
        self.commands = []
    def invoke_agent(self, prompt):
        return 'Mocked: no agent invoked'
    def run(self, command, **kwargs):
        self.commands.append(command)
        return types.SimpleNamespace(success=True, stdout='', stderr='')

with tempfile.TemporaryDirectory(prefix='agentcoreshell-test-') as directory:
    root = Path(directory)
    tools = root / 'bin'
    tools.mkdir()
    fake_git = tools / 'git'
    fake_git.write_text('#!/bin/sh\nexit 0\n')
    fake_git.chmod(0o755)
    results = []
    for case, task in [('control', 'JIRA-1234'), ('injection', 'JIRA-1234; printf verified > injection_marker #')]:
        shell = FakeShell()
        with contextlib.redirect_stdout(io.StringIO()):
            module.coding_workflow(shell, task)
        command = next(c for c in shell.commands if 'git checkout -b' in c)
        # Parse the outer command into argv, preserving the inner bash script.
        # Replace only the workspace directory; use fake git via PATH.
        argv = shlex.split(command.replace('/workspace', directory))
        completed = subprocess.run(argv, env={**os.environ, 'PATH': str(tools) + ':/usr/bin:/bin'}, capture_output=True, text=True, timeout=5)
        marker = root / 'injection_marker'
        results.append({'case': case, 'exit_code': completed.returncode, 'marker_created': marker.exists(), 'marker_content': marker.read_text() if marker.exists() else None})
        if marker.exists():
            marker.unlink()
    assert results[0]['marker_created'] is False
    assert results[1]['marker_content'] == 'verified'
    print(json.dumps({'test': 'untrusted task interpolation into bash command', 'cloud_calls': 0, 'real_git_calls': 0, 'results': results}, indent=2))
