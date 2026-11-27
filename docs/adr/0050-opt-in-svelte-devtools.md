# ADR-0050: Use opt-in Svelte DevTools for runtime diagnostics

- **Status:** Accepted
- **Date:** 2026-11-27

## Context

When a live schedule update triggers unexpected renders, developers and agents
need to see which Svelte components and reactive dependencies were active in the
browser. The existing Svelte MCP server provides documentation and static checks.
The DevTools plugin exposes runtime measurements and lets agents compare captures
before and after a change. [Upstream DevTools](https://github.com/sveltejs/vite-devtools-svelte#readme)

## Decision

Pin `@sveltejs/vite-devtools-svelte` as a frontend development dependency. Enable
its standalone panel and MCP endpoint only when a local Vite dev server starts
with `SVELTE_DEVTOOLS=1`. Run the MCP relay from the installed package so it uses
the same version as the instrumentation. [Setup guide](../../.agents/context/agent-tooling.md#svelte-runtime-diagnostics)

## Consequences

Developers and agents can inspect the same running app. Captures require an open
browser tab and can include live state values, so use local demo data. The host
server binds to loopback when enabled, and Compose publishes its port on loopback.
Preview, Vitest, and production builds exclude the instrumentation. We accept one
more pinned dependency and occasional pairing or compatibility issues while the
upstream plugin matures.

## Alternatives considered

- **Browser tools and manual logging.** These avoid a dependency but require
  custom instrumentation to reproduce a Svelte reactivity trace for an agent.
- **Vite DevTools dock.** This provides in-page navigation and room for more Vite
  tools. The standalone panel already supplies the Svelte diagnostics and MCP
  endpoint, so we can defer the dock and its extra dependency.
