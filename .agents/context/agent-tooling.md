# Agent tooling

How the agent setup in this repo works. `AGENTS.md` holds the rules; this file holds the mechanics. Read it when you change the tooling itself.

## Svelte AI tooling

Codex loads the Svelte MCP server from [`.codex/config.toml`](../../.codex/config.toml) in a trusted checkout. Keep its command in sync with `.mcp.json` and `.vscode/mcp.json`. The Svelte skills are shared under `.agents/skills/`. [Svelte AI tooling](https://svelte.dev/docs/ai/overview)

The Codex server uses the environment's HTTP proxy settings to fetch Svelte documentation. [Node.js proxy settings](https://nodejs.org/learn/http/enterprise-network-configuration)

The `@sveltejs/mcp` 0.1.x CLI accepts only a major for `--svelte-version` (`5`).

## Vendored skills

Update vendored skills with `npx skills update --project`. `skills-lock.json` records their sources. The `fanfan-*` skills are local to Fanapp.

Codex discovers skills from their names and descriptions in `.agents/skills/`. Keep those descriptions specific to the tasks that need them. Put project rules and guide links in `AGENTS.md`. Keep examples and longer workflows in the guide or skill that owns them. [Codex skill guidance](https://learn.chatgpt.com/docs/build-skills)

Matt Pocock's engineering and productivity skills are installed in the shared `.agents/skills/` directory. Fanapp disables the Codex plugin in its project settings to prevent duplicate skills. [Upstream bundle](https://github.com/mattpocock/skills) · [MIT license](../skills/LICENSE-mattpocock-skills)

[Modern Web Guidance](https://github.com/GoogleChrome/modern-web-guidance) is installed at `.agents/skills/modern-web-guidance/`. Keep a copy of the upstream [Apache 2.0 license](../skills/modern-web-guidance/LICENSE) in that folder after updates. Its guides use [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) and include material derived from MDN and W3C, WHATWG, and IETF specifications. [Upstream license notice](https://github.com/GoogleChrome/modern-web-guidance#license)

`npx skills update` overwrites local edits, so re-apply these after one until upstream carries them:

- In `antislop` (R-25) and `antislop-human` (`SKILL.md` and `contrast-check.py`), use the WCAG large-text threshold of 24px, or about 18.66px bold. [W3C, Understanding 1.4.3](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum)
- `antislop-human/references/A11Y-PATTERNS.md`: the fallback focus trap filters disabled, hidden, inert and non-tabbable controls on each Tab keypress, and handles dialogs with no tab stops.

## CodeGraph

CodeGraph is opt-in. Check that the local index and tools are available before using it. The tracked `.codegraph/.gitignore` reserves the directory for local index files.
