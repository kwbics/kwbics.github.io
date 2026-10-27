"""Argument and exact-SHA status regressions; no network, publishing or browser."""
import importlib.util
import importlib.machinery
from pathlib import Path
import argparse
import contextlib
import io
import json
import tempfile
import os
import unittest
from unittest.mock import patch

loader = importlib.machinery.SourceFileLoader("site_cli", str(Path(__file__).resolve().parents[1] / "bin/site"))
spec = importlib.util.spec_from_loader(loader.name, loader)
site = importlib.util.module_from_spec(spec)
loader.exec_module(site)
SHA = "a" * 40
OTHER = "b" * 40


class SiteCliTest(unittest.TestCase):
    def test_preview_defaults_to_port_4444(self):
        self.assertEqual(site.parser().parse_args(["preview"]).port, 4444)

    def test_rejects_exposed_host_and_skips(self):
        for args in (["preview", "--host", "0.0.0.0"], ["check", "--skip-build"], ["publish"]):
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                site.parser().parse_args(args)

    def test_invalid_ports(self):
        for port in ("0", "-1", "65536", "abc", "80"):
            with self.assertRaises(argparse.ArgumentTypeError):
                site.port_number(port)

    def test_environment_confines_scratch_and_frozen_dependencies(self):
        with tempfile.TemporaryDirectory(dir=os.environ["TMPDIR"]) as directory:
            root = Path(directory)
            with patch.object(site, "ROOT", root), patch.object(site, "OUTPUT", root / "output/site"), patch.object(site, "TMP", root / "output/site/tmp"):
                with patch.dict(os.environ, {"TMPDIR": "/tmp"}):
                    env = site.environment()
                self.assertTrue(Path(env["TMPDIR"]).is_relative_to(root))
                self.assertTrue(Path(env["TMPDIR"]).is_dir())
                self.assertEqual(env["JEKYLL_ENV"], "production")
                self.assertEqual(env["BUNDLE_FROZEN"], "true")

    def test_preview_binds_loopback(self):
        with tempfile.TemporaryDirectory(dir=os.environ["TMPDIR"]) as directory:
            root = Path(directory)
            (root / "_site").mkdir()
            (root / "_site/index.html").write_text("fixture")
            with patch.object(site, "ROOT", root), patch.object(site.http.server, "ThreadingHTTPServer") as server:
                with contextlib.redirect_stdout(io.StringIO()):
                    site.preview(4444)
                self.assertEqual(server.call_args.args[0], ("127.0.0.1", 4444))
                server.return_value.__enter__.return_value.serve_forever.assert_called_once()

    def test_status_requires_full_sha(self):
        for sha in ("main", "a" * 7, "a" * 39, ";echo unsafe", "g" * 40):
            with self.assertRaises(site.SiteError):
                site.deploy_status(sha)

    def runs(self, *, sha=SHA):
        return [{"id": index, "head_sha": sha, "path": f".github/workflows/{name}",
                 "status": "completed", "conclusion": "success", "run_number": 1,
                 "event": "push", "html_url": f"https://example.test/runs/{index}"}
                for index, name in enumerate(("unit-tests.yml", "prettier.yml", "deploy.yml", "visual-regression.yml"), start=1)]

    def status(self, runs, changes=""):
        def run(args, **kwargs):
            if args[:2] == ["git", "rev-parse"]:
                return SHA + "\n"
            if args[:2] == ["git", "diff-tree"]:
                return changes
            self.assertEqual(args[:4], ["gh", "api", "--paginate", "--slurp"])
            self.assertIn("head_sha=" + SHA, args[4])
            return json.dumps([{"workflow_runs": runs}])
        with patch.object(site, "run", side_effect=run), patch.object(site.shutil, "which", return_value="gh"):
            with contextlib.redirect_stdout(io.StringIO()) as output:
                site.deploy_status(SHA)
            return json.loads(output.getvalue())

    def test_exact_source_all_required_success(self):
        output = self.status(self.runs())
        self.assertEqual(output["source_sha"], SHA)
        self.assertEqual(len(output["remote_ci"]), 4)
        self.assertEqual({item["workflow"] for item in output["remote_ci"]},
                         {"Integration tests", "Prettier code formatter", "Deploy site", "Visual regression checks"})
        self.assertIn("separate manual step", output["scope"])

    def test_success_for_other_head_does_not_count(self):
        with self.assertRaises(site.SiteError):
            self.status(self.runs(sha=OTHER))

    def test_pending_failure_and_missing_workflows_fail(self):
        for state, conclusion in (("in_progress", None), ("completed", "failure"), ("completed", "cancelled")):
            runs = self.runs()
            runs[0].update(status=state, conclusion=conclusion)
            with self.assertRaises(site.SiteError):
                self.status(runs)
        with self.assertRaises(site.SiteError):
            self.status(self.runs()[:-1])

    def test_visual_pending_or_failure_prevents_success(self):
        for state, conclusion in (("queued", None), ("in_progress", None), ("completed", "failure")):
            with self.subTest(state=state, conclusion=conclusion):
                runs = self.runs()
                visual = next(run for run in runs if run["path"].endswith("/visual-regression.yml"))
                visual.update(status=state, conclusion=conclusion)
                with self.assertRaisesRegex(site.SiteError, "Visual regression checks"):
                    self.status(runs)

    def test_newest_visual_failure_is_not_hidden_by_older_success(self):
        runs = self.runs()
        visual = next(run for run in runs if run["path"].endswith("/visual-regression.yml"))
        runs.append(dict(visual, id=10, run_number=2, conclusion="failure"))
        with self.assertRaisesRegex(site.SiteError, "Visual regression checks"):
            self.status(runs)

    def test_other_head_visual_success_does_not_count(self):
        runs = self.runs()
        visual = next(run for run in runs if run["path"].endswith("/visual-regression.yml"))
        visual["head_sha"] = OTHER
        with self.assertRaisesRegex(site.SiteError, "Visual regression checks"):
            self.status(runs)

    def test_newest_failure_is_not_hidden_by_older_success(self):
        runs = self.runs()
        runs.append(dict(runs[0], id=10, run_number=2, conclusion="failure"))
        with self.assertRaises(site.SiteError):
            self.status(runs)

    def test_pr_deploy_success_is_not_publishing_success(self):
        runs = self.runs()
        next(run for run in runs if run["path"].endswith("/deploy.yml"))["event"] = "pull_request"
        with self.assertRaises(site.SiteError):
            self.status(runs)

    def test_related_cv_change_requires_cv_workflow(self):
        with self.assertRaises(site.SiteError):
            self.status(self.runs(), "_data/cv.yml\n")

    def test_non_pdf_cv_paths_only_require_four_core_workflows(self):
        for path in ("_pages/cv.md", "_data/cv.yaml"):
            with self.subTest(path=path):
                output = self.status(self.runs(), path + "\n")
                self.assertEqual(len(output["remote_ci"]), 4)
                self.assertNotIn("Render a CV", {item["workflow"] for item in output["remote_ci"]})

    def test_rendercv_asset_prefix_requires_cv_workflow(self):
        for path in ("assets/rendercv/design.yaml", "assets/rendercv/nested/new-asset.yaml"):
            with self.subTest(path=path), self.assertRaisesRegex(site.SiteError, "Render a CV"):
                self.status(self.runs(), path + "\n")

    def test_rendercv_prefix_does_not_match_neighbor_directory(self):
        output = self.status(self.runs(), "assets/rendercv-other/design.yaml\n")
        self.assertEqual(len(output["remote_ci"]), 4)

    def test_present_cv_workflow_failure_is_detected(self):
        runs = self.runs()
        runs.append(dict(runs[0], path=".github/workflows/render-cv.yml", id=5, conclusion="failure"))
        with self.assertRaises(site.SiteError):
            self.status(runs)

    def test_command_failure_is_nonzero(self):
        with contextlib.redirect_stderr(io.StringIO()), patch.object(site, "environment", side_effect=site.SiteError("fixture failure")):
            self.assertEqual(site.main(["check"]), 1)


if __name__ == "__main__":
    unittest.main()
