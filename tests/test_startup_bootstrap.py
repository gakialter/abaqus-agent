import json
import os
import subprocess
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from tests.support import ROOT, archive_to, load, temp_home


class Readiness(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="abaqus-d6-state-")
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.state = load("d6_bridge_state_" + self.home.name.replace("-", "_"), "scripts/bridge_state.py")
        self.state.MCP_HOME = self.home
        self.state.STATUS_FILE = self.home / "status.json"
        self.sid = "a" * 32
        (self.home / "owner.json").write_text(json.dumps({"session_id": self.sid}), encoding="utf-8")

    def probe(self, status=None, pong=None, locked=True):
        if status is not None:
            self.state.STATUS_FILE.write_text(status if isinstance(status, str) else json.dumps(status), encoding="utf-8")
        pong = pong or {"success": False}
        with mock.patch.object(self.state, "_locked", return_value=locked), \
             mock.patch.dict("sys.modules", {"client": mock.Mock(send=mock.Mock(return_value=pong))}):
            return self.state.state()

    def test_L5_no_malformed_stale_wrong_status(self):
        self.assertEqual(self.probe(locked=False), "STOPPED")
        self.assertEqual(self.probe("{"), "BUSY_UNRESPONSIVE")
        pong = {"success": True, "data": {"session_id": self.sid}}
        self.assertEqual(self.probe({"status": "running", "timestamp": time.time()-100, "session_id": self.sid}, pong), "BUSY_UNRESPONSIVE")
        self.assertEqual(self.probe({"status": "stopped", "timestamp": time.time(), "session_id": self.sid}, pong), "BUSY_UNRESPONSIVE")
        self.assertEqual(self.probe({"status": "running", "timestamp": time.time(), "session_id": self.sid}), "BUSY_UNRESPONSIVE")

    def test_L5_status_X_ping_X_is_ready(self):
        status = {"status": "running", "timestamp": time.time(), "session_id": self.sid}
        pong = {"success": True, "data": {"session_id": self.sid}}
        self.assertEqual(self.probe(status, pong), "BRIDGE_READY")

    def test_L5_legacy_fresh_status_is_not_ready(self):
        self.assertEqual(self.probe({"status": "running", "timestamp": time.time()}), "BUSY_UNRESPONSIVE")

    def test_L5_future_timestamp_is_not_fresh(self):
        status = {"status": "running", "timestamp": time.time()+10000, "session_id": self.sid}
        self.assertEqual(self.probe(status, {"success": True, "data": {"session_id": self.sid}}), "BUSY_UNRESPONSIVE")

    def test_L5_status_and_ping_must_share_session(self):
        status = {"status": "running", "timestamp": time.time(), "session_id": self.sid}
        self.assertEqual(self.probe(status, {"success": True, "data": {"session_id": "b" * 32}}), "BUSY_UNRESPONSIVE")

    def test_L5_start_batch_requires_ping_after_new_status(self):
        batch = (ROOT / "start_abaqus_agent.bat").read_text(encoding="utf-8")
        helper = (ROOT / "scripts/start_windows.py").read_text(encoding="utf-8")
        self.assertIn("scripts\\start_windows.py", batch)
        self.assertIn("bridge_state.state()", helper)


class Bootstrap(unittest.TestCase):
    def test_L6_archive_copy_paths_and_missing_runtime(self):
        paths = [r"C:\Temp\Abaqus Agent Test", r"C:\Temp\中文 测试\abaqus-agent",
                 r"C:\Temp\Abaqus (test)", r"C:\Temp\Abaqus & Test"]
        with temp_home() as root:
            for label in paths:
                # Use each Windows spelling as an isolated directory name under temp.
                dst = root / label.split("\\")[-1]
                dst.mkdir()
                archive_to(dst)
                self.assertFalse((dst / ".venv").exists())
                self.assertFalse((dst / "mcp_home").exists())
                self.assertFalse((dst / "work").exists())
                self.assertTrue((dst / "SKILL.md").exists())

    def test_L6_clean_archive_preflight_passes(self):
        with temp_home() as repo:
            bootstrap = load("d6_bootstrap_preflight", "scripts/bootstrap_windows.py")
            archive_to(repo)
            for name in ("local_config.py", "runtime_detection.py"):
                (repo / "scripts" / name).write_bytes((ROOT / "scripts" / name).read_bytes())
            with mock.patch.object(bootstrap, "REPO", repo):
                self.assertEqual(bootstrap.verify_repo_files(), [])

    def test_L6_missing_venv_and_missing_abaqus_are_detected(self):
        bootstrap = load("d6_bootstrap_missing", "scripts/bootstrap_windows.py")
        with temp_home() as repo, mock.patch.object(bootstrap, "REPO", repo), \
             mock.patch.object(bootstrap, "CONFIG_PATH", repo / "user.json"):
            self.assertFalse(bootstrap.already_ready())
            with mock.patch.object(bootstrap.runtime_detection, "detect_abaqus", return_value=None):
                self.assertIsNone(bootstrap.resolve_abaqus_cmd(interactive=False))

    def test_L6_one_fake_bat_or_exe_candidate_auto_selects(self):
        setup = load("d6_setup_detection", "scripts/runtime_detection.py")
        with temp_home() as home:
            for name in ("Abaqus Agent Test/fake abaqus.bat", "中文 测试/fake abaqus.exe"):
                executable = home / name
                executable.parent.mkdir(parents=True, exist_ok=True)
                executable.write_bytes(b"fake")
                with mock.patch.object(setup, "which", side_effect=lambda candidate: str(executable) if candidate == "abaqus" else None):
                    self.assertEqual(setup.detect_abaqus(), str(executable))

    def test_L6_multiple_abaqus_candidates_are_not_silently_selected(self):
        setup = load("d61_setup_ambiguous", "scripts/runtime_detection.py")
        with temp_home() as home:
            first, second = home / "one.bat", home / "two.exe"
            first.write_bytes(b"fake")
            second.write_bytes(b"fake")
            candidates = {"abaqus": str(first), "abq2026": str(second)}
            with mock.patch.object(setup, "which", side_effect=lambda name: candidates.get(name)):
                try:
                    selected = setup.detect_abaqus()
                except (ValueError, RuntimeError):
                    return  # explicit ambiguity is acceptable
            self.assertNotEqual(selected, str(first))

    def test_L6_unexpected_abaqus_command_arguments_are_invalid(self):
        bootstrap = load("d61_bootstrap_args", "scripts/bootstrap_windows.py")
        with temp_home() as home:
            fake = home / "fake abaqus.bat"
            fake.write_text("@echo off\n", encoding="ascii")
            with mock.patch.object(bootstrap.runtime_detection, "detect_abaqus", return_value=None), \
                 mock.patch("builtins.input", return_value=str(fake) + " --unexpected"):
                self.assertIsNone(bootstrap.resolve_abaqus_cmd(interactive=True))

    def test_L7_release_python_is_311_only(self):
        setup = load("d6_setup_python", "scripts/runtime_detection.py")
        def fake_run(args, **kwargs):
            stdout = "3.10\n"
            return subprocess.CompletedProcess(args, 0, stdout, "")
        with mock.patch.object(setup.subprocess, "run", side_effect=fake_run), \
             mock.patch.object(setup, "which", side_effect=lambda name: name):
            self.assertIsNone(setup.detect_python())

    def test_L6_partial_venv_is_not_ready(self):
        bootstrap = load("d6_bootstrap_partial", "scripts/bootstrap_windows.py")
        with temp_home() as repo, mock.patch.object(bootstrap, "REPO", repo), \
             mock.patch.object(bootstrap, "CONFIG_PATH", repo / "user.json"):
            py = repo / ".venv" / "Scripts" / "python.exe"
            py.parent.mkdir(parents=True)
            py.write_bytes(b"broken")
            (repo / "user.json").write_text("{}")
            (repo / "SKILL.md").write_text("fixture")
            (repo / "references").mkdir()
            self.assertFalse(bootstrap.already_ready())

    def test_L6_repeated_bootstrap_preserves_user_config(self):
        bootstrap = load("d6_bootstrap_config", "scripts/bootstrap_windows.py")
        with temp_home() as repo, mock.patch.object(bootstrap, "REPO", repo), \
             mock.patch.object(bootstrap, "CONFIG_PATH", repo / "user.json"), \
             mock.patch("runtime_detection.validate_abaqus_cmd", return_value="custom.bat"):
            original = '{"schema_version":1,"ABAQUS_CMD":"custom.bat"}\n'
            (repo / "user.json").write_text(original)
            bootstrap.write_config(str(repo / ".venv" / "Scripts" / "python.exe"), "custom.bat")
            self.assertEqual((repo / "user.json").read_text(), original)

    def test_L8_single_config_is_move_safe(self):
        bootstrap = load("d6_bootstrap_move", "scripts/bootstrap_windows.py")
        with temp_home() as repo, mock.patch.object(bootstrap, "REPO", repo), \
             mock.patch.object(bootstrap, "CONFIG_PATH", repo / "user.json"), \
             mock.patch.object(bootstrap.runtime_detection, "validate_abaqus_cmd", return_value="fake.bat"):
            bootstrap.write_config(str(repo / ".venv" / "Scripts" / "python.exe"), "fake.bat")
            cfg = json.loads((repo / "user.json").read_text())
            self.assertEqual(cfg, {"schema_version": 1, "ABAQUS_CMD": "fake.bat"})
            self.assertFalse((repo / ".abaqus-agent.local").exists())
