"""Behavioral regressions using throwaway Git repositories and synthetic data."""
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location("validation", Path(__file__).resolve().parents[1] / "scripts/validate.py")
v = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(v)


class Fixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        subprocess.run(["git", "init", "-q", str(self.root)], check=True, capture_output=True)

    def write(self, name, content, stage=True):
        target = self.root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
        if stage:
            subprocess.run(["git", "add", "--", name], cwd=self.root, check=True, capture_output=True)

    def copy_metadata(self):
        for name in v.inventory():
            src = v.ROOT / name
            if src.is_file():
                dest = self.root / name
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(src, dest)
        subprocess.run(["git", "add", "."], cwd=self.root, check=True, capture_output=True)

    def test_links_accept_real_markdown(self):
        self.write("README.md", '# Hello\n\n[Title](other.md "A title")\n\n[Reference][ref]\n\n[ref]: other.md#repeat-1\n\n[Self](#hello)\n\n```text\n[fake](absent.md)\n```\n\n`[fake](absent.md)`\n')
        self.write("other.md", "# Repeat\n\n# Repeat\n")
        v.markdown(self.root)

    def test_broken_same_page_cross_file_and_reference(self):
        self.write("other.md", "# Existing\n")
        for text in ["[bad](#missing)", "[bad](other.md#missing)", "[bad][x]\n\n[x]: absent.md"]:
            with self.subTest(text=text):
                self.write("README.md", text)
                with self.assertRaises(v.Invalid):
                    v.markdown(self.root)

    def test_encoded_paths_plus_and_heading_markup(self):
        self.write("README.md", "[Space](has%20space.md)\n[Plus](a+b.md)\n[Heading](other.md#use-code--emphasis)")
        self.write("has space.md", "# Space")
        self.write("a+b.md", "# Plus")
        self.write("other.md", "# Use `code` & *emphasis*")
        v.markdown(self.root)

    def test_duplicate_slug_collision(self):
        self.write("README.md", "[Target](other.md#repeat-2)")
        self.write("other.md", "# Repeat\n\n# Repeat-1\n\n# Repeat")
        v.markdown(self.root)

    def test_untracked_and_ignored_target_fail_but_staged_passes(self):
        self.write("README.md", "[New](new.md)")
        self.write("new.md", "# New", stage=False)
        with self.assertRaises(v.Invalid):
            v.markdown(self.root)
        subprocess.run(["git", "add", "new.md"], cwd=self.root, check=True, capture_output=True)
        v.markdown(self.root)
        self.write(".gitignore", "/archive/\n")
        self.write("archive/local.md", "Private fixture", stage=False)
        self.write("README.md", "[Local](archive/local.md)")
        with self.assertRaises(v.Invalid):
            v.markdown(self.root)

    def test_traversal_absolute_and_symlink_rejected(self):
        self.write("target.md", "# Target")
        (self.root / "link.md").symlink_to("target.md")
        subprocess.run(["git", "add", "link.md"], cwd=self.root, check=True, capture_output=True)
        for text in ["[x](../private.md)", "[x](/private.md)", "[x](link.md)"]:
            with self.subTest(text=text):
                self.write("README.md", text)
                with self.assertRaises(v.Invalid):
                    v.markdown(self.root)

    def test_inventory_failure_is_not_empty_success(self):
        failure = subprocess.CompletedProcess(["git"], 2, b"", b"sensitive diagnostic")
        with patch.object(v.subprocess, "run", return_value=failure):
            with self.assertRaisesRegex(v.Invalid, "Command failed") as caught:
                v.inventory(self.root)
            self.assertNotIn("sensitive", str(caught.exception))

    def test_missing_and_failing_scanner_fail_closed(self):
        with patch.object(v.subprocess, "run", side_effect=FileNotFoundError):
            with self.assertRaises(v.Invalid):
                v.secrets(self.root, set())
        with patch.object(v, "command", side_effect=[v.GITLEAKS, v.Invalid("scanner failed")]):
            with self.assertRaisesRegex(v.Invalid, "scanner failed"):
                v.secrets(self.root, set())

    def test_secret_scanner_inventories_reviews_and_policy(self):
        self.write("project/reviews/new.md", "Safe review")
        self.write("policy.json", "{}")
        seen = []
        def fake_command(args, root):
            if args[1] == "version":
                return v.GITLEAKS
            snapshot = Path(args[2])
            seen.extend(p.relative_to(snapshot).as_posix() for p in snapshot.rglob("*") if p.is_file())
            self.assertIn("--redact", args)
            return ""
        with patch.object(v, "command", side_effect=fake_command):
            v.secrets(self.root, {"project/reviews/new.md", "policy.json"})
        self.assertCountEqual(seen, ["project/reviews/new.md", "policy.json"])

    def test_hygiene_redacts_new_review_and_no_directory_exemption(self):
        self.write("scripts/publication-policy.json", json.dumps({"patterns": ["PRIVATE[_]FIXTURE"], "exceptions": []}))
        self.write("project/reviews/new.md", "PRIVATE_FIXTURE confidential example")
        with self.assertRaises(v.Invalid) as caught:
            v.hygiene(self.root)
        self.assertNotIn("confidential example", str(caught.exception))
        self.write("project/reviews/new.md", "Safe review")
        v.hygiene(self.root)
        self.write("project/reviews/another.md", "PRIVATE_FIXTURE different example")
        with self.assertRaises(v.Invalid):
            v.hygiene(self.root)

    def test_raw_html_navigation_rejected_but_formatting_allowed(self):
        for content in ['<a href="missing.md">bad</a>', '<img src="../private.png">',
                        '<div>\n<a href="missing.md">bad</a>\n</div>']:
            self.write("README.md", content)
            with self.assertRaisesRegex(v.Invalid, "raw HTML navigation"):
                v.markdown(self.root)
        self.write("README.md", "Hello<br>world\n\n`<a href=missing.md>`")
        v.markdown(self.root)

    def test_current_metadata_cannot_be_satisfied_by_decoy_mentions(self):
        self.copy_metadata()
        edition = (self.root / "VERSION").read_text().strip()
        for name in ["README.md", "CHARTER.md"]:
            path = self.root / name
            original = path.read_text()
            path.write_text(original.replace("Version " + edition, "Version 1999.01.01") + "\nVersion " + edition + "\n")
            with self.assertRaises(v.Invalid):
                v.metadata(self.root)
            path.write_text(original)
        path = self.root / "CHANGELOG.md"
        path.write_text("## [2099.01.01] - 2099-01-01\n\n" + path.read_text())
        with self.assertRaises(v.Invalid):
            v.metadata(self.root)

    def test_unclosed_mermaid_fence_fails(self):
        self.write("README.md", "```mermaid\nflowchart LR\n  A --> B\n")
        with self.assertRaisesRegex(v.Invalid, "unclosed Mermaid"):
            v.markdown(self.root)

    def test_calendar_and_historical_versions(self):
        for value in ["2026.09.05", "2026.09.05.1", "2028.02.29"]:
            v.version_date(value)
        for value in ["2026.02.29", "2026.9.5", "2026.09.05.0", "2026.09.05.01", "1.1.0"]:
            with self.assertRaises(v.Invalid):
                v.version_date(value)
        self.assertIsNone(v.version_date("1.1.0", historical=True))

    def test_active_metadata_valid_and_mutations_fail(self):
        self.copy_metadata()
        v.metadata(self.root)
        cff_path = self.root / "CITATION.cff"
        original = cff_path.read_text()
        edition = (self.root / "VERSION").read_text().strip()
        date = v.version_date(edition)
        for modified in [original.replace('/tag/v' + edition, '/tag/v2099.01.01'),
                         original.replace('cff-version: 1.2.0', 'cff-version: invalid'),
                         original.replace('authors:\n  - family-names: Groux\n    given-names: Brad', 'authors: 42'),
                         original.replace('date-released: ' + str(date), 'date-released: invalid')]:
            cff_path.write_text(modified)
            with self.assertRaises(v.Invalid):
                v.metadata(self.root)
        cff_path.write_text(original)
        for name in ["VERSION", "README.md", "CHARTER.md", "CHANGELOG.md", "CITATION.cff"]:
            f = self.root / name
            f.write_text(f.read_text().replace(edition, '2099.01.01').replace(str(date), '2099-01-01'))
        with self.assertRaisesRegex(v.Invalid, "Missing public regular file"):
            v.metadata(self.root)
        original_note = (self.root / f"project/releases/v{edition}.md").read_text()
        future_note = original_note.replace(edition, "2099.01.01").replace(str(date), "2099-01-01")
        self.write("project/releases/v2099.01.01.md", future_note)
        self.assertEqual(v.metadata(self.root), "2099.01.01")
        for name in ["VERSION", "README.md", "CHARTER.md", "CHANGELOG.md", "CITATION.cff"]:
            path = self.root / name
            path.write_text(path.read_text().replace("2099.01.01", "2099.01.01.1"))
        self.write("project/releases/v2099.01.01.1.md", future_note.replace("2099.01.01", "2099.01.01.1"))
        self.assertEqual(v.metadata(self.root), "2099.01.01.1")

    def test_release_response_state_author_and_body(self):
        good = {"tag_name": "v2026.09.05", "draft": False, "prerelease": False,
                "author": {"login": "BradGroux"}, "published_at": "2026-09-05T04:00:00Z", "body": "Approved\r\n"}
        v.verify_release_response(good, "v2026.09.05", "Approved\n")
        for key, value in [("tag_name", "v1.1.0"), ("draft", True), ("prerelease", True),
                           ("author", {"login": "other"}), ("published_at", "2026-09-06T04:00:00Z"), ("body", "Changed")]:
            with self.subTest(key=key), self.assertRaises(v.Invalid):
                v.verify_release_response({**good, key: value}, "v2026.09.05", "Approved\n")

    def test_api_binds_host_and_repo_despite_environment(self):
        with patch.dict(v.os.environ, {"GH_REPO": "someone/else", "GH_HOST": "example.invalid"}), \
             patch.object(v, "command", return_value='{}') as run:
            v.gh_json([f"repos/{v.REPO}/releases/tags/v2026.09.05"], self.root)
            args = run.call_args.args[0]
            self.assertEqual(args[:4], ["gh", "api", "--hostname", "github.com"])
            self.assertIn("repos/BradGroux/open-framework-commons/releases/tags/v2026.09.05", args)


if __name__ == "__main__":
    unittest.main()
