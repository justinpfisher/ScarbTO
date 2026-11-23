"""Offline tests of the optional Pages stage using a fictional release checkout."""
from hashlib import sha256
import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from scripts import resolve_staged_release as resolver, scarb_notebook_release as notebook

AREA = {"code": "999", "name": "Fable Crossing", "slug": "fable-crossing"}
TARGET = "docs/fable-crossing/index.html"
DATA = {"docs/data/snapshot.json": b"snapshot\n", "docs/community-data/release.json": b"release\n",
        "docs/briefs/edition/index.html": b"<p>Original archive</p>\n"}
PAGE = (b'<link rel="canonical" href="https://scarb.to/fable-crossing/">\n'
        b'<main data-area-code="999" data-neighbourhood-page>\n'
        b'    <h1 id="page-title">Fable Crossing</h1>\n'
        b'    <section>Map and inspection links</section>\n'
        b'    <footer class="page-footer">\n')
SUBJECT = notebook.CLAIM + " Stage the fictional notebook"


class NotebookReleaseTests(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory(prefix="scarb-notebook-")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name) / "repo"
        self.root.mkdir()
        self.event = self.root.parent / "event.json"
        self.git("init", "-q")
        self.git("config", "core.autocrlf", "false")
        self.git("config", "user.name", "Notebook fixture")
        self.git("config", "user.email", "fixture@example.invalid")
        for rel, content in {
            TARGET: PAGE, "docs/other-place/index.html": b"<p>Other place</p>\n",
            notebook.DIRECTORY: b'<li><a href="/fable-crossing/">Fable Crossing</a></li>\n',
            "docs/index.html": b"home\n",
            notebook.RESOLVER: b"old resolver\n", notebook.HELPER: b"reviewed helper\n",
            notebook.WORKFLOW: b"reviewed workflow\n", notebook.VERIFIER: b"reviewed verifier\n",
            **DATA,
        }.items():
            self.write(rel, content)
        self.commit("Fictional verified baseline")
        self.base = self.git("rev-parse", "HEAD")
        self.protected = {name: self.git("rev-parse", f"HEAD:{name}")
                          for name in ("docs/data", "docs/briefs", "docs/community-data")}
        guard = patch.object(resolver, "PROTECTED_TREES", self.protected)
        guard.start()
        self.addCleanup(guard.stop)

    def write(self, rel, content):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    def git(self, *args):
        return subprocess.check_output(["git", *args], cwd=self.root, text=True).strip()

    def commit(self, subject):
        self.git("add", ".")
        self.git("commit", "-qm", subject)

    def activate(self, subject=SUBJECT, extra=False):
        value = {
            "version": notebook.VERSION, "area": AREA, "heading": "Fable note <reviewed>",
            "paragraphs": ["Fictional exhibit & its limit."],
            "links": [{"label": "Fictional catalogue", "url": "https://example.invalid/catalogue?a=1&b=2"}],
            "base_sha256": notebook.digest(PAGE),
        }
        # Only public digest-shaped fixture data. No authored or reviewer receipt
        # is synthesized and no production authority is installed.
        for key in ("packet_sha256", "receipt_sha256", "private_stage_sha256"):
            value[key] = sha256(("fictional " + key).encode()).hexdigest()
        target, expected = notebook.render_page(PAGE, AREA, value["heading"], value["paragraphs"], value["links"])
        self.assertEqual(target, TARGET)
        value["output_sha256"] = notebook.digest(expected)
        raw = (json.dumps(value, sort_keys=True) + "\n").encode()
        self.write(notebook.MANIFEST, raw)
        self.write(notebook.RESOLVER, b"fixture enrolled resolver\n")
        if extra:
            self.write("docs/other-place/index.html", b"extra unreviewed output")
        self.commit(subject)
        head = self.git("rev-parse", "HEAD")
        approval = {"base": self.base, "sha256": notebook.digest(raw), "changed": {notebook.RESOLVER, notebook.MANIFEST},
                    "projection": {rel: self.git("rev-parse", f"HEAD:{rel}")
                                   for rel in notebook.PINNED_FILES | {TARGET}}}
        return expected, head, approval

    def push(self, head, message=SUBJECT, *, forced=False, branch="refs/heads/main"):
        self.event.write_text(json.dumps({"ref": branch, "before": self.base, "after": head,
                                          "forced": forced, "head_commit": {"id": head, "message": message}}),
                              encoding="utf-8")
        return {"GITHUB_EVENT_NAME": "push", "GITHUB_EVENT_PATH": str(self.event), "GITHUB_SHA": head,
                "GITHUB_REF": branch, "GITHUB_REPOSITORY": "justinpfisher/ScarbTO"}

    def site(self):
        return {p.relative_to(self.root).as_posix(): p.read_bytes()
                for p in (self.root / "docs").rglob("*") if p.is_file()}

    def test_default_off_preserves_normal_modes_and_rejects_a_claim(self):
        before = self.site()
        self.assertEqual(resolver.resolve(self.root, {"GITHUB_EVENT_NAME": "schedule"}), "refresh")
        self.assertEqual(resolver.resolve(self.root, self.push(self.base, "Ordinary push")), "refresh")
        self.assertEqual(resolver.resolve(self.root, {"GITHUB_EVENT_NAME": "workflow_dispatch",
                                                     "MANUAL_RELEASE_MODE": "code_only"}), "code_only")
        resolver.apply_notebook(self.root)
        self.assertEqual(self.site(), before)
        with self.assertRaisesRegex(resolver.StageError, "No independently approved Notebook release"):
            resolver.resolve(self.root, self.push(self.base))
        self.assertEqual(self.site(), before)

    def test_staged_output_changes_exactly_one_canonical_page(self):
        output, head, approval = self.activate()
        before = self.site()
        with patch.object(resolver, "NOTEBOOK_APPROVAL", approval):
            self.assertEqual(resolver.resolve(self.root, self.push(head)), "code_only")
            self.assertEqual(self.site(), before)
            resolver.apply_notebook(self.root)
        self.assertEqual(self.site(), {**before, TARGET: output})
        self.assertIn(b'Fable note &lt;reviewed&gt;', output)
        self.assertIn(b'catalogue?a=1&amp;b=2', output)
        self.assertLess(output.index(b"Map and inspection"), output.index(b"Scarb\xe2\x80\x99s notebook"))
        self.assertLess(output.index(b"scarb-notebook-title"), output.index(b'class="page-footer"'))

    def test_later_publish_uses_the_same_activation(self):
        output, _, approval = self.activate()
        self.write("docs/data/snapshot.json", b"later fictional snapshot\n")
        self.commit("Later normal publication")
        before = self.site()
        with patch.object(resolver, "NOTEBOOK_APPROVAL", approval):
            self.assertEqual(resolver.resolve(self.root, {"GITHUB_EVENT_NAME": "schedule"}), "refresh")
            resolver.apply_notebook(self.root)
        self.assertEqual(self.site(), {**before, TARGET: output})

    def test_artifact_needs_approval_and_matches_its_pins(self):
        _, head, approval = self.activate()
        before = self.site()
        with self.assertRaisesRegex(resolver.StageError, "no independent approval"):
            resolver.resolve(self.root, self.push(head))
        with self.assertRaisesRegex(resolver.StageError, "no independent approval"):
            resolver.apply_notebook(self.root)
        with patch.object(resolver, "NOTEBOOK_APPROVAL", approval):
            path = self.root / notebook.MANIFEST
            original = path.read_bytes()
            path.write_bytes(original + b" ")
            with self.assertRaisesRegex(resolver.StageError, "projection bytes differ"):
                resolver.apply_notebook(self.root)
            path.unlink()
            with self.assertRaisesRegex(resolver.StageError, "Missing or invalid approved"):
                resolver.apply_notebook(self.root)
        self.assertEqual(self.site(), before)

    def test_unmarked_forced_wrong_branch_and_competing_stage_cannot_use_code_only(self):
        _, head, approval = self.activate()
        with patch.object(resolver, "NOTEBOOK_APPROVAL", approval):
            with self.assertRaisesRegex(resolver.StageError, "exact Notebook marker"):
                resolver.resolve(self.root, self.push(head, "Missing marker"))
            for message, forced, branch in ((SUBJECT, True, "refs/heads/main"),
                                            (SUBJECT, False, "refs/heads/feature"),
                                            (SUBJECT+" "+resolver.CLAIM, False, "refs/heads/main")):
                with self.assertRaisesRegex(resolver.StageError, "exact main push"):
                    resolver.resolve(self.root, self.push(head, message, forced=forced, branch=branch))

    def test_rejects_unmarked_installation_even_on_later_schedule(self):
        _, _, approval = self.activate(subject="No Notebook marker")
        with patch.object(resolver, "NOTEBOOK_APPROVAL", approval):
            with self.assertRaisesRegex(resolver.StageError, "not installed by its exact staged push"):
                resolver.resolve(self.root, {"GITHUB_EVENT_NAME": "schedule"})

    def test_changed_baseline_or_unexpected_output_blocks_publication(self):
        _, head, approval = self.activate(extra=True)
        with patch.object(resolver, "NOTEBOOK_APPROVAL", approval):
            with self.assertRaisesRegex(resolver.StageError, "unexpected accompanying changes"):
                resolver.resolve(self.root, self.push(head))
            self.write(TARGET, PAGE + b"changed")
            with self.assertRaisesRegex(resolver.StageError, "baseline bytes differ"):
                resolver.apply_notebook(self.root)
        self.write("docs/other-place/index.html", b'<h2 id="scarb-notebook-title">Unreviewed markup</h2>')
        with self.assertRaisesRegex(resolver.StageError, "markup already present"):
            resolver.apply_notebook(self.root)

    def test_only_a_listed_neighbourhood_outside_protected_trees_can_be_targeted(self):
        with self.assertRaisesRegex(notebook.NotebookError, "Invalid Notebook geography"):
            notebook.route_path({**AREA, "slug": "briefs"})
        _, _, approval = self.activate()
        self.write(notebook.DIRECTORY, b"Not listed")
        with patch.object(resolver, "NOTEBOOK_APPROVAL", approval):
            with self.assertRaisesRegex(resolver.StageError, "absent from the qualified directory"):
                resolver.apply_notebook(self.root)
