"""Temporary workaround for CUDA H2D copy lockup during GLM loading.

Run inside the glm53 container before restarting it. The original loader is
saved once. Recreating the container requires applying this workaround again.
"""
from pathlib import Path

path = Path(
    "/sgl-workspace/sglang/python/sglang/srt/models/"
    "deepseek_common/deepseek_weight_loader.py"
)
original = "use_async_loading = should_async_load(loaded_weight)"
replacement = (
    "use_async_loading = False  # Workaround: CUDA H2D threadpool lock hang"
)
source = path.read_text()
if replacement in source:
    print("Synchronous weight loading already enabled")
else:
    assert source.count(original) == 1, "Unexpected loader version; inspect before patching"
    backup = path.with_suffix(".py.before-sync-load")
    if not backup.exists():
        backup.write_text(source)
    path.write_text(source.replace(original, replacement))
    print("Enabled synchronous weight loading; original saved:", backup)
