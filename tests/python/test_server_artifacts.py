import tempfile
import unittest
from pathlib import Path

from web_app.server import collect_project_artifacts


class ProjectArtifactTests(unittest.TestCase):
    def test_lists_only_visible_regular_workspace_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            (workspace / "report.md").write_text("report", encoding="utf-8")
            (workspace / "results").mkdir()
            (workspace / "results" / "data.json").write_text("{}", encoding="utf-8")
            (workspace / ".git").mkdir()
            (workspace / ".git" / "config").write_text("secret", encoding="utf-8")
            (workspace / "report-link.md").symlink_to(workspace / "report.md")

            artifacts = collect_project_artifacts(workspace, "11111111-1111-4111-8111-111111111111")

        paths = {item["path"] for item in artifacts}
        self.assertEqual(paths, {"report.md", "results/data.json"})
        report = next(item for item in artifacts if item["path"] == "report.md")
        self.assertEqual(report["mime"], "text/markdown")
        self.assertEqual(
            report["url"],
            "/api/projects/11111111-1111-4111-8111-111111111111/artifacts/report.md",
        )


if __name__ == "__main__":
    unittest.main()
