"""Windows-only real BAT boundaries with disposable archive copies and fake targets."""
import json
import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

from tests.support import ROOT, archive_to, temp_home


@unittest.skipUnless(os.name == "nt", "Windows cmd.exe boundary")
class WindowsBatBoundary(unittest.TestCase):
    PATH_CASES = ("Abaqus Agent Test", "中文 测试", "Abaqus (test)", "Abaqus & Test")

    def run_bat(self, path, env):
        return subprocess.run(["cmd.exe", "/d", "/c", "call", str(path)],
                              cwd=path.parent, env=env, input=b"\r\n", capture_output=True,
                              creationflags=subprocess.CREATE_NO_WINDOW, timeout=25)

    def test_L6_install_bat_preserves_python_script_argument(self):
        with temp_home() as root:
            fake_bin = root / "fake-bin"
            fake_bin.mkdir()
            capture = root / "capture.py"
            capture.write_text("import json,os,sys\nfrom pathlib import Path\n"
                               "Path(os.environ['D6_ARG_LOG']).write_text(json.dumps(sys.argv[1:], ensure_ascii=False), encoding='utf-8')\n",
                               encoding="utf-8")
            (fake_bin / "py.cmd").write_text('@echo off\n"%D6_REAL_PY%" "%D6_CAPTURE%" %*\n', encoding="ascii")
            for index, label in enumerate((*self.PATH_CASES, "Abaqus ! Test")):
                with self.subTest(path=label):
                    repo = root / label
                    repo.mkdir()
                    archive_to(repo)
                    (repo / "install.bat").write_bytes((ROOT / "install.bat").read_bytes())
                    log = root / (str(index) + ".json")
                    env = {**os.environ, "PATH": str(fake_bin) + os.pathsep + os.environ.get("PATH", ""),
                           "TEMP": str(root), "TMP": str(root), "D6_REAL_PY": sys.executable,
                           "D6_CAPTURE": str(capture), "D6_ARG_LOG": str(log)}
                    result = self.run_bat(repo / "install.bat", env)
                    self.assertEqual(result.returncode, 0, result.stdout[-500:])
                    self.assertEqual(json.loads(log.read_text(encoding="utf-8")),
                                     [str(repo / "scripts" / "bootstrap_windows.py")])

    def test_L6_start_bat_preserves_fake_command_arguments(self):
        with temp_home() as root:
            sitecustomize = root / "sitecustomize.py"
            sitecustomize.write_text("import json,os,sys\nfrom pathlib import Path\n"
                                    "if Path(sys.executable).name.lower() == 'fake abaqus.exe':\n"
                                    " Path(os.environ['D6_ARG_LOG']).write_text(json.dumps(sys.argv, ensure_ascii=False), encoding='utf-8')\n"
                                    " status=Path(os.environ['D6_STATUS_PATH']); status.parent.mkdir(parents=True,exist_ok=True)\n"
                                    " status.write_text(json.dumps({'status':'running'}, indent=2),encoding='utf-8')\n"
                                    " os._exit(0)\n", encoding="utf-8")
            for label in self.PATH_CASES:
                with self.subTest(path=label):
                    repo = root / label
                    repo.mkdir()
                    archive_to(repo)
                    venv = subprocess.run([sys.executable, "-m", "venv", "--without-pip", str(repo / ".venv")],
                                          capture_output=True, timeout=25)
                    self.assertEqual(venv.returncode, 0, venv.stderr[-500:])
                    fake_abq = repo / "fake abaqus.exe"
                    shutil.copy2(repo / ".venv" / "Scripts" / "python.exe", fake_abq)
                    shutil.copy2(repo / ".venv" / "pyvenv.cfg", repo / "pyvenv.cfg")
                    log = root / ("start-" + str(self.PATH_CASES.index(label)) + ".json")
                    env = {**os.environ, "TEMP": str(root), "TMP": str(root), "PYTHONPATH": str(root),
                           "D6_ARG_LOG": str(log),
                           "D6_STATUS_PATH": str(repo / "mcp_home" / "status.json"),
                           "ABAQUS_CMD": str(fake_abq)}
                    (repo / ".abaqus-agent.json").write_text(
                        json.dumps({"schema_version": 1, "ABAQUS_CMD": str(fake_abq)}), encoding="utf-8")
                    proc = subprocess.Popen(["cmd.exe", "/d", "/c", "call", str(repo / "start_abaqus_agent.bat")],
                                            cwd=repo, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                            creationflags=subprocess.CREATE_NO_WINDOW)
                    try:
                        import time
                        deadline = time.monotonic() + 10
                        while not log.exists() and time.monotonic() < deadline:
                            time.sleep(.05)
                        self.assertTrue(log.exists(), "launcher never called fake Abaqus; process=" + str(proc.poll()))
                    finally:
                        proc.kill()
                        proc.communicate(timeout=5)
                    self.assertEqual(json.loads(log.read_text(encoding="utf-8")),
                                     ["cae", "script=" + str(repo / "abaqus_start_mcp.py")])
