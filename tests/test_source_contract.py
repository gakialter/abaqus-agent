import re
import unittest
from pathlib import PurePosixPath

from tests.support import ROOT, archive_files, load, temp_home


class SourceContract(unittest.TestCase):
    def test_L1_archive_excludes_runtime(self):
        files = archive_files()
        self.assertFalse(any(p.startswith((".venv/", "mcp_home/", "work/")) for p in files))
        self.assertIn("validation/result.json", files)  # historical evidence is source, not live status

    def test_L1_required_source_and_skill_links(self):
        files = archive_files()
        for path in ("SKILL.md", "client.py", "mcp_server.py", "abaqus_mcp_plugin.py",
                     "abaqus_start_mcp.py", "scripts/bootstrap_windows.py"):
            self.assertIn(path, files)
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        for target in re.findall(r"\]\((references/[^)#]+)\)", skill):
            self.assertIn(str(PurePosixPath(target)), files)

    def test_L1_clean_archive_bootstrap_needs_no_runtime_directory(self):
        with temp_home() as home:
            bootstrap = load("d6_bootstrap_clean", "scripts/bootstrap_windows.py")
            from unittest import mock
            with mock.patch.object(bootstrap, "REPO", home):
                for name in bootstrap.REQUIRED_FILES:
                    target = home / name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text("fixture", encoding="utf-8")
                (home / "references").mkdir()
                self.assertEqual(bootstrap.verify_repo_files(), [])

    def test_L1_only_root_runtime_is_canonical(self):
        files = archive_files()
        duplicates = {"scripts/client.py", "scripts/mcp_server.py", "scripts/abaqus_mcp_plugin.py",
                      "scripts/abaqus_start_mcp.py", "scripts/setup_abaqus_agent.py"}
        self.assertFalse(files & duplicates, "legacy runtime duplicates still shipped")

    def test_L1_portable_guidance_has_no_personal_path(self):
        paths = [ROOT / "SKILL.md", ROOT / "README.md", ROOT / "QUICKSTART_FOR_STUDENTS.md",
                 ROOT / "bootstrap_for_doubao_work.md"]
        self.assertFalse([str(p) for p in paths if re.search(r"C:[\\/]Users[\\/]27296", p.read_text(encoding="utf-8"))])

    def test_L1_runbook_personal_paths_are_labelled_local_history(self):
        runbook = (ROOT / "RUNBOOK.md").read_text(encoding="utf-8")
        self.assertRegex(runbook, r"C:[\\/]Users[\\/]27296")
        self.assertRegex(runbook[:600], r"(?i)historical|local reproduction|non.portable|历史|本机复现|非通用")

    def test_L1_all_public_entry_docs_converge_on_root_installer(self):
        names = ("README.md", "QUICKSTART_FOR_STUDENTS.md", "bootstrap_for_doubao_work.md", "SKILL.md")
        bad = []
        for name in names:
            doc = (ROOT / name).read_text(encoding="utf-8")
            if "install.bat" not in doc or "python scripts/setup_abaqus_agent.py" in doc or "--workspace D:" in doc:
                bad.append(name)
        self.assertEqual(bad, [])

    def test_L9_package_footprint(self):
        files = archive_files()
        package = {p for p in files if p == "SKILL.md" or p.startswith("references/")}
        self.assertIn("SKILL.md", package)
        self.assertFalse(any(p.startswith((".venv/", "mcp_home/", "work/", "validation/")) for p in package))
        self.assertFalse(any(p.split("/")[-1] in {"client.py", "mcp_server.py"} for p in package))

    def test_L9_all_package_links_are_internal_and_resolve(self):
        package_root = ROOT
        for source in [ROOT / "SKILL.md", *(ROOT / "references").rglob("*.md")]:
            text = source.read_text(encoding="utf-8")
            self.assertNotRegex(text, r"C:[\\/]Users[\\/]27296")
            for href in re.findall(r"\]\(([^)#]+)(?:#[^)]*)?\)", text):
                if "://" in href:
                    continue
                target = (source.parent / href).resolve()
                self.assertTrue(target.is_relative_to(package_root), (source, href))
                self.assertTrue(target.is_file(), (source, href))


class KnowledgeContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.current = {p.name: p.read_text(encoding="utf-8") for p in [ROOT / "SKILL.md", *list((ROOT / "references").rglob("*.md"))]}
        cls.guidance = "\n".join(cls.current.values())

    def test_L2_canonical_gates_G1_to_G8(self):
        workflow = (ROOT / "references/execution/workflow.md").read_text(encoding="utf-8")
        for i in range(1, 9):
            self.assertRegex(workflow, rf"\bG{i}\b")
        self.assertNotRegex(self.guidance, r"\bGATE\s+(?:[A-F]|3a|3b|C\+E)\b")

    def test_L2_G1_facts_unknowns_ambiguities_inferences(self):
        workflow = self.current["workflow.md"]
        for word in ("FACTS", "UNKNOWNS", "AMBIGUITIES", "MODEL INFERENCES"):
            self.assertIn(word, workflow)

    def test_L2_G8_solver_completed_is_not_task_complete(self):
        workflow = self.current["workflow.md"]
        self.assertRegex(workflow, r"\bG8\b")
        self.assertRegex(workflow, r"(?is)G8.{0,500}COMPLETED.{0,500}(?:not|never|不等于|不能)")

    def test_L2_backfit_evidence_is_historical(self):
        lessons = self.current["lessons-learned.md"]
        self.assertIn("27683 N", lessons)
        self.assertIn("reverse-fit", lessons)
        self.assertNotIn("27683 N", self.current["workflow.md"])

    def test_L2_RF_CPRESS_distinct(self):
        self.assertRegex(self.current["verification.md"], r"Press force.*not.*contact pressure")

    def test_L2_failed_job_partial_odb_is_diagnostic(self):
        self.assertNotIn("only trustworthy if COMPLETED", self.current["error-diagnosis.md"])

    def test_L2_no_arbitrary_first_contact_key(self):
        self.assertNotRegex(self.guidance, r"\[k for k in .*startswith\(['\"](?:CPRESS|COPEN).*\]\[0\]")

    def test_L2_units_are_consistent_choices(self):
        self.assertNotIn("N-mm-MPa only", self.guidance)

    def test_L2_sanity_check_needs_no_percent_error(self):
        self.assertNotIn("Always state: what you compared, the FE number, the expected number, and the % difference", self.guidance)

    def test_L2_README_no_tight_RF_analytical_claim(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertNotRegex(readme, r"(?is)(?:RF\s*[=~]?\s*(?:27557\s*N|27[.,]5[56]\s*kN)).{0,100}(?:0[.,]5\s*%|tight|analytical)")

    def test_L2_README_PEEQ_010_is_local_max(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        for line in readme.splitlines():
            if re.search(r"PEEQ\s*[=~]?\s*0[.,]10\b", line, re.I):
                self.assertRegex(line, r"(?i)local\s+max(?:imum)?|local\s+peak|局部最大|局部峰值")

    def test_L2_README_27683_only_in_historical_backfit_context(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        for paragraph in re.split(r"\n\s*\n", readme):
            if "27683 N" in paragraph:
                self.assertRegex(paragraph, r"(?i)historical|back.fit|reverse.fit|历史|反推")
