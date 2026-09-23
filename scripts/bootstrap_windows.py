# -*- coding: utf-8 -*-
"""Install the repo-local Windows environment from a source-only ZIP."""
import argparse
import json
import subprocess
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import local_config
import runtime_detection

REPO = Path(__file__).resolve().parent.parent
CONFIG_PATH = REPO / ".abaqus-agent.json"
LOCAL_ENV = REPO / ".abaqus-agent.local"  # legacy text input; never execute
MCP_VERSION = "1.30.0"

REQUIRED_FILES = (
    "SKILL.md", "client.py", "mcp_server.py", "abaqus_mcp_plugin.py",
    "abaqus_start_mcp.py", "install.bat", "doctor.bat", "start_abaqus_agent.bat",
    "scripts/bootstrap_windows.py", "scripts/doctor.py", "scripts/bridge_state.py",
    "scripts/local_config.py", "scripts/runtime_detection.py",
    "scripts/start_windows.py",
)
REQUIRED_DIRS = ("references",)


def verify_repo_files():
    missing = [name for name in REQUIRED_FILES if not (REPO / name).is_file()]
    missing += [name + "/" for name in REQUIRED_DIRS if not (REPO / name).is_dir()]
    return missing


def _venv_python(directory):
    return directory / "Scripts" / "python.exe"


def venv_is_ready(directory):
    python = _venv_python(directory)
    if not python.is_file():
        return False
    code = (
        "import json,sys,importlib.metadata as md; "
        "from mcp.server.fastmcp import FastMCP; "
        "print(json.dumps({'version':list(sys.version_info[:2]),"
        "'prefix':sys.prefix,'base_prefix':sys.base_prefix,"
        "'mcp':md.version('mcp')}))"
    )
    try:
        result = subprocess.run([str(python), "-c", code], capture_output=True,
                                text=True, timeout=20)
        if result.returncode != 0:
            return False
        data = json.loads(result.stdout.strip().splitlines()[-1])
        return (data["version"] == [3, 11] and data["mcp"] == MCP_VERSION
                and Path(data["prefix"]).resolve() == directory.resolve()
                and data["prefix"] != data["base_prefix"])
    except (OSError, ValueError, KeyError, IndexError, subprocess.TimeoutExpired):
        return False


def already_ready():
    try:
        config = local_config.read_config(CONFIG_PATH)
        runtime_detection.validate_abaqus_cmd(config["ABAQUS_CMD"])
    except (OSError, ValueError, KeyError):
        return False
    return (not verify_repo_files() and venv_is_ready(REPO / ".venv")
            and (REPO / "mcp_home").is_dir() and (REPO / "work").is_dir())


def ensure_venv(base_cmd):
    """Build and verify a sibling before moving any existing .venv."""
    target = REPO / ".venv"
    if venv_is_ready(target):
        return _venv_python(target)
    if not base_cmd:
        raise RuntimeError("External Python 3.11 was not found")

    replacement = REPO / (".venv.replacement-" + uuid.uuid4().hex)
    previous = REPO / (".venv.previous-" + uuid.uuid4().hex)
    print("Creating replacement venv: " + str(replacement))
    subprocess.run(list(base_cmd) + ["-m", "venv", str(replacement)], check=True)
    subprocess.run([str(_venv_python(replacement)), "-m", "pip", "install",
                    "mcp==" + MCP_VERSION], check=True)
    if not venv_is_ready(replacement):
        raise RuntimeError("Replacement venv failed Python 3.11 / FastMCP / mcp==1.30.0 checks; old .venv kept")

    moved_old = False
    try:
        if target.exists():
            target.rename(previous)
            moved_old = True
        replacement.rename(target)
        if not venv_is_ready(target):
            raise RuntimeError("Switched venv failed validation")
    except Exception as exc:
        if moved_old:
            try:
                if target.exists():
                    target.rename(replacement)
                previous.rename(target)
            except OSError as restore_error:
                raise RuntimeError("Venv switch failed; old environment is at %s; restore failed: %s" %
                                   (previous, restore_error)) from exc
        raise RuntimeError("Venv switch failed safely; old environment kept: %s" % exc) from exc
    if moved_old:
        print("Previous venv retained at: " + str(previous))
    return _venv_python(target)


def resolve_abaqus_cmd(interactive, existing=None):
    if existing:
        return runtime_detection.validate_abaqus_cmd(existing)
    try:
        found = runtime_detection.detect_abaqus()
    except ValueError as exc:
        if not interactive:
            raise
        print("[!!] " + str(exc))
        found = None
    if found:
        return found
    if not interactive:
        return None
    try:
        entered = input("Abaqus .bat/.exe full path or command name> ").strip()
        return runtime_detection.validate_abaqus_cmd(entered) if entered else None
    except (EOFError, ValueError) as exc:
        print("[!!] Invalid Abaqus command: " + str(exc))
        return None


def write_config(_venv_py, abq_cmd):
    # Keep the old callable signature for the D6 harness; no derived path is stored.
    return local_config.write_config(CONFIG_PATH, abq_cmd)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--yes", action="store_true", help="repair without a prompt")
    parser.add_argument("--dry-run", action="store_true", help="inspect without writing")
    args = parser.parse_args(argv)

    missing = verify_repo_files()
    if missing:
        print("[!!] Missing source: " + ", ".join(missing))
        return 1
    try:
        config, source = local_config.load_or_migrate(REPO, CONFIG_PATH, LOCAL_ENV,
                                                       write=False)
        existing_cmd = config["ABAQUS_CMD"] if config else None
        base_cmd = runtime_detection.detect_python()
        if not base_cmd:
            raise RuntimeError("External Python 3.11 is required")
        if args.dry_run:
            abq_cmd = resolve_abaqus_cmd(interactive=False, existing=existing_cmd)
            if not abq_cmd:
                raise RuntimeError("Abaqus command not found; supply a full .bat/.exe path or command name")
            print("[dry-run] source OK; Python=%s; Abaqus=%s; config source=%s" %
                  (base_cmd, abq_cmd, source))
            print("[dry-run] would verify/repair .venv and create mcp_home/ and work/")
            return 0

        ensure_venv(base_cmd)
        (REPO / "mcp_home").mkdir(exist_ok=True)
        (REPO / "work").mkdir(exist_ok=True)
        abq_cmd = resolve_abaqus_cmd(interactive=True, existing=existing_cmd)
        if not abq_cmd:
            raise RuntimeError("Abaqus command not found; supply a full .bat/.exe path or command name")
        if not CONFIG_PATH.exists():
            write_config(None, abq_cmd)
        print("[OK] Installed at " + str(REPO))
        print("[OK] Config: " + str(CONFIG_PATH))
        print("[OK] Legacy input: " + source + " (left unchanged)")
        print("Next: doctor.bat, then start_abaqus_agent.bat")
        return 0
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as exc:
        print("[!!] Installation stopped: " + str(exc))
        return 1


if __name__ == "__main__":
    sys.exit(main())
