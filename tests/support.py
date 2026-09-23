import importlib.util
import os
import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]


def load(name, path, home=None, modules=None):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    overrides = {"ABAQUS_MCP_HOME": str(home)} if home else {}
    with mock.patch.dict(os.environ, overrides), mock.patch.dict("sys.modules", modules or {}):
        spec.loader.exec_module(module)
    return module


@contextmanager
def temp_home():
    with tempfile.TemporaryDirectory(prefix="abaqus-d6-") as tmp:
        yield Path(tmp)


def archive_files():
    import io
    import tarfile
    with tarfile.open(fileobj=io.BytesIO(_archive_bytes())) as archive:
        return {m.name for m in archive.getmembers() if m.isfile()}


def _archive_bytes():
    return subprocess.run(["git", "archive", "--format=tar", "HEAD"], cwd=ROOT,
                          capture_output=True, check=True).stdout


def archive_to(destination):
    import io
    import tarfile
    with tarfile.open(fileobj=io.BytesIO(_archive_bytes())) as archive:
        for member in archive.getmembers():
            if member.isfile():
                target = destination / member.name
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.extractfile(member) as src, target.open("wb") as dst:
                    dst.write(src.read())
