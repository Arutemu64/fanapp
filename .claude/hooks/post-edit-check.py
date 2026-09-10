#!/usr/bin/env python3
"""PostToolUse hook: give the agent immediate feedback on the file it just edited.

AGENTS.md and .claude/rules/*.md ask the agent to run `just backend-lint` /
`just frontend-lint` after a change. That is prose asking a model to remember;
this runs the check instead and feeds the result back as additionalContext.

Deliberately CHECK-ONLY, never --fix. A hook that rewrites the file behind the
agent invalidates the string it is about to edit next, and it removes the
feedback signal that is the entire point. The pre-commit hooks still auto-fix
at commit time, so nothing here has to.

Scope is one file and a hard latency budget (hooks are synchronous, so every
millisecond is added to the agent's turn). Measured on this repo:
    ruff check       ~0.3s   -> in
    prettier --check ~1.2s   -> in
    eslint           ~8.7s   -> OUT, stays in pre-commit and CI
    ty / svelte-check       whole-project -> OUT, pre-push and CI already run them
That mirrors the fast/slow split .pre-commit-config.yaml already makes between
its pre-commit and pre-push stages.

Exits 0 always. PostToolUse cannot block (the tool has already run), and its
stderr never reaches the agent — the JSON `additionalContext` field is the only
channel that does. See https://code.claude.com/docs/en/hooks
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

TIMEOUT_SECONDS = 30

# Attributes whose value a user actually reads. `title` doubles as a non-visible
# SVG label, which is still user-facing to a screen reader.
USER_FACING_ATTRS = ("placeholder", "title", "alt", "aria-label")

CYRILLIC = re.compile(r"[Ѐ-ӿ]")
LATIN_WORD = re.compile(r"[A-Za-z]{4,}")

# A token carrying @ _ . or a digit is an identifier, address or URL, not prose:
# name@example.com, nomination_title, PUBLIC_API_URL, Arutemu64.
IDENTIFIERISH = re.compile(r"[A-Za-z][A-Za-z0-9]*[@_.0-9]")

# Proper nouns that stay Latin in Russian copy — brand and technology names, and
# the festival's own latinised name.
COPY_ALLOWLIST = frozenset(
    {
        "fan",
        "fanfan",
        "pwa",
        "telegram",
        "github",
        "fastapi",
        "svelte",
        "sveltekit",
        "postgresql",
        "python",
        "http",
        "https",
        "email",
    }
)


def run(cmd: list[str], cwd: Path) -> tuple[int, str]:
    try:
        proc = subprocess.run(  # noqa: S603
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        # A missing toolchain must never nag the agent about its own edit.
        return 0, f"(skipped: {exc})"
    # Diagnostics go to stdout; stderr is the fallback for a tool that failed
    # before it could report. Preferring stdout keeps unrelated runtime chatter
    # (uv's own deprecation warnings, for one) out of the agent's context.
    return proc.returncode, (proc.stdout.strip() or proc.stderr.strip())


def check_python(path: Path, repo: Path) -> str | None:
    rel = path.relative_to(repo / "backend")
    code, out = run(["uv", "run", "ruff", "check", str(rel)], repo / "backend")
    return out if code != 0 and out else None


def check_prettier(path: Path, repo: Path) -> str | None:
    rel = path.relative_to(repo / "frontend")
    code, _ = run(["pnpm", "exec", "prettier", "--check", str(rel)], repo / "frontend")
    if code == 0:
        return None
    # prettier --check only names the file; say what to do about it instead of
    # forwarding its output, which carries no diagnostic beyond pass/fail.
    return (
        "Not formatted to Prettier style. Fix with:\n"
        f"  cd frontend && pnpm exec prettier --write {rel}"
    )


def strip_non_markup(source: str) -> str:
    """Drop <script>/<style> bodies, comments and {expressions} from a Svelte file.

    What is left is roughly the static text a visitor reads. Crude on purpose: a
    real parser would be more precise, but this only has to be good enough to
    nudge, and it must stay fast.
    """
    source = re.sub(r"<script[^>]*>.*?</script>", " ", source, flags=re.DOTALL)
    source = re.sub(r"<style[^>]*>.*?</style>", " ", source, flags=re.DOTALL)
    source = re.sub(r"<!--.*?-->", " ", source, flags=re.DOTALL)

    # Monospace content is an identifier the user must type verbatim (a
    # spreadsheet column, an env var), not copy to translate.
    source = re.sub(r"<(code|kbd|pre)\b[^>]*>.*?</\1>", " ", source, flags=re.DOTALL)
    source = re.sub(
        r"<(\w+)[^>]*\bfont-mono\b[^>]*>.*?</\1>", " ", source, flags=re.DOTALL
    )

    # Svelte expressions nest — {#snippet child({ props })} — so one non-greedy
    # pass leaves the outer braces behind. Peel innermost-first until stable.
    while True:
        stripped = re.sub(r"\{[^{}]*\}", " ", source)
        if stripped == source:
            return stripped
        source = stripped


def english_runs(source: str) -> list[str]:
    """Latin-script user-facing runs that contain no Cyrillic at all."""
    markup = strip_non_markup(source)

    candidates = re.findall(r">([^<>]+)<", markup)
    for attr in USER_FACING_ATTRS:
        candidates += re.findall(rf'{attr}="([^"{{}}]+)"', markup)

    hits = []
    for raw in candidates:
        text = raw.strip()
        if not text or CYRILLIC.search(text):
            continue
        if any(IDENTIFIERISH.search(token) for token in text.split()):
            continue
        words = [w for w in LATIN_WORD.findall(text) if w.lower() not in COPY_ALLOWLIST]
        if words:
            hits.append(" ".join(text.split())[:80])
    return hits


def check_russian_copy(path: Path) -> str | None:
    """Advisory only: AGENTS.md forbids user-facing English, and English is the
    register a language model falls back to. Heuristic, so it never gates CI —
    it just puts the question in front of the agent while the edit is fresh."""
    hits = english_runs(path.read_text(encoding="utf-8"))
    if not hits:
        return None
    listed = "\n".join(f"  - {h}" for h in dict.fromkeys(hits))
    return (
        "Possible user-facing English (AGENTS.md: every user-visible string is "
        f"Russian).\n{listed}\n"
        "Ignore any of these that are not user-visible copy — this is a heuristic."
    )


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except ValueError:
        return 0

    raw_path = (event.get("tool_input") or {}).get("file_path")
    if not raw_path:
        return 0

    repo = Path(event.get("cwd") or ".").resolve()
    while not (repo / ".git").exists() and repo != repo.parent:
        repo = repo.parent

    path = Path(raw_path).resolve()
    if not path.is_file():
        return 0
    try:
        relative = path.relative_to(repo)
    except ValueError:
        return 0

    parts = relative.parts
    area = parts[0] if parts else ""
    reports: list[str] = []

    if area == "backend" and path.suffix == ".py":
        reports.append(check_python(path, repo))
    elif area == "frontend" and path.suffix in {
        ".svelte",
        ".ts",
        ".js",
        ".css",
        ".json",
    }:
        reports.append(check_prettier(path, repo))
        if path.suffix == ".svelte":
            reports.append(check_russian_copy(path))

    found = [r for r in reports if r]
    if not found:
        return 0

    # stdout is the hook's output channel, not logging.
    print(  # noqa: T201
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": f"Checks on {relative}:\n\n"
                    + "\n\n".join(found),
                }
            }
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
