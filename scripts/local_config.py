# -*- coding: utf-8 -*-
"""Repo-local config and read-only migration from the two old config inputs."""
import json
import os
import re
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

SCHEMA_VERSION = 1


def derived_paths(repo):
    repo = Path(repo).resolve()
    return {"workspace": repo, "venv": repo / ".venv",
            "mcp_home": repo / "mcp_home", "work": repo / "work"}


def read_config(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or set(data) != {"schema_version", "ABAQUS_CMD"}:
        raise ValueError("Config requires only schema_version and ABAQUS_CMD")
    if type(data["schema_version"]) is not int or data["schema_version"] != SCHEMA_VERSION:
        raise ValueError("Unsupported config schema_version")
    if not isinstance(data["ABAQUS_CMD"], str) or not data["ABAQUS_CMD"].strip():
        raise ValueError("ABAQUS_CMD is required")
    return data


def write_config(path, abaqus_cmd):
    import runtime_detection
    command = runtime_detection.validate_abaqus_cmd(abaqus_cmd)
    path = Path(path)
    if path.exists():
        existing = read_config(path)
        if existing["ABAQUS_CMD"] != command:
            raise ValueError("Existing config differs; choose explicitly before changing it")
        return str(path)
    payload = {"schema_version": SCHEMA_VERSION, "ABAQUS_CMD": command}
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if path.exists():
            raise ValueError("Config appeared during write; did not replace it")
        # On supported Windows filesystems rename refuses an existing target.
        temporary.rename(path)
    finally:
        temporary.unlink(missing_ok=True)
    return str(path)


def _legacy_json(path, repo):
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Legacy JSON must be an object")
    workspace = data.get("workspace")
    if workspace and Path(workspace).resolve() != Path(repo).resolve():
        return None  # global file belongs to another extracted repo
    return data.get("abaqus_cmd") or data.get("ABAQUS_CMD")


def _legacy_bat(path):
    assignment = None
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.lower().startswith(("@rem ", "rem ", "::")):
            continue
        match = re.fullmatch(r'set\s+"ABAQUS_CMD=([^"\r\n]*)"', line, flags=re.I)
        if not match or assignment is not None:
            raise ValueError("Legacy BAT has non-literal or multiple commands; it was not executed")
        assignment = match.group(1)
    return assignment


def load_or_migrate(repo, config_path=None, local_env=None, write=False, legacy_home=None):
    """Return (config or None, source); preserve all old files byte-for-byte."""
    repo = Path(repo).resolve()
    config_path = Path(config_path or repo / ".abaqus-agent.json")
    local_env = Path(local_env or repo / ".abaqus-agent.local")
    legacy_home = Path(legacy_home or Path(os.environ.get("USERPROFILE", str(Path.home()))) /
                       ".abaqus-agent.local.json")
    if config_path.exists():
        return read_config(config_path), "current"

    candidates = []
    if legacy_home.is_file():
        value = _legacy_json(legacy_home, repo)
        if value:
            candidates.append((value, str(legacy_home)))
    if local_env.is_file():
        value = _legacy_bat(local_env)
        if value:
            candidates.append((value, str(local_env)))
    if not candidates:
        return None, "none"
    import runtime_detection
    validated = [(runtime_detection.validate_abaqus_cmd(value), source)
                 for value, source in candidates]
    if len({value for value, _ in validated}) != 1:
        raise ValueError("Legacy Abaqus configs disagree; choose one explicitly")
    command = validated[0][0]
    if write:
        write_config(config_path, command)
    return {"schema_version": SCHEMA_VERSION, "ABAQUS_CMD": command}, "+".join(source for _, source in validated)
