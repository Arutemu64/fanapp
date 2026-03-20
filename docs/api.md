# API Integration Rules

## Goal

Keep API usage type-safe, SSR-compatible, and consistent across the frontend.

## Source of Truth

- This project uses `openapi-typescript` to generate API types and `openapi-fetch` for the shared typed client.
- Treat `frontend/src/lib/api/v1.d.ts` as the only source of truth for API shapes.
- Do not define new API data structures from scratch when the generated schema already covers them.
- If a reusable local alias is needed, define it under `frontend/src/lib/types`.

## Generation

- Run `pnpm generate-api` from `frontend/` when `shared/openapi/openapi.json` changes.
- Keep custom OpenAPI transforms in `frontend/scripts/generate-api.mjs`.
- Preserve the `Blob` transform for file upload fields emitted as `format: binary` or `contentMediaType`.

## Client Usage

- Use the shared API client from `frontend/src/lib/api/index.ts`, imported through `$lib/api`.
- Reuse `client` in browser or universal code when no request-specific client setup is needed.
- Use `createApiClient()` in server code when you need a fresh client instance for request-aware calls.
- Do not introduce a second API client without a strong architectural reason.

## SSR Requirements

- In SvelteKit load functions, hooks, actions, or other SSR-aware contexts, use the framework-provided `fetch` or `event.fetch`.
- Pass that `fetch` into the API client call so cookies, `handleFetch`, relative URLs, and server rendering behave correctly.
- Prefer loading initial page data on the server when it affects first render.

## Response Handling

- `openapi-fetch` results expose `data`, `error`, and `response`. Check them before consuming payload fields.
- Treat success payload, error payload, and response metadata as separate concerns.
- Do not assume `data` exists when `error` is present or the response is not successful.

## Error Handling

- Log or normalize API failures before presenting them to the user.
- Show user-friendly Russian messages in the UI.
- Never expose raw backend error payloads, internal identifiers, or stack traces to users.
- Define how the UI recovers after a failed request.

## Type Safety

- Let generated request and response types drive implementation details.
- Prefer narrowing and composition over manual duplication of schema fields.
- Keep type aliases descriptive and close to the feature that uses them.

## Mutation Rules

- After every mutation, define how the UI becomes consistent again.
- Prefer one clear strategy per action: refresh, invalidate, local reconciliation, or optimistic update with rollback.
- If a page load declares `depends(...)`, invalidate the matching dependency after a successful mutation when appropriate.
- Do not leave stale page state after a successful write.

## Review Checklist

- Generated API types are used everywhere relevant.
- Shared client usage is preserved.
- SSR contexts use the provided `fetch`.
- Success, loading, and failure paths are all handled.
- User-visible error text is in Russian and safe to expose.
