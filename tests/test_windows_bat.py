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

    def test_L6_start_helper_preserves_fake_command_arguments(self):
        from unittest import mock
        from tests.support import load
        with temp_home() as root:
            for label in self.PATH_CASES:
                with self.subTest(path=label):
                    repo = root / label
                    repo.mkdir()
                    archive_to(repo)
                    fake_abq = repo / "fake abaqus.exe"
                    fake_abq.write_bytes(b"fake")
                    (repo / ".abaqus-agent.json").write_text(
                        json.dumps({"schema_version": 1, "ABAQUS_CMD": str(fake_abq)}), encoding="utf-8")
                    helper = load("start_" + str(len(label)), "scripts/start_windows.py")
                    states = iter(("STOPPED", "BRIDGE_READY"))
                    with mock.patch.object(helper, "REPO", repo), \
                         mock.patch.object(helper.bridge_state, "state", side_effect=lambda: next(states)), \
                         mock.patch.object(helper.subprocess, "Popen") as launched:
                        self.assertEqual(helper.main(), 0)
                    args, kwargs = launched.call_args
                    self.assertEqual(args[0], [str(fake_abq), "cae", "script=" + str(repo / "abaqus_start_mcp.py")])
                    self.assertEqual(kwargs["env"]["ABAQUS_MCP_HOME"], str(repo / "mcp_home"))
                    self.assertEqual(kwargs["cwd"], str(repo / "work"))

    def test_L6_bat_launch_quotes_spaces_chinese_and_ampersand(self):
        with temp_home() as root:
            repo = root / '中文 & Abaqus Agent'
            repo.mkdir()
            fake = repo / 'fake & Abaqus.bat'
            fake.write_text('@echo off\necho %1 %2\n', encoding='ascii')
            script = repo / 'abaqus_start_mcp.py'
            launch = 'cmd.exe /d /v:off /s /c ""%s" cae "script=%s""' % (fake, script)
            result = subprocess.run(launch, capture_output=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(str(script).encode('utf-8'), result.stdout)
            self.assertIn(b'cae', result.stdout)
