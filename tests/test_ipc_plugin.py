import json
import os
import threading
import time
import types
import unittest
from pathlib import Path
from unittest import mock

from tests.support import load, temp_home


def load_server(name, home):
    mcp = types.ModuleType("mcp")
    server = types.ModuleType("mcp.server")
    fastmcp = types.ModuleType("mcp.server.fastmcp")
    class FakeFastMCP:
        def __init__(self, name):
            self.name = name
        def resource(self, _uri):
            return lambda func: func
        def tool(self):
            return lambda func: func
    fastmcp.FastMCP = FakeFastMCP
    return load(name, "mcp_server.py", home, {"mcp": mcp, "mcp.server": server,
                                                "mcp.server.fastmcp": fastmcp})


class IPC(unittest.TestCase):
    def test_L3_filenames_use_generated_command_id(self):
        with temp_home() as home:
            client = load("d6_client_ok", "client.py", home)
            def worker():
                while not list((home / "commands").glob("*.json")):
                    time.sleep(.001)
                cmd = next((home / "commands").glob("*.json"))
                data = json.loads(cmd.read_text())
                self.assertEqual(cmd.name, "cmd_" + data["id"] + ".json")
                (home / "results" / (data["id"] + ".json")).write_text(json.dumps({"success": True}))
            thread = threading.Thread(target=worker)
            thread.start()
            result = client.send("ping", timeout=1)
            thread.join(timeout=1)
            self.assertTrue(result["success"])
            self.assertEqual(list((home / "results").glob("*.json")), [])

    @unittest.expectedFailure
    def test_L3_command_id_uses_full_uuid4_hex(self):
        with temp_home() as home:
            client = load("d61_client_full_id", "client.py", home)
            generated = "0123456789abcdef0123456789abcdef"
            seen = []
            def respond(_):
                command = next((home / "commands").glob("cmd_*.json"))
                data = json.loads(command.read_text())
                seen.append((command.name, data["id"]))
                (home / "results" / (data["id"] + ".json")).write_text('{"success": true}')
            with mock.patch.object(client.uuid, "uuid4", return_value=types.SimpleNamespace(hex=generated)), \
                 mock.patch.object(client.time, "sleep", side_effect=respond):
                self.assertTrue(client.send("ping", timeout=1)["success"])
            self.assertEqual(seen, [("cmd_" + generated + ".json", generated)])

    def test_L3_server_filenames_use_generated_command_id(self):
        with temp_home() as home:
            server = load_server("d61_server_names", home)
            seen = []
            def respond(_):
                command = next((home / "commands").glob("cmd_*.json"))
                data = json.loads(command.read_text())
                seen.append((command.name, data["id"]))
                (home / "results" / (data["id"] + ".json")).write_text('{"success": true}')
            with mock.patch.object(server.time, "sleep", side_effect=respond):
                self.assertTrue(server._send_command("ping", timeout=1)["success"])
            self.assertEqual(seen[0][0], "cmd_" + seen[0][1] + ".json")

    @unittest.expectedFailure
    def test_L3_server_command_id_uses_full_uuid4_hex(self):
        with temp_home() as home:
            server = load_server("d61_server_full_id", home)
            generated = "fedcba9876543210fedcba9876543210"
            seen = []
            def respond(_):
                command = next((home / "commands").glob("cmd_*.json"))
                data = json.loads(command.read_text())
                seen.append((command.name, data["id"]))
                (home / "results" / (data["id"] + ".json")).write_text('{"success": true}')
            with mock.patch.object(server.uuid, "uuid4", return_value=types.SimpleNamespace(hex=generated)), \
                 mock.patch.object(server.time, "sleep", side_effect=respond):
                self.assertTrue(server._send_command("ping", timeout=1)["success"])
            self.assertEqual(seen, [("cmd_" + generated + ".json", generated)])

    def test_L3_queued_timeout_reports_no_success(self):
        with temp_home() as home:
            client = load("d6_client_timeout", "client.py", home)
            result = client.send("ping", timeout=0)
            self.assertFalse(result["success"])

    @unittest.expectedFailure
    def test_L3_claimed_timeout_reports_unknown_may_continue(self):
        with temp_home() as home:
            client = load("d6_client_inflight", "client.py", home)
            seen = threading.Event()
            resume = threading.Event()
            def worker():
                while not list((home / "commands").glob("*.json")):
                    time.sleep(.001)
                cmd = next((home / "commands").glob("*.json"))
                data = json.loads(cmd.read_text())
                cmd.unlink()
                seen.set()
                resume.wait(1)
                (home / "results" / (data["id"] + ".json")).write_text('{"success": true}')
            thread = threading.Thread(target=worker)
            thread.start()
            outcome = []
            caller = threading.Thread(target=lambda: outcome.append(client.send("submit_job", timeout=.05)))
            caller.start()
            self.assertTrue(seen.wait(1))
            caller.join(1)
            resume.set()
            thread.join(1)
            self.assertEqual(len(outcome), 1)
            self.assertFalse(outcome[0]["success"])
            message = json.dumps(outcome[0], ensure_ascii=False).lower()
            self.assertRegex(message, r"unknown|may continue|still executing")

    @unittest.expectedFailure
    def test_L3_long_A_does_not_lose_queued_B_C(self):
        with temp_home() as home:
            plugin = load("d6_plugin_queue", "abaqus_mcp_plugin.py", home)
            plugin.ensure_dirs()
            plugin._mcp_running = True
            plugin._mcp_last_status_time = time.time()
            plugin._mcp_start_time = time.time()
            for name in "ABC":
                path = home / "commands" / ("cmd_" + name + ".json")
                path.write_text(json.dumps({"id": name, "type": "ping"}))
            entered = threading.Event()
            resume = threading.Event()
            original = plugin.process_command
            def process(command):
                if command["id"] == "A":
                    entered.set()
                    resume.wait(1)
                return original(command)
            plugin.process_command = process
            worker = threading.Thread(target=plugin.poll_once)
            worker.start()
            self.assertTrue(entered.wait(1))
            # A is still executing. B/C have waited past the old 120 s age.
            for name in "BC":
                os.utime(home / "commands" / ("cmd_" + name + ".json"), (0, 0))
            resume.set()
            worker.join(1)
            with mock.patch.object(plugin.time, "time", return_value=121.0):
                plugin._cleanup_stale_commands()
            self.assertTrue(plugin.poll_once())
            self.assertTrue(plugin.poll_once())


class Plugin(unittest.TestCase):
    def test_L4_load_with_minimal_stubs(self):
        with temp_home() as home:
            stubs = {"abaqus": types.SimpleNamespace(mdb=object(), session=object()),
                     "abaqusConstants": types.SimpleNamespace(PNG="png", SVG="svg", TIFF="tif"),
                     "odbAccess": types.SimpleNamespace(openOdb=lambda **_: None)}
            plugin = load("d6_plugin_stubs", "abaqus_mcp_plugin.py", home, stubs)
            self.assertTrue(plugin.ABAQUS_AVAILABLE)
            self.assertEqual(plugin.process_command({"id": "p", "type": "ping"})["data"]["response"], "pong")


    @unittest.expectedFailure
    def test_L4_command_is_published_atomically(self):
        with temp_home() as home:
            client = load("d6_client_atomic", "client.py", home)
            with mock.patch.object(client.json, "dump", side_effect=RuntimeError("mid-write")):
                with self.assertRaises(RuntimeError):
                    client.send("ping")
            self.assertEqual(list((home / "commands").glob("cmd_*.json")), [])

    @unittest.expectedFailure
    def test_L4_result_is_published_atomically(self):
        with temp_home() as home:
            plugin = load("d6_plugin_atomic", "abaqus_mcp_plugin.py", home)
            plugin.ensure_dirs()
            path = home / "results" / "x.json"
            with mock.patch.object(plugin.json, "dump", side_effect=RuntimeError("mid-write")):
                with self.assertRaises(RuntimeError):
                    plugin._write_json(str(path), {"success": True})
            self.assertFalse(path.exists())

    @unittest.expectedFailure
    def test_L4_second_consumer_cannot_process_same_command(self):
        with temp_home() as home:
            p1 = load("d6_plugin_one", "abaqus_mcp_plugin.py", home)
            p2 = load("d6_plugin_two", "abaqus_mcp_plugin.py", home)
            p1.ensure_dirs()
            for p in (p1, p2):
                p._mcp_running = True
                p._mcp_last_status_time = time.time()
            (home / "commands" / "cmd_x.json").write_text('{"id":"x","type":"ping"}')
            barrier = threading.Barrier(2)
            seen = []
            def load_both(path):
                barrier.wait(1)
                return {"id": "x", "type": "ping"}
            for p in (p1, p2):
                p._load_command_file = load_both
                p.process_command = lambda c: seen.append(c["id"]) or {"success": True}
            threads = [threading.Thread(target=p.poll_once) for p in (p1, p2)]
            for t in threads: t.start()
            for t in threads: t.join(1)
            self.assertEqual(seen, ["x"])

    @unittest.expectedFailure
    def test_L4_stop_flag_is_session_owned(self):
        with temp_home() as home:
            plugin = load("d6_plugin_stop", "abaqus_mcp_plugin.py", home)
            result = plugin.process_command({"id": "x", "type": "stop"})
            self.assertTrue(result["success"])
            self.assertIn("session_id", (home / "stop.flag").read_text())

    @unittest.expectedFailure
    def test_L4_screenshot_names_do_not_collide(self):
        with temp_home() as home:
            files = []
            def capture(**kwargs):
                files.append(kwargs["fileName"])
                Path(kwargs["fileName"] + ".png").write_bytes(b"png")
            session = types.SimpleNamespace(currentViewportName="V", viewports={"V": object()}, printToFile=capture)
            plugin = load("d6_plugin_shot", "abaqus_mcp_plugin.py", home,
                          {"abaqus": types.SimpleNamespace(session=session),
                           "abaqusConstants": types.SimpleNamespace(PNG="png", SVG="svg", TIFF="tif")})
            plugin.ensure_dirs()
            stubs = {"abaqus": types.SimpleNamespace(session=session),
                     "abaqusConstants": types.SimpleNamespace(PNG="png", SVG="svg", TIFF="tif")}
            with mock.patch.dict("sys.modules", stubs), mock.patch.object(plugin.time, "time", return_value=10):
                plugin.get_viewport_image()
                plugin.get_viewport_image()
            self.assertEqual(len(set(files)), 2)

    @unittest.expectedFailure
    def test_L4_unsupported_image_format_fails(self):
        with temp_home() as home:
            session = types.SimpleNamespace(currentViewportName="V", viewports={"V": object()},
                                            printToFile=lambda **kw: Path(kw["fileName"] + ".png").write_bytes(b"png"))
            plugin = load("d6_plugin_format", "abaqus_mcp_plugin.py", home,
                          {"abaqus": types.SimpleNamespace(session=session),
                           "abaqusConstants": types.SimpleNamespace(PNG="png", SVG="svg", TIFF="tif")})
            plugin.ensure_dirs()
            stubs = {"abaqus": types.SimpleNamespace(session=session),
                     "abaqusConstants": types.SimpleNamespace(PNG="png", SVG="svg", TIFF="tif")}
            with mock.patch.dict("sys.modules", stubs):
                self.assertFalse(plugin.get_viewport_image(fmt="JPEG")["success"])
