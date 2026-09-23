"""Optional, networked L7 acceptance; uses disposable venvs only.

Run: py -3.11 -m tests.accept_python
Add --candidates to try locally installed 3.10/3.12/3.13/3.14 separately.
"""
import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from tests.support import ROOT


def run(cmd, **kwargs):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=240, **kwargs)


def check(version):
    probe = run(["py", "-" + version, "-c", "import sys; print(sys.executable)"])
    if probe.returncode:
        return "NOT_AVAILABLE", probe.stderr.strip()[-300:]
    with tempfile.TemporaryDirectory(prefix="abaqus-d6-python-") as tmp:
        env = Path(tmp) / "venv"
        created = run(["py", "-" + version, "-m", "venv", str(env)])
        if created.returncode:
            return "PROJECT_TESTED_FAIL", "venv: " + created.stderr.strip()[-300:]
        py = env / "Scripts" / "python.exe" if sys.platform == "win32" else env / "bin" / "python"
        installed = run([str(py), "-m", "pip", "install", "--disable-pip-version-check", "mcp==1.30.0"])
        if installed.returncode:
            return "PROJECT_TESTED_FAIL", "pip: " + installed.stderr.strip()[-300:]
        code = ("import importlib.metadata as m; from mcp.server.fastmcp import FastMCP; "
                "import runpy; x=runpy.run_path(%r, run_name='d6_import'); "
                "assert m.version('mcp')=='1.30.0'; assert isinstance(x['mcp'], FastMCP); "
                "print(m.version('mcp'))" % str(ROOT / "mcp_server.py"))
        loaded = run([str(py), "-c", code], env={**__import__("os").environ,
                                                   "ABAQUS_MCP_HOME": str(Path(tmp) / "mcp_home")})
        if loaded.returncode:
            return "PROJECT_TESTED_FAIL", "import/server: " + loaded.stderr.strip()[-500:]
        handshake = '''import asyncio, os, sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
async def main():
    params = StdioServerParameters(command=sys.executable, args=[sys.argv[1]], env=os.environ.copy())
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            names = [tool.name for tool in (await session.list_tools()).tools]
            assert "ping" in names and "check_abaqus_connection" in names, names
            print("STDIO_TOOLS=" + ",".join(names))
asyncio.run(main())'''
        connected = run([str(py), "-c", handshake, str(ROOT / "mcp_server.py")],
                        env={**__import__("os").environ, "ABAQUS_MCP_HOME": str(Path(tmp) / "mcp_home")})
        if connected.returncode:
            return "PROJECT_TESTED_FAIL", "stdio: " + connected.stderr.strip()[-500:]
        return "PROJECT_TESTED_PASS", "venv/import/FastMCP/STDIO discovery; mcp=" + loaded.stdout.strip()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidates", action="store_true")
    args = parser.parse_args()
    versions = ["3.11"] + (["3.10", "3.12", "3.13", "3.14"] if args.candidates else [])
    print(json.dumps({v: check(v) for v in versions}, ensure_ascii=False, indent=2))
