# Agent tooling

How the agent setup in this repo works. `AGENTS.md` holds the rules; this file holds the mechanics. Read it when you change the tooling itself.

## Edit hook

`.claude/hooks/post-edit-check.py` (wired in `.claude/settings.json`) checks the one file just edited:

- `ruff check` on `backend/**/*.py`;
- `prettier --check` on `frontend/**`;
- the Tailwind design-system class rules on `frontend/src` (ADR-0030, about 1s via `eslint.tailwind.config.js`);
- a heuristic scan of `.svelte` markup for user-facing English.

It only checks, never `--fix`: a hook that rewrites the file invalidates the next edit. It skips full ESLint (about 9s), `ty` and `svelte-check`, which run at pre-push and in CI. A silent hook means the fast checks passed, not that the work is done.

## Secret reads

`.claude/settings.json` denies `secrets/**`, `*.pem` and `*.key`. `.env` is not denied, because fixing drift against `.env.example` is agent work. The deny rules bind the `Read` tool, not `cat` in Bash.

## Subagents

`.claude/agents/` holds three subagents. Each runs in its own context and returns a summary. That saves context in the parent session, not tokens: total usage goes up.

| Agent                | Does                                                                                 | Model  |
| -------------------- | ------------------------------------------------------------------------------------ | ------ |
| `gate-runner`        | Runs the lint, typecheck, test and drift gates; reports pass/fail. Fixes nothing.    | sonnet |
| `migration-reviewer` | Read-only safety review of a migration against the deployed database.                | opus   |
| `ru-copy`            | Writes and revises Russian user-facing strings, including both halves of each email. | opus   |

Delegate verbose or well-bounded work. Keep targeted edits and cross-file design judgment inline. A subagent cannot see the conversation, so put everything it needs in the prompt.

When you edit one: keep the body short and the output format explicit, move procedure into a skill via `skills:`, and restrict `tools:` to the job. A reviewer without `Edit` cannot quietly "fix" what it was asked to report.

## Svelte AI tooling

The official [`sveltejs/ai-tools`](https://svelte.dev/docs/ai/overview) are wired twice, because a cloud session doesn't install plugins a repo enables ([what carries over](https://code.claude.com/docs/en/cloud-environments#what-carries-over-from-your-setup)):

- **Locally:** `.claude/settings.json` enables the `svelte` plugin (MCP server, both skills, `svelte-file-editor` subagent). That subagent doesn't run our gates or know our copy rules, so the caller still runs them and routes strings through `ru-copy`.
- **Everywhere:** `.mcp.json` declares the same `svelte` MCP server, and the two skills are vendored. Keep its command identical to the plugin's; Claude Code dedupes the two by command ([MCP scope precedence](https://code.claude.com/docs/en/mcp#scope-hierarchy-and-precedence)).

The `@sveltejs/mcp` 0.1.x CLI accepts only a major for `--svelte-version` (`5`).

## Vendored skills

Skills are managed with `npx skills` and pinned in `skills-lock.json`. The `fanfan-*` skills are local to this repo.

`npx skills update` overwrites local edits, so re-apply these after one until upstream carries them:

- `antislop` (R-25) and `antislop-human` (guide, `contrast-check.py`, `contrast-mcp.py`): WCAG large text is 24px, or about 18.66px bold, not "18px+". Compare the unrounded contrast ratio, since 4.499:1 fails 4.5:1 ([W3C, Understanding 1.4.3](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum)).
- `setup-matt-pocock-skills` writes its config to `.agents/context/`, not upstream's `docs/agents/`.

## CodeGraph

`.codegraph/` at the repo root means the index is live. Web sessions provision it ([docs/claude-cloud.md](../../docs/claude-cloud.md)). Locally it is opt-in; don't install it unless asked. Usage lives in the vendor-managed block in `.claude/CLAUDE.md`, which `codegraph upgrade` rewrites, so don't hand-edit it.
