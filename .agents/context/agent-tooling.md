# Agent tooling

How the agent setup in this repo works. `AGENTS.md` holds the rules; this file holds the mechanics. Read it when you change the tooling itself.

## Svelte AI tooling

Codex loads the Svelte MCP server from [`.codex/config.toml`](../../.codex/config.toml) in a trusted checkout. Keep its command in sync with `.mcp.json` and `.vscode/mcp.json`. The Svelte skills are shared under `.agents/skills/`. [Svelte AI tooling](https://svelte.dev/docs/ai/overview)

The Codex server uses the environment's HTTP proxy settings to fetch Svelte documentation. [Node.js proxy settings](https://nodejs.org/learn/http/enterprise-network-configuration)

The `@sveltejs/mcp` 0.1.x CLI accepts only a major for `--svelte-version` (`5`).

## Svelte runtime diagnostics

Use Svelte DevTools to trace reactivity or compare render profiles. Install the locked frontend dependencies with `just frontend-install` and start the frontend with `SVELTE_DEVTOOLS=1 just frontend-dev`. Open the app and reproduce the interaction in a browser. For the standalone panel, open `/.svelte-devtools/` on the same origin and enter the pairing code from the frontend terminal. [Svelte DevTools setup](https://github.com/sveltejs/vite-devtools-svelte#setup)

If the first panel shows an authorization error after pairing, click **Retry**. [Upstream pairing issue](https://github.com/sveltejs/vite-devtools-svelte/issues/262)

For a host dev server, the project Codex config starts `svelte-devtools` with the installed frontend package. Open a new Codex session in the trusted checkout and use `list_dev_servers` to find fanapp. For Docker, start with `SVELTE_DEVTOOLS=1 just dev --build` after installing the dependency. Register the relay inside the frontend container so it can discover the server and read its rotating token. Run this from the checkout root and open a new Codex session there.

```sh
codex mcp add svelte-devtools-docker -- docker compose \
  -f docker-compose.yml -f docker-compose.dev.yml --profile core \
  exec -T frontend pnpm exec vite-devtools-svelte mcp
```

Use local demo data. Record the same action with the same data before and after a change, then compare the sessions. Start with render counts and hotspots, inspect individual reactive scopes as needed, and check capture coverage before drawing conclusions. Keep captures in memory unless you need to preserve them. [MCP tool reference](https://sveltejs.github.io/vite-devtools-svelte/mcp/)

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
