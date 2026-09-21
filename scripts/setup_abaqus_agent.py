# -*- coding: utf-8 -*-
"""
One-click installer: wire this machine's Abaqus/CAE to an AI agent via file-IPC MCP.

Idempotent. Creates an isolated workspace (default %USERPROFILE%\\Desktop\\abaqus-agent)
with its own venv, copies the Abaqus-side plugin, and prints the exact launch command.

Usage (from any terminal):
    python setup_abaqus_agent.py
    python setup_abaqus_agent.py --workspace D:\\abaqus-agent --abaqus-cmd abaqus

After it finishes, start Abaqus with the printed command and you are done.
No Abaqus install directory or License files are modified.
"""
import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BUNDLED_PLUGIN = HERE / "abaqus_mcp_plugin.py"
BUNDLED_CLIENT = HERE / "client.py"
BUNDLED_MCP_SERVER = HERE / "mcp_server.py"
BUNDLED_SKILL_MD = HERE.parent / "SKILL.md"
LAUNCHER_TEMPLATE = (HERE / "abaqus_start_mcp.py").read_text(encoding="utf-8")


def which(name):
    return shutil.which(name)


def detect_abaqus():
    for cand in ("abaqus", "abq2026", "abaqus2026"):
        p = which(cand)
        if p:
            return p
    # Common EstProducts layout
    for root in (r"C:\Program Files\SIMULIA\EstProducts", r"D:\SIMULIA\EstProducts"):
        if Path(root).exists():
            for v in Path(root).iterdir():
                bat = v / "win_b64" / "code" / "bin" / "abq2026.bat"
                if bat.exists():
                    return str(bat)
    return None


def detect_python():
    """Pick a system Python for the venv. Prefer 3.11-3.13 (known to install
    mcp<2 cleanly); avoid 3.10 (Abaqus's bundled interpreter)."""
    good, other = [], []
    try:
        out = subprocess.run(["py", "-0"], capture_output=True, text=True)
        for line in out.stdout.splitlines():
            line = line.strip()
            if not line.startswith("-V:3."):
                continue
            ver = line.split()[0].split(":")[1]
            r = subprocess.run(["py", f"-{ver}", "-c",
                               "import sys; print('%d.%d' % sys.version_info[:2])"],
                               capture_output=True, text=True)
            v = r.stdout.strip()
            if not v or v == "3.10":
                continue
            minor = int(v.split(".")[1])
            if 11 <= minor <= 13:
                good.append(["py", f"-{ver}"])
            elif minor >= 10:
                other.append(["py", f"-{ver}"])
    except Exception:
        pass
    if good:
        return good[0]
    if other:
        return other[0]
    p = which("python")
    return [p] if p else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", default=str(Path.home() / "Desktop" / "abaqus-agent"),
                    help="isolated workspace dir (default ~/Desktop/abaqus-agent)")
    ap.add_argument("--abaqus-cmd", default=None, help="abaqus command/bat (auto-detected)")
    args = ap.parse_args()

    ws = Path(args.workspace)
    ws.mkdir(parents=True, exist_ok=True)
    (ws / "mcp_home").mkdir(exist_ok=True)
    (ws / "work").mkdir(exist_ok=True)

    abq = args.abaqus_cmd or detect_abaqus()
    if not abq:
        print("!! Could not auto-detect the abaqus command. Pass --abaqus-cmd.")
        sys.exit(1)
    print(f"[1/5] Abaqus command : {abq}")

    py = detect_python()
    if not py:
        print("!! No suitable system Python found. Need Python 3.11+ on PATH.")
        sys.exit(1)
    print(f"[2/5] Venv Python    : {' '.join(py)}")

    print("[3/5] Copying plugin + client ...")
    shutil.copy(BUNDLED_PLUGIN, ws / "abaqus_mcp_plugin.py")
    shutil.copy(BUNDLED_CLIENT, ws / "client.py")
    shutil.copy(BUNDLED_MCP_SERVER, ws / "mcp_server.py")

    # Copy SKILL.md if present in the repo; otherwise note it must be installed
    # separately by pointing your agent at the repo root.
    if BUNDLED_SKILL_MD.exists():
        shutil.copy(BUNDLED_SKILL_MD, ws / "SKILL.md")
        skill_copied = True
    else:
        skill_copied = False
    launcher = LAUNCHER_TEMPLATE.replace("__WORKSPACE__", str(ws))
    (ws / "abaqus_start_mcp.py").write_text(launcher, encoding="utf-8")

    # Emit a ready-to-use MCP client config (env embedded, no manual `set` needed).
    import json as _json
    venv_py = ws / ".venv" / "Scripts" / "python.exe"
    mcp_cfg = {
        "mcpServers": {
            "abaqus": {
                "command": str(venv_py),
                "args": [str(ws / "mcp_server.py")],
                "env": {"ABAQUS_MCP_HOME": str(ws / "mcp_home")},
            }
        }
    }
    (ws / "mcp_client_config.json").write_text(_json.dumps(mcp_cfg, indent=2), encoding="utf-8")

    venv_py = ws / ".venv" / "Scripts" / "python.exe"
    if not venv_py.exists():
        print("[4/5] Creating venv + installing mcp<2 (this may take a minute) ...")
        subprocess.run(py + ["-m", "venv", str(ws / ".venv")], check=True)
        subprocess.run([str(venv_py), "-m", "pip", "install", "--upgrade", "pip"], check=True)
        subprocess.run([str(venv_py), "-m", "pip", "install", "mcp<2"], check=True)
    else:
        print("[4/5] venv already exists, skipping install.")

    print("[5/5] Done.")
    print()
    print("=" * 64)
    print("NEXT STEPS")
    print("=" * 64)
    print(f'1) Start Abaqus/CAE and auto-load the bridge:')
    print(f'     set ABAQUS_MCP_HOME={ws}\\mcp_home')
    print(f'     "{abq}" cae script="{ws}\\abaqus_start_mcp.py"')
    print(f"   wait ~20-40s until {ws}\\mcp_home\\status.json shows status=\"running\"")
    print()
    print(f'2) Verify the link (ping round-trip):')
    print(f'     set ABAQUS_MCP_HOME={ws}\\mcp_home')
    print(f'     "{venv_py}" "{ws}\\client.py"')
    print()
    print(f'3) Drive Abaqus directly:')
    print(f'     "{venv_py}" "{ws}\\client.py"   (then import client; send("execute_script", ...))')
    print()
    print("4) MCP client config (already generated, env embedded):")
    print(f'     {ws}\\mcp_client_config.json')
    print("     - Cursor: merge the mcpServers entry into .cursor/mcp.json")
    print("     - Claude Desktop: merge it into claude_desktop_config.json")
    print("     - Codex: copy command/args/env into config.toml [[mcp_servers]]")
    print("     Nothing in your global agent config is modified automatically.")
    print("=" * 64)

    if skill_copied:
        print("5) Skill installed at:")
        print(f'     {ws}\\SKILL.md')
        print("     Point your agent skill directory at this workspace to load it.")
    else:
        print("5) Skill (SKILL.md) was NOT bundled with this installer.")
        print("   Install it separately by cloning the repo and pointing your agent")
        print("   skill root at the repo directory that contains SKILL.md.")
    print("=" * 64)


if __name__ == "__main__":
    main()
