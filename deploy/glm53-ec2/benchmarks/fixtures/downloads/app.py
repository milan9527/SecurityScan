"""Download handlers: root is administrator configured; filename is user supplied.
The root and its ancestors cannot be modified by clients; no client symlink creation.
"""
from pathlib import Path

def download(root, filename):
    return (Path(root) / filename).read_bytes()

def download_v2(root, filename):
    base = Path(root).resolve()
    target = (base / filename).resolve()
    if not target.is_relative_to(base):
        raise PermissionError('outside download root')
    return target.read_bytes()
