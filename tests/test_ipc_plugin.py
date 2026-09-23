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
    def test_queued_timeout_cancels_before_claim_for_both_senders(self):
        for label in ('client', 'server'):
            with self.subTest(sender=label), temp_home() as home:
                sender = load('cancel_' + label, 'client.py', home) if label == 'client' else load_server('cancel_server', home)
                result = (sender.send if label == 'client' else sender._send_command)('ping', timeout=0)
                self.assertFalse(result['success'])
                self.assertEqual(result['execution_state'], 'CANCELLED_BEFORE_CLAIM')
                self.assertEqual(len(result['command_id']), 32)
                self.assertEqual(list((home / 'commands').glob('cmd_*.json')), [])
                self.assertEqual(list((home / 'claims').glob('cmd_*.json')), [])

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

    def test_L3_long_A_does_not_lose_queued_B_C(self):
        with temp_home() as home:
            plugin = load("d6_plugin_queue", "abaqus_mcp_plugin.py", home)
            plugin.ensure_dirs()
            plugin._mcp_running = True
            plugin._mcp_last_status_time = time.time()
            plugin._mcp_start_time = time.time()
            ids = {name: name.lower() * 32 for name in "ABC"}
            for name, cmd_id in ids.items():
                path = home / "commands" / ("cmd_" + cmd_id + ".json")
                path.write_text(json.dumps({"id": cmd_id, "type": "ping", "timestamp": time.time()}))
            entered = threading.Event()
            resume = threading.Event()
            original = plugin.process_command
            def process(command):
                if command["id"] == ids["A"]:
                    entered.set()
                    resume.wait(1)
                return original(command)
            plugin.process_command = process
            worker = threading.Thread(target=plugin.poll_once)
            worker.start()
            self.assertTrue(entered.wait(1))
            # A is still executing. B/C have waited past the old 120 s age.
            for name in "BC":
                os.utime(home / "commands" / ("cmd_" + ids[name] + ".json"), (0, 0))
            resume.set()
            worker.join(1)
            self.assertFalse(hasattr(plugin, "_cleanup_stale_commands"))
            self.assertTrue(plugin.poll_once())
            self.assertTrue(plugin.poll_once())
            self.assertEqual(len(list((home / "results").glob("*.json"))), 3)


class Plugin(unittest.TestCase):
    def test_poison_command_cannot_starve_valid_command(self):
        with temp_home() as home:
            plugin = load('plugin_poison', 'abaqus_mcp_plugin.py', home)
            plugin.ensure_dirs()
            plugin._mcp_running = True
            plugin._mcp_last_status_time = time.time()
            bad_id, good_id = '0' * 32, '1' * 32
            bad = home / 'commands' / ('cmd_' + bad_id + '.json')
            good = home / 'commands' / ('cmd_' + good_id + '.json')
            for bad_content in ('{', json.dumps({'id': '../unsafe', 'type': 'ping', 'timestamp': time.time()}),
                                json.dumps({'id': '2' * 32, 'type': 'ping', 'timestamp': time.time()}),
                                json.dumps({'id': bad_id, 'timestamp': time.time()})):
                bad.write_text(bad_content, encoding='utf-8')
                good.write_text(json.dumps({'id': good_id, 'type': 'ping', 'timestamp': time.time()}), encoding='utf-8')
                self.assertTrue(plugin.poll_once())
                error = json.loads((home / 'results' / (bad_id + '.json')).read_text())
                self.assertEqual(error['id'], bad_id)
                self.assertFalse(error['success'])
                self.assertFalse(bad.exists())
                self.assertTrue(plugin.poll_once())
                self.assertTrue(json.loads((home / 'results' / (good_id + '.json')).read_text())['success'])
                (home / 'results' / (bad_id + '.json')).unlink()
                (home / 'results' / (good_id + '.json')).unlink()

    def test_L4_load_with_minimal_stubs(self):
        with temp_home() as home:
            stubs = {"abaqus": types.SimpleNamespace(mdb=object(), session=object()),
                     "abaqusConstants": types.SimpleNamespace(PNG="png", SVG="svg", TIFF="tif"),
                     "odbAccess": types.SimpleNamespace(openOdb=lambda **_: None)}
            plugin = load("d6_plugin_stubs", "abaqus_mcp_plugin.py", home, stubs)
            self.assertTrue(plugin.ABAQUS_AVAILABLE)
            self.assertEqual(plugin.process_command({"id": "p", "type": "ping"})["data"]["response"], "pong")


    def test_L4_command_is_published_atomically(self):
        with temp_home() as home:
            client = load("d6_client_atomic", "client.py", home)
            with mock.patch.object(client.json, "dump", side_effect=RuntimeError("mid-write")):
                with self.assertRaises(RuntimeError):
                    client.send("ping")
            self.assertEqual(list((home / "commands").glob("cmd_*.json")), [])

    def test_L4_result_is_published_atomically(self):
        with temp_home() as home:
            plugin = load("d6_plugin_atomic", "abaqus_mcp_plugin.py", home)
            plugin.ensure_dirs()
            path = home / "results" / "x.json"
            with mock.patch.object(plugin.json, "dump", side_effect=RuntimeError("mid-write")):
                with self.assertRaises(RuntimeError):
                    plugin._write_json(str(path), {"success": True})
            self.assertFalse(path.exists())

    def test_L4_complete_command_visible_only_after_replace_for_both_senders(self):
        with temp_home() as home:
            for label, sender in (("client", load("d72_client_visibility", "client.py", home)),
                                  ("server", load_server("d72_server_visibility", home))):
                final = home / "commands" / ("cmd_" + "a" * 32 + ".json")
                final.parent.mkdir(parents=True, exist_ok=True)
                if final.exists():
                    final.unlink()
                original_dump = json.dump
                observed = []
                def write_and_check(data, stream):
                    stream.write('{"id":')
                    observed.append((final.exists(), Path(stream.name).name,
                                     list(final.parent.glob("cmd_*.json"))))
                    original_dump(data["id"], stream)
                    stream.write('}')
                with self.subTest(sender=label), mock.patch.object(sender.json, "dump", side_effect=write_and_check):
                    sender._publish_command(final, {"id": "a" * 32})
                self.assertEqual(observed[0][0], False)
                self.assertTrue(observed[0][1].startswith(".tmp-command-"))
                self.assertEqual(observed[0][2], [])
                self.assertEqual(json.loads(final.read_text()), {"id": "a" * 32})
                self.assertEqual(list(final.parent.glob(".tmp-command-*")), [])

    def test_L4_failed_partial_writes_leave_no_final_or_temp(self):
        with temp_home() as home:
            client = load("d72_client_partial", "client.py", home)
            server = load_server("d72_server_partial", home)
            plugin = load("d72_plugin_partial", "abaqus_mcp_plugin.py", home)
            plugin.ensure_dirs()
            def partial(_data, stream, **_kwargs):
                stream.write('{"partial":')
                raise OSError("mid-write")
            for label, sender in (("client", client), ("server", server)):
                with self.subTest(sender=label), mock.patch.object(sender.json, "dump", side_effect=partial):
                    with self.assertRaisesRegex(OSError, "mid-write"):
                        sender._publish_command(home / "commands" / ("cmd_" + "a" * 32 + ".json"),
                                                {"id": "a" * 32})
                self.assertEqual(list((home / "commands").iterdir()), [])
            result = home / "results" / ("a" * 32 + ".json")
            with mock.patch.object(plugin.json, "dump", side_effect=partial):
                with self.assertRaisesRegex(OSError, "mid-write"):
                    plugin._write_json(str(result), {"success": True})
            self.assertEqual(list((home / "results").iterdir()), [])

    def test_L4_result_visible_only_after_complete_write(self):
        with temp_home() as home:
            plugin = load("d72_plugin_visibility", "abaqus_mcp_plugin.py", home)
            plugin.ensure_dirs()
            final = home / "results" / ("a" * 32 + ".json")
            observed = []
            def write_and_check(data, stream, **kwargs):
                stream.write('{"success":')
                observed.append((final.exists(), Path(stream.name).name))
                stream.write('true}')
            with mock.patch.object(plugin.json, "dump", side_effect=write_and_check):
                plugin._write_json(str(final), {"success": True})
            self.assertEqual(observed[0][0], False)
            self.assertTrue(observed[0][1].startswith(".tmp-ipc-"))
            self.assertEqual(json.loads(final.read_text()), {"success": True})
            self.assertEqual(list(final.parent.glob(".tmp-ipc-*")), [])

    def test_L4_concurrent_writers_use_distinct_temporary_files(self):
        with temp_home() as home:
            client = load("d72_client_concurrent", "client.py", home)
            client.COMMANDS_DIR.mkdir()
            barrier = threading.Barrier(2)
            names = []
            errors = []
            def paused_dump(data, stream):
                names.append(stream.name)
                barrier.wait(1)
                stream.write('{"ready":true}')
            def writer(suffix):
                try:
                    client._publish_command(home / "commands" / ("cmd_" + suffix * 32 + ".json"),
                                            {"ready": True})
                except Exception as exc:
                    errors.append(exc)
            with mock.patch.object(client.json, "dump", side_effect=paused_dump):
                threads = [threading.Thread(target=writer, args=(suffix,)) for suffix in "ab"]
                for thread in threads:
                    thread.start()
                for thread in threads:
                    thread.join(2)
            self.assertEqual(errors, [])
            self.assertEqual(len(set(names)), 2)
            self.assertTrue(all(Path(name).parent == home / "commands" for name in names))
            self.assertEqual(len(list((home / "commands").glob("cmd_*.json"))), 2)

    def test_L4_invalid_ids_and_temp_files_never_form_protocol_paths(self):
        with temp_home() as home:
            client = load("d72_client_bad_id", "client.py", home)
            server = load_server("d72_server_bad_id", home)
            plugin = load("d72_plugin_bad_id", "abaqus_mcp_plugin.py", home)
            plugin.ensure_dirs()
            for bad in ("a" * 8, "A" * 32, "../" + "a" * 32, "a" * 31 + "g"):
                for label, sender in (("client", client), ("server", server)):
                    with self.subTest(sender=label, bad=bad), \
                         mock.patch.object(sender.uuid, "uuid4", return_value=types.SimpleNamespace(hex=bad)):
                        with self.assertRaisesRegex(ValueError, "Invalid command ID"):
                            (sender.send if label == "client" else sender._send_command)("ping", timeout=0)
                self.assertFalse(plugin.execute_script("print(1)", bad)["success"])
            valid = "b" * 32
            (home / "commands" / (".tmp-command-" + valid)).write_text(
                json.dumps({"id": valid, "type": "ping"}))
            (home / "commands" / "cmd_bad.json").write_text(
                json.dumps({"id": "bad", "type": "ping"}))
            (home / "commands" / ("cmd_" + valid + ".json")).write_text(
                json.dumps({"id": "c" * 32, "type": "ping"}))
            plugin._mcp_running = True
            plugin._mcp_last_status_time = time.time()
            self.assertTrue(plugin.poll_once())
            error = json.loads((home / "results" / (valid + ".json")).read_text())
            self.assertFalse(error["success"])
            self.assertEqual(error["id"], valid)
            self.assertFalse((home / "commands" / ("cmd_" + valid + ".json")).exists())
            self.assertFalse(plugin.poll_once())
            self.assertEqual(len(list((home / "results").iterdir())), 1)

    def test_L4_second_consumer_cannot_process_same_command(self):
        with temp_home() as home:
            p1 = load("d6_plugin_one", "abaqus_mcp_plugin.py", home)
            p2 = load("d6_plugin_two", "abaqus_mcp_plugin.py", home)
            self.assertTrue(p1._acquire_owner())
            self.assertFalse(p2._acquire_owner())
            p1._release_owner()
            self.assertTrue(p2._acquire_owner())
            p2._release_owner()

    def test_L4_stop_flag_is_session_owned(self):
        with temp_home() as home:
            plugin = load("d6_plugin_stop", "abaqus_mcp_plugin.py", home)
            self.assertTrue(plugin._acquire_owner())
            rejected = plugin.process_command({"id": "y", "type": "stop", "session_id": "f" * 32})
            self.assertFalse(rejected['success'])
            self.assertFalse((home / 'stop.flag').exists())
            result = plugin.process_command({"id": "x", "type": "stop", "session_id": plugin._session_id})
            self.assertTrue(result["success"])
            self.assertEqual(json.loads((home / "stop.flag").read_text())["session_id"], plugin._session_id)
            plugin._release_owner()

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
