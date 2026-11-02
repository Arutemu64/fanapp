"""Keep custom Renovate extraction tied to the declarations it must update."""

import json
import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def patterns_for(dependency: str) -> list[re.Pattern[str]]:
    config = json.loads((REPO_ROOT / "renovate.jsonc").read_text())
    manager = next(
        manager
        for manager in config["customManagers"]
        if manager["depNameTemplate"] == dependency
    )
    # These RE2 patterns also work with Python after adapting named groups.
    return [
        re.compile(re.sub(r"\(\?<([A-Za-z]+)>", r"(?P<\1>", pattern))
        for pattern in manager["matchStrings"]
    ]


class RenovateExtractionTests(unittest.TestCase):
    def test_postgres_literals_capture_the_same_tag_and_digest_as_compose(self) -> None:
        compose = (REPO_ROOT / "docker-compose.yml").read_text()
        image = re.search(r"image: postgres:(\S+)", compose).group(1)
        for path in (
            "backend/scripts/generate_migration.py",
            "backend/tests/fixtures/db_provider.py",
        ):
            with self.subTest(path=path):
                match = patterns_for("postgres")[0].search(
                    (REPO_ROOT / path).read_text()
                )
                self.assertIsNotNone(match)
                self.assertEqual(
                    image, match["currentValue"] + "@" + match["currentDigest"]
                )

    def test_postgres_manager_also_recognizes_a_tag_before_digest_pinning(self) -> None:
        match = patterns_for("postgres")[0].search('"postgres:18.6-alpine"')
        self.assertEqual(match["currentValue"], "18.6-alpine")
        self.assertIsNone(match["currentDigest"])

    def test_gitleaks_ci_literal_remains_extractable(self) -> None:
        workflow = (REPO_ROOT / ".github/workflows/ci.yml").read_text()
        matches = patterns_for("gitleaks/gitleaks")[0].findall(workflow)
        self.assertEqual(len(matches), 1)
        self.assertRegex(matches[0], r"^\d+\.\d+\.\d+$")

    def test_uv_required_version_remains_extractable(self) -> None:
        project = (REPO_ROOT / "backend/pyproject.toml").read_text()
        matches = patterns_for("uv")[0].findall(project)
        self.assertEqual(len(matches), 1)
        self.assertRegex(matches[0], r"^\d+\.\d+\.\d+$")


if __name__ == "__main__":
    unittest.main()
