"""Exercise the checker against changed copies of the repository's declarations."""

import json
import re
import shutil
import tempfile
import tomllib
import unittest
from pathlib import Path

from check_toolchain import check

REPO_ROOT = Path(__file__).resolve().parents[1]
PIN_FILES = (
    "mise.toml",
    ".github/renovate/mise.toml",
    "backend/.python-version",
    "backend/pyproject.toml",
    "backend/Dockerfile",
    "backend/scripts/generate_migration.py",
    "backend/tests/fixtures/db_provider.py",
    "frontend/package.json",
    "frontend/Dockerfile",
    "docker-compose.yml",
    ".pre-commit-config.yaml",
    ".github/workflows/ci.yml",
)


class ToolchainTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        for name in PIN_FILES:
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(REPO_ROOT / name, target)

    def replace(self, name: str, before: str, after: str) -> None:
        path = self.root / name
        original = path.read_text()
        self.assertIn(before, original)
        path.write_text(original.replace(before, after))

    def test_repository_pins_agree(self) -> None:
        self.assertEqual(check(self.root), [])

    def test_python_patch_drift_fails(self) -> None:
        (self.root / "backend/.python-version").write_text("3.14.1\n")
        self.assertTrue(
            any("backend/.python-version" in error for error in check(self.root))
        )

    def test_missing_file_fails(self) -> None:
        (self.root / "backend/.python-version").unlink()
        self.assertTrue(
            any("backend/.python-version" in error for error in check(self.root))
        )

    def test_missing_package_manager_names_the_manifest(self) -> None:
        path = self.root / "frontend/package.json"
        package = json.loads(path.read_text())
        del package["packageManager"]
        path.write_text(json.dumps(package))
        self.assertTrue(
            any("frontend/package.json" in error for error in check(self.root))
        )

    def test_missing_mise_tool_names_the_manifest(self) -> None:
        path = self.root / "mise.toml"
        version = tomllib.loads(path.read_text())["tools"]["uv"]
        self.replace("mise.toml", f'uv = "{version}"', "")
        self.assertTrue(any("mise.toml" in error for error in check(self.root)))

    def test_unrecognized_pin_syntax_fails(self) -> None:
        self.replace(
            "frontend/Dockerfile", "ENV PNPM_VERSION=", "ENV OLD_PNPM_VERSION="
        )
        self.assertTrue(any("PNPM_VERSION" in error for error in check(self.root)))

    def test_second_docker_stage_cannot_use_another_node_version(self) -> None:
        path = self.root / "frontend/Dockerfile"
        path.write_text(
            path.read_text()
            + "\nFROM node:22.1.0-alpine@sha256:"
            + "a" * 64
            + " AS extra\n"
        )
        self.assertTrue(any("22.1.0" in error for error in check(self.root)))

    def test_platform_specific_docker_stage_cannot_drift(self) -> None:
        path = self.root / "frontend/Dockerfile"
        path.write_text(
            path.read_text()
            + "\nFROM --platform=$BUILDPLATFORM node:22.1.0-alpine@sha256:"
            + "a" * 64
            + " AS extra\n"
        )
        self.assertTrue(any("22.1.0" in error for error in check(self.root)))

    def test_mise_rejects_a_container_suffix_in_a_runtime_pin(self) -> None:
        version = tomllib.loads((self.root / "mise.toml").read_text())["tools"]["node"]
        self.replace("mise.toml", f'node = "{version}"', f'node = "{version}-alpine"')
        self.assertTrue(check(self.root))

    def test_compatibility_floor_is_not_an_exact_runtime_pin(self) -> None:
        project = tomllib.loads((self.root / "backend/pyproject.toml").read_text())
        floor = project["project"]["requires-python"]
        self.replace(
            "backend/pyproject.toml",
            f'requires-python = "{floor}"',
            'requires-python = ">=3.13"',
        )
        self.assertEqual(check(self.root), [])

    def test_postgres_image_digest_drift_fails(self) -> None:
        path = self.root / "backend/tests/fixtures/db_provider.py"
        path.write_text(
            re.sub(r"@sha256:[a-f0-9]{64}", "@sha256:" + "a" * 64, path.read_text())
        )
        self.assertTrue(any("db_provider.py" in error for error in check(self.root)))

    def test_a_docker_runtime_cannot_drop_its_digest(self) -> None:
        path = self.root / "frontend/Dockerfile"
        original = path.read_text()
        start = original.index("@sha256:", original.index("FROM node:"))
        path.write_text(original[:start] + original[start + len("@sha256:") + 64 :])
        self.assertTrue(
            any("frontend/Dockerfile" in error for error in check(self.root))
        )

    def test_backup_image_must_follow_the_postgres_major(self) -> None:
        compose = (self.root / "docker-compose.yml").read_text()
        major = re.search(r"postgres-backup-local:(\d+)-", compose).group(1)
        self.replace(
            "docker-compose.yml",
            f"postgres-backup-local:{major}-",
            f"postgres-backup-local:{int(major) - 1}-",
        )
        self.assertTrue(
            any("postgres-backup-local" in error for error in check(self.root))
        )


if __name__ == "__main__":
    unittest.main()
