# fanapp

## MCP configuration

This repository includes a repo-level MCP configuration at `.mcp.json` with a `svelte` server entry.

### What the Svelte MCP server provides

The Svelte MCP server (`@sveltejs/mcp`) exposes Svelte and SvelteKit-aware context/tools to MCP-compatible clients so they can better understand project files, framework conventions, and related development workflows.

### Startup and log verification

From the repository root, you can verify the server starts by running:

```sh
npx -y @sveltejs/mcp
```

When startup is successful, you should see normal MCP server startup logs (for example, initialization/ready output) and no module resolution errors. The configured working directory is `frontend`, so context resolution happens against this app.

### Expected runtime availability

Running this MCP server expects:

- Node.js available on `PATH` (to run `npx`)
- `pnpm` typically available for this repository's frontend workflow (`frontend/pnpm-lock.yaml`), although MCP startup itself is invoked via `npx`
