#!/usr/bin/env python3
"""Build reproducible, line-numbered real repository audit workloads."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

p = argparse.ArgumentParser()
p.add_argument('--repo', type=Path, required=True)
p.add_argument('--out', type=Path, required=True)
a = p.parse_args()
groups = {
    'auth': ['backend/src/middleware/auth.ts', 'backend/src/authorization/auth.middleware.ts', 'backend/src/authorization/authorization.ts', 'backend/src/authorization/permissions.ts', 'backend/src/routes/auth.routes.ts'],
    'paths': ['backend/src/routes/files.routes.ts', 'backend/src/services/workspace-manager.ts', 'backend/src/services/workflow-workspace.ts', 'agentcore/src/workspace-sync.ts'],
    'webhook': ['backend/src/routes/webhooks.routes.ts', 'backend/src/services/webhook.service.ts', 'backend/src/services/oauth-flow.service.ts'],
    'tools': ['backend/src/routes/execution.routes.ts', 'backend/src/routes/mcp.routes.ts', 'agentcore/src/agent-runner.ts', 'agentcore/src/index.ts'],
}
cases, manifest = {}, {}
for name, paths in groups.items():
    chunks, files = [], []
    for relative in paths:
        relative = 'super-agent/' + relative
        raw = (a.repo / relative).read_bytes()
        text = raw.decode('utf-8')
        chunks.append('\nFILE: ' + relative + '\n' + '\n'.join(f'{i}: {line}' for i, line in enumerate(text.splitlines(), 1)))
        files.append({'path': relative, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()})
    cases[name] = '\n'.join(chunks)
    manifest[name] = {'files': files, 'prompt_chars': len(cases[name])}
a.out.parent.mkdir(parents=True, exist_ok=True)
a.out.write_text(json.dumps(cases))
a.out.with_suffix('.manifest.json').write_text(json.dumps({'commit': subprocess.check_output(['git', '-C', str(a.repo), 'rev-parse', 'HEAD'], text=True).strip(), 'cases': manifest}, indent=2))
print(json.dumps({k: v['prompt_chars'] for k, v in manifest.items()}))
