# Mission

- Build a helper web app for "FAN FAN", a Russian anime convention.
- Optimize every change for utility, clarity, and mobile responsiveness.
- Follow industry best practices.
- Keep all user-facing copy in Russian.

# Stack

- Framework: SvelteKit with Svelte 5 runes.
- UI library: Flowbite-Svelte.
- Styling: Tailwind CSS.
- Backend: FastAPI.
- Reverse proxy: Caddy.

# Package Managers and Commands

- Use `pnpm` for frontend dependencies and frontend scripts.
- Use `uv` and `.venv` for backend dependencies and backend scripts.
- Do not switch package managers unless the task explicitly requires it.

# Instruction Priority

1. Follow this `AGENTS.md`.
2. Follow relevant files in `docs/`.
3. Follow existing project patterns in code.
4. Ask follow-up questions when necessary.

# Core Principles

- Default to SSR-safe implementations.
- Reuse existing utilities, generated types, and shared clients.
- Keep implementations easy for a junior developer to maintain.
- Respect existing backend Clean Architecture / DDD boundaries without adding unnecessary abstraction.
- Add clear beginner-friendly comments in written code.
- Design for mobile-first layouts and interactions, but don't forget about desktop.
- Keep UI text concise and actionable.

# Required Reading Before Editing

- Read only documents relevant to the task.
- Read them before writing code or docs.
- Use `docs/api.md` for API integration, request types, and client usage.
- Use `docs/ssr.md` for loading, SSR behavior, browser-only APIs, and environment handling.
- Use `docs/ui.md` for components, layout, accessibility, copy, and UI states.

# Implementation 

- Prefer SSR-first data flows for initial content.
- Use Flowbite-Svelte components when they meet the requirement.
- Do not introduce custom visual patterns when an established project pattern exists.

# Tooling Workflow

## Available MCP Servers

### Svelte MCP Server

You have access to comprehensive Svelte 5 and SvelteKit documentation. Here's how to use the available tools effectively:

#### Available Tools:

**1. list-sections**

- Use this FIRST to discover all available documentation sections
- Returns a structured list with titles, use_cases, and paths
- When asked about Svelte or SvelteKit topics, ALWAYS use this tool at the start to find relevant sections

**2. get-documentation**

- Retrieves full documentation content for specific sections
- Accepts single or multiple sections
- After calling list-sections, you MUST analyze the returned documentation (especially the use_cases field) and then fetch ALL relevant sections for the user's task

**3. svelte-autofixer**

- Analyzes Svelte code and returns issues and suggestions
- You MUST use this tool whenever writing Svelte code before sending it to the user
- Keep calling it until no issues or suggestions are returned

**4. playground-link**

- Generates a Svelte Playground link with the provided code
- After completing the code, ask the user if they want a playground link
- NEVER call this if code was written to files in their project

### Flowbite-Svelte MCP Server

You have access to comprehensive Flowbite-Svelte component documentation. Here's how to use the available tools effectively:

#### Available Tools:

**1. findComponent**

- Use this FIRST to discover components by name or category
- Returns component information including the documentation path
- When asked about Flowbite-Svelte components, ALWAYS use this tool to locate the correct component before fetching documentation
- Example queries: 'Button', 'CardPlaceholder', 'form checkbox'

**2. getComponentList**

- Lists all available Flowbite-Svelte components with their categories
- Use this to discover what components are available or to help users explore component options

**3. getComponentDoc**

- Retrieves full documentation content for a specific component
- Accepts the component path found using findComponent
- After calling findComponent, use this tool to fetch complete documentation including usage examples, props, and best practices

**4. searchDocs**

- Performs full-text search across all Flowbite-Svelte documentation
- Use this when you need to find specific information that might span multiple components or when the user asks about features or patterns

## Workflow Guidelines

### When building Svelte components with Flowbite-Svelte:

1. **Start with Svelte documentation**: Use `list-sections` to understand which Svelte concepts are needed
2. **Fetch relevant Svelte docs**: Use `get-documentation` to get all necessary Svelte sections
3. **Find Flowbite-Svelte components**: Use `findComponent` to locate the UI components needed
4. **Get component details**: Use `getComponentDoc` to fetch usage examples and props
5. **Write the code**: Combine Svelte patterns with Flowbite-Svelte components
6. **Validate the code**: Use `svelte-autofixer` to check for issues
7. **Offer playground**: Ask if the user wants a playground link (only if not writing to files)

### Best Practices:

- Always prioritize Svelte 5 runes and modern patterns
- Use Flowbite-Svelte components for consistent UI design
- Validate all code with svelte-autofixer before delivering
- Keep documentation lookups efficient by fetching multiple sections at once

### Context7 MCP Server

Always use Context7 MCP when you need library/API documentation, code generation, setup or configuration steps without having to explicitly ask. Prefer MCP for Svelte and Flowbite.
