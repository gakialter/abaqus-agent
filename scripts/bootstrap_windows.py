# -*- coding: utf-8 -*-
"""
Zero-base Windows bootstrap for abaqus-agent.

This is the "one-click" installer behind install.bat. It REUSES the detection
logic from setup_abaqus_agent.py (detect_python / detect_abaqus) but targets
the REPO ITSELF as the workspace instead of copying files out to a new
directory. That keeps the repo as the single source of truth and, crucially,
does NOT overwrite the newer root-level bridge files (plugin / mcp_server)
that an older scripts/ copy would clobber.

What it does:
  1. Locate the repo root (%~dp0..  / parent of this file).
  2. Detect a system Python (reused from setup_abaqus_agent.detect_python).
  3. Detect Abaqus (reused from setup_abaqus_agent.detect_abaqus); ask the
     user to type a command/path if it cannot be found automatically.
  4. Create an isolated .venv inside the repo and install mcp<2 into it
     (never into Abaqus's bundled Python).
  5. Verify the bridge files / skill files are present.
  6. Write a user-local config: %USERPROFILE%\\.abaqus-agent.local.json
     (workspace, abaqus command, python, skill source - NO secrets).
  7. Install/sync the Skill (SKILL.md + references/) into any detected
     Doubao Work skill runtime; if no runtime is detected, write
     doubao_skill_install.txt with the manual fallback.
  8. Print a simple [OK] summary.

Idempotent. Never touches Abaqus install dirs or the License.
"""
import argparse
import datetime as _dt
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent          # scripts/
REPO = HERE.parent                              # repo root = workspace
CONFIG_PATH = Path(os.environ.get("USERPROFILE", str(Path.home()))) / ".abaqus-agent.local.json"
LOCAL_ENV = REPO / ".abaqus-agent.local"        # BAT-sourced, gitignored

# Reuse existing detection logic instead of reinventing it.
sys.path.insert(0, str(HERE))
try:
    import setup_abaqus_agent as _setup
    detect_python = _setup.detect_python
    detect_abaqus = _setup.detect_abaqus
except Exception as _e:  # pragma: no cover - degrade gracefully
    print("[!] Could not import setup_abaqus_agent: %s" % _e)
    detect_python = None
    detect_abaqus = None


def info(msg):
    print(msg)


def ok(msg):
    print("[OK] " + msg)


def warn(msg):
    print("[!!] " + msg)


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------

def pick_venv_python():
    """Return a command list to launch the base interpreter used to make the venv."""
    if detect_python is None:
        return None
    return detect_python()


def resolve_abaqus_cmd(interactive):
    abq = detect_abaqus() if detect_abaqus else None
    if abq:
        return abq
    if not interactive:
        return None
    print()
    print("[!] Abaqus command not found automatically.")
    print("    Type the abaqus command or the full path to abaqus.bat, then press Enter.")
    print("    Examples:")
    print("      abaqus")
    print("      D:\\SIMULIA\\EstProducts\\2026\\win_b64\\code\\bin\\abq2026.bat")
    try:
        val = input("    abaqus command/path> ").strip().strip('"')
    except EOFError:
        val = ""
    return val or None


# ---------------------------------------------------------------------------
# .venv (isolated, never Abaqus Python)
# ---------------------------------------------------------------------------

def ensure_venv(base_cmd):
    venv_py = REPO / ".venv" / "Scripts" / "python.exe"
    if venv_py.exists():
        # Sanity: can it run and import mcp?
        try:
            r = subprocess.run([str(venv_py), "-c", "import mcp, sys; print(sys.version)"],
                               capture_output=True, text=True)
            if r.returncode == 0:
                return str(venv_py)
            warn("Existing .venv is broken; rebuilding it.")
            shutil.rmtree(REPO / ".venv", ignore_errors=True)
        except Exception:
            shutil.rmtree(REPO / ".venv", ignore_errors=True)

    if not base_cmd:
        return None
    info("     Creating isolated .venv inside the repo (one time, may take a minute)...")
    subprocess.run(base_cmd + ["-m", "venv", str(REPO / ".venv")], check=True)
    subprocess.run([str(venv_py), "-m", "pip", "install", "--upgrade", "pip"], check=True)
    subprocess.run([str(venv_py), "-m", "pip", "install", "mcp<2"], check=True)
    return str(venv_py)


# ---------------------------------------------------------------------------
# Verification of shipped files
# ---------------------------------------------------------------------------

REQUIRED_FILES = [
    "SKILL.md",
    "client.py",
    "mcp_server.py",
    "abaqus_mcp_plugin.py",
    "abaqus_start_mcp.py",
]
REQUIRED_DIRS = ["references", "mcp_home"]


def verify_repo_files():
    missing = []
    for f in REQUIRED_FILES:
        if not (REPO / f).is_file():
            missing.append(f)
    for d in REQUIRED_DIRS:
        if not (REPO / d).is_dir():
            missing.append(d + "/")
    return missing


# ---------------------------------------------------------------------------
# Skill install / sync
# ---------------------------------------------------------------------------

def skill_runtime_candidates():
    """Known Doubao Work skill roots, derived from env (no hard-coded username)."""
    cands = []
    local = os.environ.get("LOCALAPPDATA", "")
    home = os.environ.get("USERPROFILE", "")
    if local:
        cands.append(os.path.join(
            local, r"DoubaoWork\User Data\Default\.doubaowork\agent_mode\workspace\.user_skills"))
        cands.append(os.path.join(
            local, r"DoubaoWork\User Data\Default\.doubaowork\agent_mode\workspace\.skills"))
    if home:
        cands.append(os.path.join(home, "DoubaoWork", "skills"))
        cands.append(os.path.join(home, ".agents", "skills"))
    return [c for c in cands if os.path.isdir(c)]


def sync_skill_to_runtime(runtime_root):
    target = Path(runtime_root) / "abaqus-agent"
    # Lightweight backup if a previous version exists.
    if target.exists():
        stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = Path(runtime_root) / ("abaqus-agent.bak-" + stamp)
        try:
            shutil.copytree(str(target), str(backup))
            info("     Backed up existing skill to %s" % backup)
        except Exception as e:
            warn("Could not back up old skill (%s); overwriting anyway." % e)
        shutil.rmtree(str(target), ignore_errors=True)

    target.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(REPO / "SKILL.md"), str(target / "SKILL.md"))
    shutil.copytree(str(REPO / "references"), str(target / "references"))
    return str(target)


def write_fallback_install_text():
    txt = REPO / "doubao_skill_install.txt"
    txt.write_text(
        "abaqus-agent skill auto-install\n"
        "================================\n"
        "No Doubao Work skill runtime folder was detected automatically.\n"
        "In Doubao Work, paste the self-install prompt from\n"
        "bootstrap_for_doubao_work.md (section: give to Doubao Work),\n"
        "which asks Work to detect its own runtime and sync SKILL.md + references/.\n"
        "Repository (single source of truth):\n  %s\n" % str(REPO),
        encoding="utf-8",
    )
    return str(txt)


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def write_config(venv_py, abq_cmd):
    cfg = {
        "config_version": 1,
        "workspace": str(REPO),
        "mcp_home": str(REPO / "mcp_home"),
        "venv_python": str(venv_py) if venv_py else "",
        "abaqus_cmd": abq_cmd or "",
        "skill_source": str(REPO),
        "installed_at": _dt.datetime.now().isoformat(timespec="seconds"),
    }
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    # BAT-sourced mini config (start_abaqus_agent.bat reads this; no JSON parse needed).
    LOCAL_ENV.write_text(
        "@rem auto-generated by bootstrap_windows.py - safe to delete, recreated by install.bat\n"
        'set "ABAQUS_CMD=%s"\n' % (abq_cmd or "abaqus"),
        encoding="utf-8",
    )
    return str(CONFIG_PATH)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def already_ready():
    venv_py = REPO / ".venv" / "Scripts" / "python.exe"
    return (venv_py.exists() and CONFIG_PATH.exists()
            and (REPO / "SKILL.md").is_file() and (REPO / "references").is_dir())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--yes", action="store_true", help="non-interactive (no repair/quit prompt)")
    ap.add_argument("--dry-run", action="store_true", help="print actions, do not write anything")
    args = ap.parse_args()

    print("=" * 60)
    print(" abaqus-agent bootstrap  (repo: %s)" % REPO)
    print("=" * 60)

    # Idempotency: existing install?
    if already_ready() and not args.yes and not args.dry_run:
        print("Existing installation detected.")
        ans = input("  [R] repair/update  or  [Q] quit ? [R] ").strip().lower()
        if ans == "q":
            print("Aborted. Nothing changed.")
            return 0

    # 1) Verify repo files
    missing = verify_repo_files()
    if missing:
        warn("Missing files in repo: %s" % ", ".join(missing))
        warn("Did you download the whole ZIP and unzip it completely?")
        return 1
    ok("Repository files present")

    # 2) Python
    base_cmd = pick_venv_python()
    if not base_cmd:
        warn("No suitable system Python found. Install Python 3.11-3.13 (or have py launcher).")
        return 1
    ok("Python base interpreter: %s" % " ".join(base_cmd))

    # 3) Abaqus
    abq_cmd = resolve_abaqus_cmd(interactive=not args.dry_run)
    if not abq_cmd:
        warn("Abaqus command not found and none entered.")
        warn("Re-run install.bat and type the abaqus command/path when asked.")
        return 1
    ok("Abaqus command: %s" % abq_cmd)

    # 4) venv
    if args.dry_run:
        venv_py = str(REPO / ".venv" / "Scripts" / "python.exe")
        info("     [dry-run] would create/verify .venv and install mcp<2")
    else:
        venv_py = ensure_venv(base_cmd)
        if not venv_py:
            warn("Could not create .venv.")
            return 1
    ok("Isolated venv ready (no packages into Abaqus Python)")

    # 5) Config
    if args.dry_run:
        info("     [dry-run] would write %s" % CONFIG_PATH)
    else:
        cfg_path = write_config(venv_py, abq_cmd)
    ok("Config written")

    # 6) Skill
    runtimes = skill_runtime_candidates()
    if args.dry_run:
        if runtimes:
            for r in runtimes:
                info("     [dry-run] would sync skill -> %s\\abaqus-agent" % r)
        else:
            info("     [dry-run] no skill runtime detected; would write doubao_skill_install.txt")
    else:
        if runtimes:
            for r in runtimes:
                tgt = sync_skill_to_runtime(r)
                ok("Skill synced -> %s" % tgt)
        else:
            fb = write_fallback_install_text()
            warn("No skill runtime detected automatically.")
            warn("Wrote fallback: %s" % fb)
            warn("Use the self-install prompt in bootstrap_for_doubao_work.md inside Doubao Work.")

    # Summary
    print()
    print("=" * 60)
    ok("abaqus-agent installed")
    print()
    print("Next: double-click  start_abaqus_agent.bat")
    print("      then open Doubao Work and start building.")
    print("      If anything looks wrong, double-click doctor.bat.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
