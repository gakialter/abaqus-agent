# -*- coding: utf-8 -*-
"""
Doctor for abaqus-agent - one-shot health check used by doctor.bat.

Checks the whole chain from repo files down to a live Abaqus kernel round-trip.
Never submits a heavy job; the only kernel exercise is a minimal
    from abaqus import mdb; print(mdb.models.keys())

Output is intentionally short and English-keyword so it survives console
codepage differences. Chinese guidance lives in the .md docs.
"""
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
MCP_HOME = REPO / "mcp_home"
STATUS_FILE = MCP_HOME / "status.json"
CONFIG_PATH = Path(os.environ.get("USERPROFILE", str(Path.home()))) / ".abaqus-agent.local.json"

results = []  # (index, name, PASS/FAIL, detail)


def record(idx, name, ok_flag, detail=""):
    results.append((idx, name, "PASS" if ok_flag else "FAIL", detail))


def proc_alive(pid):
    if not pid:
        return False
    try:
        out = subprocess.run(["tasklist", "/FI", "PID eq %d" % int(pid)],
                             capture_output=True, text=True).stdout
        return str(pid) in out
    except Exception:
        return False


def check_repo():
    need_files = ["SKILL.md", "client.py", "mcp_server.py",
                  "abaqus_mcp_plugin.py", "abaqus_start_mcp.py"]
    need_dirs = ["references", "mcp_home"]
    missing = [f for f in need_files if not (REPO / f).is_file()]
    missing += [d for d in need_dirs if not (REPO / d).is_dir()]
    record(1, "repository", not missing,
           "all shipped files present" if not missing else "missing: " + ", ".join(missing))


def check_venv_py():
    venv_py = REPO / ".venv" / "Scripts" / "python.exe"
    record(2, "python", venv_py.exists(), str(venv_py) if venv_py.exists() else ".venv python.exe not found")
    return venv_py


def check_venv(venv_py):
    record(3, "venv", venv_py.exists(), "isolated repo .venv" if venv_py.exists() else "run install.bat")


def check_packages(venv_py):
    if not venv_py.exists():
        record(4, "packages", False, "no venv")
        return
    try:
        r = subprocess.run([str(venv_py), "-c", "import mcp"], capture_output=True, text=True)
        if r.returncode == 0:
            record(4, "packages", True, "mcp importable in venv")
        else:
            last = (r.stderr.strip().splitlines() or ["import mcp failed"])[-1]
            record(4, "packages", False, last)
    except Exception as e:
        record(4, "packages", False, str(e))


def load_config():
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def check_abaqus(cfg):
    abq = cfg.get("abaqus_cmd", "")
    if not abq:
        # Fall back to PATH lookup.
        found = None
        for c in ("abaqus", "abq2026"):
            from shutil import which
            found = which(c)
            if found:
                abq = found
                break
    ok_flag = bool(abq) and (os.path.exists(abq) or _on_path(abq))
    record(5, "abaqus", ok_flag, abq or "not configured; run install.bat")


def _on_path(cmd):
    from shutil import which
    return which(cmd) is not None


def check_mcp_home():
    record(6, "ABAQUS_MCP_HOME", str(MCP_HOME) == str(cfg_mcp_home()) or MCP_HOME.is_dir(),
           str(MCP_HOME))


def cfg_mcp_home():
    return MCP_HOME


def check_mcp_home_writable():
    probe = MCP_HOME / ".doctor_write_test.tmp"
    try:
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        record(7, "mcp_home writable", True, str(MCP_HOME))
    except Exception as e:
        record(7, "mcp_home writable", False, str(e))


def check_status_json():
    if not STATUS_FILE.exists():
        record(8, "status.json", False, "no status.json yet (start the bridge)")
        return None
    try:
        st = json.loads(STATUS_FILE.read_text(encoding="utf-8"))
        record(8, "status.json", True,
               "%s @ %s" % (st.get("status"), st.get("datetime", "?")))
        return st
    except Exception as e:
        record(8, "status.json", False, str(e))
        return None


def check_bridge_state(st):
    if st is None:
        record(9, "bridge", False, "no status")
        return False
    alive = proc_alive(st.get("pid"))
    fresh = (time.time() - float(st.get("timestamp", 0))) < 15
    running = st.get("status") == "running"
    ok_flag = bool(running and (alive or fresh))
    detail = "pid=%s alive=%s fresh=%s" % (st.get("pid"), alive, fresh)
    record(9, "bridge", ok_flag, detail)
    return ok_flag


def _venv_client_call(venv_py, cmd_type, **kwargs):
    """Run a one-off client.send() inside the venv python (same process as agent)."""
    kw = dict(kwargs)
    kw.setdefault("timeout", 30)
    code = (
        "import os,sys,json;"
        "os.environ['ABAQUS_MCP_HOME']=r'%s';"
        "sys.path.insert(0,r'%s');"
        "import client;"
        "r=client.send(%s,**%s);"
        "print(json.dumps(r))"
        % (str(MCP_HOME), str(REPO), json.dumps(cmd_type), json.dumps(kw))
    )
    r = subprocess.run([str(venv_py), "-c", code], capture_output=True, text=True)
    if r.returncode != 0:
        return {"success": False, "error": r.stderr.strip() or "client call failed"}
    try:
        return json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:
        return {"success": False, "error": "bad client output: " + r.stdout.strip()[:200]}


def check_ping(venv_py, bridge_ok):
    if not bridge_ok:
        record(10, "ping", False, "bridge not running")
        return
    res = _venv_client_call(venv_py, "ping", timeout=15)
    record(10, "ping", bool(res.get("success")),
           json.dumps(res.get("data", res.get("error", "")), ensure_ascii=False)[:80])


def check_kernel(venv_py, bridge_ok):
    if not bridge_ok:
        record(11, "kernel", False, "bridge not running")
        return
    script = "from abaqus import mdb; print('models=' + str(list(mdb.models.keys())))"
    res = _venv_client_call(venv_py, "execute_script", script=script, timeout=60)
    out = (res.get("output") or "").strip()
    record(11, "kernel", bool(res.get("success")),
           out or res.get("error", "")[:100])


def check_skill_files():
    record(12, "skill files",
           (REPO / "SKILL.md").is_file() and (REPO / "references").is_dir(),
           "SKILL.md + references/")


def check_skill_links():
    skill_md = REPO / "SKILL.md"
    if not skill_md.exists():
        record(13, "skill links", False, "SKILL.md missing")
        return
    text = skill_md.read_text(encoding="utf-8")
    links = set(re.findall(r"\]\((references/[^)]+)\)", text))
    bad = [l for l in sorted(links) if not (REPO / l).is_file()]
    record(13, "skill links", not bad,
           "%d reference link(s)" % len(links) if not bad else "broken: " + ", ".join(bad))


def main():
    cfg = load_config()
    venv_py = check_venv_py and (REPO / ".venv" / "Scripts" / "python.exe")

    check_repo()
    check_venv(venv_py)
    check_packages(venv_py)
    check_abaqus(cfg)
    check_mcp_home()
    check_mcp_home_writable()
    st = check_status_json()
    bridge_ok = check_bridge_state(st)
    check_ping(venv_py, bridge_ok)
    check_kernel(venv_py, bridge_ok)
    check_skill_files()
    check_skill_links()

    # Report
    print()
    print("Environment")
    print("-----------")
    overall = True
    for idx, name, verdict, detail in results:
        if verdict == "FAIL":
            overall = False
        line = "%-12s %s" % (name, verdict)
        if detail:
            line += "   " + detail
        print(line)
    print("-----------")
    print("Overall: " + ("READY" if overall else "NOT READY"))
    if not overall:
        print()
        print("Fix hints:")
        print(" - Python/venv/packages FAIL  -> double-click install.bat")
        print(" - abaqus FAIL                -> re-run install.bat and enter the abaqus path")
        print(" - status/bridge FAIL         -> double-click start_abaqus_agent.bat")
        print(" - ping/kernel FAIL           -> wait 30s for Abaqus/CAE to finish loading, re-run doctor.bat")
        print(" - skill links FAIL           -> re-download the whole ZIP (references/ incomplete)")
    return 0 if overall else 1


if __name__ == "__main__":
    sys.exit(main())
