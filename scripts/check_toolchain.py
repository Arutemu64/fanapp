"""Check shared pins offline using Python 3.11+, before installing the project.

Like Airflow's check_go_version_in_sync.py, missing declarations fail closed.
See docs/dependencies.md for sources and the distinction between pins and ranges.
"""

from __future__ import annotations

import json
import re
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
VERSION = r"\d+\.\d+\.\d+"


@dataclass(frozen=True)
class PinSite:
    tool: str
    path: str
    pattern: str


POSTGRES_SOURCE = PinSite(
    "postgres", "docker-compose.yml", r"(?m)^\s+image: postgres:([^\s]+)"
)
GITLEAKS_SOURCE = PinSite(
    "gitleaks",
    ".pre-commit-config.yaml",
    r"repo: https://github.com/gitleaks/gitleaks\s+rev: v?([^\s]+)",
)

SITES = (
    PinSite("python", "backend/.python-version", r"(?m)^([^\s]+)$"),
    PinSite(
        "node",
        "frontend/Dockerfile",
        r"(?mi)^FROM\s+(?:--platform=\S+\s+)?node:([^\s]+)",
    ),
    PinSite("pnpm", "frontend/Dockerfile", r"(?m)^ENV PNPM_VERSION=([^\s]+)"),
    PinSite("uv", "backend/Dockerfile", r"ghcr\.io/astral-sh/uv:([^\s]+)"),
    POSTGRES_SOURCE,
    PinSite(
        "postgres", "backend/scripts/generate_migration.py", r'postgres:([^"\s]+)"'
    ),
    PinSite(
        "postgres", "backend/tests/fixtures/db_provider.py", r'postgres:([^"\s]+)"'
    ),
    PinSite(
        "postgres-backup-local", "docker-compose.yml", r"postgres-backup-local:([^\s]+)"
    ),
    PinSite(
        "hadolint",
        ".pre-commit-config.yaml",
        r"repo: https://github.com/hadolint/hadolint\s+rev: v?([^\s]+)",
    ),
    GITLEAKS_SOURCE,
    PinSite(
        "gitleaks", ".github/workflows/ci.yml", r"(?m)^\s+GITLEAKS_VERSION: ([^\s]+)"
    ),
)


def read_matches(root: Path, site: PinSite) -> list[str]:
    matches = re.findall(site.pattern, (root / site.path).read_text())
    if not matches:
        raise ValueError(
            f"{site.path}: missing {site.tool} pin; expected {site.pattern}"
        )
    return matches


def read_version(root: Path, path: str, *keys: str) -> str:
    try:
        text = (root / path).read_text()
        value = json.loads(text) if path.endswith(".json") else tomllib.loads(text)
        for key in keys:
            value = value[key]
        if not isinstance(value, str):
            raise TypeError("expected a version string")
        return value
    except (ValueError, TypeError, KeyError) as error:
        raise ValueError(f"{path}: {'.'.join(keys)}: {error}") from error


def normalize(tool: str, value: str) -> str:
    if tool == "postgres":
        if not re.fullmatch(r"\d+\.\d+(?:\.\d+)?-[\w.-]+@sha256:[a-f0-9]{64}", value):
            raise ValueError(
                f"postgres: expected an exact tag and OCI digest, found {value!r}"
            )
        return value
    if tool == "postgres-backup-local":
        if not re.fullmatch(r"\d+-[\w.-]+@sha256:[a-f0-9]{64}", value):
            raise ValueError(
                "postgres-backup-local: expected a major tag and OCI digest, "
                f"found {value!r}"
            )
        return value.split("-", 1)[0]
    if not re.fullmatch(VERSION, value):
        raise ValueError(f"{tool}: expected an exact X.Y.Z pin, found {value!r}")
    return value


def source_versions(root: Path) -> dict[str, str]:
    versions = {}
    for tool in ("python", "node", "pnpm", "uv", "hadolint"):
        versions[tool] = normalize(tool, read_version(root, "mise.toml", "tools", tool))
    postgres = read_matches(root, POSTGRES_SOURCE)[0]
    versions["postgres"] = postgres
    versions["postgres-backup-local"] = postgres.split(".", 1)[0]
    versions["gitleaks"] = read_matches(root, GITLEAKS_SOURCE)[0]
    return versions


def compare_pin(tool: str, value: str, expected: str, label: str) -> list[str]:
    try:
        if label.endswith("Dockerfile") and tool in {"node", "uv"}:
            tag, _, digest = value.partition("@")
            if not re.fullmatch(r"sha256:[a-f0-9]{64}", digest):
                raise ValueError(f"{tool}: expected an OCI digest in {value!r}")
            value = tag.split("-", 1)[0]
        actual = normalize(tool, value)
    except ValueError as error:
        return [f"{label}: {error}"]
    if actual == expected:
        return []
    return [f"{label}: {tool} is {actual!r}; expected {expected!r}"]


def check_manifest_pins(root: Path, versions: dict[str, str]) -> list[str]:
    for tool in ("node", "npm:renovate"):
        normalize(tool, read_version(root, ".github/renovate/mise.toml", "tools", tool))
    manager = read_version(root, "frontend/package.json", "packageManager")
    if not manager.startswith("pnpm@"):
        raise ValueError("frontend/package.json: packageManager must pin pnpm")
    errors = compare_pin(
        "pnpm", manager[5:].split("+", 1)[0], versions["pnpm"], "frontend/package.json"
    )
    required = read_version(
        root, "backend/pyproject.toml", "tool", "uv", "required-version"
    )
    if not required.startswith("=="):
        raise ValueError("backend/pyproject.toml: required-version must pin uv with ==")
    errors.extend(
        compare_pin("uv", required[2:], versions["uv"], "backend/pyproject.toml")
    )
    return errors


def check(root: Path) -> list[str]:
    try:
        versions = source_versions(root)
        errors = check_manifest_pins(root, versions)
        for site in SITES:
            for value in read_matches(root, site):
                errors.extend(
                    compare_pin(site.tool, value, versions[site.tool], site.path)
                )
        return errors
    except (OSError, ValueError, KeyError, TypeError) as error:
        return [str(error)]


def main() -> int:
    errors = check(REPO_ROOT)
    if errors:
        print("Toolchain consistency check failed:", file=sys.stderr)
        for error in errors:
            print(f"  {error}", file=sys.stderr)
        return 1
    print("Shared toolchain pins agree.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
