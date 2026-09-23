"""D7.1 installation contracts; all writes are confined to temporary repos."""
import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

from tests.support import ROOT, archive_to, load, temp_home


class ConfigAndDetection(unittest.TestCase):
    def setUp(self):
        self.config = load("d71_local_config", "scripts/local_config.py")
        self.detection = load("d71_detection", "scripts/runtime_detection.py")

    def test_config_derives_paths_after_repo_move(self):
        with temp_home() as base:
            first, moved = base / "first", base / "moved 中文 & !"
            first.mkdir()
            with mock.patch("runtime_detection.validate_abaqus_cmd", return_value="abaqus"):
                self.config.write_config(first / ".abaqus-agent.json", "abaqus")
            first.rename(moved)
            data = self.config.read_config(moved / ".abaqus-agent.json")
            self.assertEqual(data, {"schema_version": 1, "ABAQUS_CMD": "abaqus"})
            self.assertEqual(self.config.derived_paths(moved)["mcp_home"], moved / "mcp_home")

    def test_legacy_inputs_are_parsed_never_executed_or_deleted(self):
        with temp_home() as repo:
            launcher = repo / "Abaqus & ! 中文.bat"
            launcher.write_text("@echo off\n", encoding="utf-8")
            legacy_json = repo / "old-global.json"
            legacy_bat = repo / ".abaqus-agent.local"
            legacy_json.write_text(json.dumps({"workspace": str(repo), "abaqus_cmd": str(launcher)}))
            legacy_bat.write_text('@rem old\nset "ABAQUS_CMD=%s"\n' % launcher, encoding="utf-8")
            before = (legacy_json.read_bytes(), legacy_bat.read_bytes())
            data, source = self.config.load_or_migrate(repo, legacy_home=legacy_json, write=True)
            self.assertEqual(data["ABAQUS_CMD"], str(launcher))
            self.assertIn(str(legacy_bat), source)
            self.assertEqual((legacy_json.read_bytes(), legacy_bat.read_bytes()), before)
            self.assertEqual(self.config.read_config(repo / ".abaqus-agent.json"), data)

    def test_legacy_conflict_and_nonliteral_bat_stop_without_new_config(self):
        with temp_home() as repo:
            one, two = repo / "one.bat", repo / "two.exe"
            one.write_bytes(b"x")
            two.write_bytes(b"x")
            legacy_json = repo / "old-global.json"
            legacy_bat = repo / ".abaqus-agent.local"
            legacy_json.write_text(json.dumps({"workspace": str(repo), "abaqus_cmd": str(one)}))
            legacy_bat.write_text('set "ABAQUS_CMD=%s"\n' % two)
            with self.assertRaisesRegex(ValueError, "disagree"):
                self.config.load_or_migrate(repo, legacy_home=legacy_json, write=True)
            self.assertFalse((repo / ".abaqus-agent.json").exists())
            legacy_bat.write_text('echo unsafe\nset "ABAQUS_CMD=%s"\n' % one)
            with self.assertRaisesRegex(ValueError, "not executed"):
                self.config.load_or_migrate(repo, legacy_home=legacy_json, write=True)
            self.assertFalse((repo / ".abaqus-agent.json").exists())

    def test_command_accepts_special_full_paths_rejects_arguments(self):
        with temp_home() as repo:
            for suffix in (".bat", ".exe"):
                path = repo / ("Abaqus 中文 (& !)" + suffix)
                path.write_bytes(b"x")
                self.assertEqual(self.detection.validate_abaqus_cmd(str(path)), str(path))
                with self.assertRaises(ValueError):
                    self.detection.validate_abaqus_cmd(str(path) + " --unexpected")

    def test_python_311_selected_only_after_version_probe(self):
        def run(args, **_):
            version = "3.11\n" if args[:2] == ["py", "-3.11"] else "3.14\n"
            return subprocess.CompletedProcess(args, 0, version, "")
        with mock.patch.object(self.detection, "which", side_effect=lambda name: name), \
             mock.patch.object(self.detection.subprocess, "run", side_effect=run):
            self.assertEqual(self.detection.detect_python(), ["py", "-3.11"])


class VenvRepair(unittest.TestCase):
    def setUp(self):
        self.bootstrap = load("d71_bootstrap_venv", "scripts/bootstrap_windows.py")

    def test_failed_replacement_keeps_old_venv(self):
        with temp_home() as repo, mock.patch.object(self.bootstrap, "REPO", repo):
            old = repo / ".venv" / "marker.txt"
            old.parent.mkdir()
            old.write_text("user old venv")
            with mock.patch.object(self.bootstrap, "venv_is_ready", return_value=False), \
                 mock.patch.object(self.bootstrap.subprocess, "run", side_effect=subprocess.CalledProcessError(1, "pip")):
                with self.assertRaises(subprocess.CalledProcessError):
                    self.bootstrap.ensure_venv(["py", "-3.11"])
            self.assertEqual(old.read_text(), "user old venv")
            self.assertEqual(list(repo.glob(".venv.previous-*")), [])

    def test_successful_repair_switches_after_replacement_validation(self):
        with temp_home() as repo, mock.patch.object(self.bootstrap, "REPO", repo):
            old = repo / ".venv" / "marker.txt"
            old.parent.mkdir()
            old.write_text("old")
            calls = []
            def ready(path):
                calls.append(path.name)
                return path.name != ".venv" or (path / "marker.txt").read_text() == "new"
            def fake_run(args, **_):
                if "venv" in args:
                    replacement = Path(args[-1])
                    (replacement / "Scripts").mkdir(parents=True)
                    (replacement / "marker.txt").write_text("new")
                return subprocess.CompletedProcess(args, 0, "", "")
            with mock.patch.object(self.bootstrap, "venv_is_ready", side_effect=ready), \
                 mock.patch.object(self.bootstrap.subprocess, "run", side_effect=fake_run):
                result = self.bootstrap.ensure_venv(["py", "-3.11"])
            self.assertEqual(result, repo / ".venv" / "Scripts" / "python.exe")
            self.assertEqual((repo / ".venv" / "marker.txt").read_text(), "new")
            backups = list(repo.glob(".venv.previous-*"))
            self.assertEqual(len(backups), 1)
            self.assertEqual((backups[0] / "marker.txt").read_text(), "old")
            self.assertEqual(calls[0], ".venv")

    def test_blocked_windows_switch_preserves_old_environment(self):
        with temp_home() as repo, mock.patch.object(self.bootstrap, "REPO", repo):
            old = repo / ".venv" / "marker.txt"
            old.parent.mkdir()
            old.write_text("old")
            original_rename = Path.rename
            def blocked_rename(path, target):
                if path == repo / ".venv":
                    raise PermissionError("in use")
                return original_rename(path, target)
            def fake_run(args, **_):
                if "venv" in args:
                    (Path(args[-1]) / "Scripts").mkdir(parents=True)
                return subprocess.CompletedProcess(args, 0, "", "")
            with mock.patch.object(self.bootstrap, "venv_is_ready",
                                   side_effect=lambda path: path.name != ".venv"), \
                 mock.patch.object(self.bootstrap.subprocess, "run", side_effect=fake_run), \
                 mock.patch.object(Path, "rename", blocked_rename):
                with self.assertRaisesRegex(RuntimeError, "old environment kept"):
                    self.bootstrap.ensure_venv(["py", "-3.11"])
            self.assertEqual(old.read_text(), "old")
            self.assertEqual(list(repo.glob(".venv.previous-*")), [])

    def test_clean_archive_source_preflight_and_runtime_creation(self):
        with temp_home() as repo:
            archive_to(repo)
            for name in ("bootstrap_windows.py", "local_config.py", "runtime_detection.py"):
                (repo / "scripts" / name).write_bytes((ROOT / "scripts" / name).read_bytes())
            bootstrap = load("d71_archive_bootstrap", "scripts/bootstrap_windows.py")
            with mock.patch.object(bootstrap, "REPO", repo), \
                 mock.patch.object(bootstrap, "CONFIG_PATH", repo / ".abaqus-agent.json"), \
                 mock.patch.object(bootstrap, "LOCAL_ENV", repo / ".abaqus-agent.local"), \
                 mock.patch.object(bootstrap.runtime_detection, "detect_python", return_value=["py", "-3.11"]), \
                 mock.patch.object(bootstrap.runtime_detection, "detect_abaqus", return_value="abaqus"), \
                 mock.patch.object(bootstrap, "ensure_venv", return_value=repo / ".venv" / "Scripts" / "python.exe"), \
                 mock.patch("runtime_detection.validate_abaqus_cmd", return_value="abaqus"):
                self.assertEqual(bootstrap.verify_repo_files(), [])
                self.assertFalse((repo / "mcp_home").exists())
                self.assertFalse((repo / "work").exists())
                self.assertEqual(bootstrap.main([]), 0)
            self.assertTrue((repo / "mcp_home").is_dir())
            self.assertTrue((repo / "work").is_dir())
            self.assertEqual(json.loads((repo / ".abaqus-agent.json").read_text()),
                             {"schema_version": 1, "ABAQUS_CMD": "abaqus"})
