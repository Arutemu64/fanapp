# Agent tooling

How the agent setup in this repo works. `AGENTS.md` holds the rules; this file holds the mechanics. Read it when you change the tooling itself.

## Svelte AI tooling

The official [`sveltejs/ai-tools`](https://svelte.dev/docs/ai/overview) are configured in `.mcp.json`. The Svelte skills are vendored under `.agents/skills/`.

The `@sveltejs/mcp` 0.1.x CLI accepts only a major for `--svelte-version` (`5`).

## Vendored skills

Skills are managed with `npx skills` and pinned in `skills-lock.json`. The `fanfan-*` skills are local to this repo.

`npx skills update` overwrites local edits, so re-apply these after one until upstream carries them:

- `antislop` (R-25) and `antislop-human` (guide, `contrast-check.py`, `contrast-mcp.py`): WCAG large text is 24px, or about 18.66px bold, not "18px+". Compare the unrounded contrast ratio, since 4.499:1 fails 4.5:1 ([W3C, Understanding 1.4.3](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum)).
- `antislop-human/references/A11Y-PATTERNS.md`: the fallback focus trap filters disabled, hidden, inert and non-tabbable controls on each Tab keypress, and handles dialogs with no tab stops.
- `setup-matt-pocock-skills` writes its config to `.agents/context/`, not upstream's `docs/agents/`.

## CodeGraph

`.codegraph/` at the repo root means the index is live. CodeGraph is opt-in; don't install it unless asked.
