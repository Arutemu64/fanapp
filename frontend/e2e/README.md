# Frontend E2E (Playwright)

End-to-end tests that drive the **real production build** in a browser with the
backend **mocked per test**. This is the tier that covers what Vitest cannot
(ADR-0011, node-only): SPA routing and guards, the service worker, offline / PWA
behaviour, and DOM interactions. Backend behaviour itself is already covered by
the `@pytest.mark.integration` suite, and the frontend↔backend contract by the
OpenAPI drift guards (`test_openapi_spec.py` + `frontend-check-api`) — so here we
mock, and keep these tests about the UI. See [docs/testing.md](../../docs/testing.md).

## Running

```sh
just frontend-e2e        # headless
just frontend-e2e-ui     # Playwright UI, for debugging a spec (local)
```

The config builds the app and serves it with `vite preview` automatically — a
production build is required because the service worker and offline caching are
inert in `vite dev` (docs/frontend.md §2).

**Browser:** in a Claude Code web session the pre-baked Chromium is used with no
install — `@playwright/test` is pinned to the version whose Chromium build matches
it. On CI / a fresh laptop, install it once:

```sh
pnpm --dir frontend exec playwright install chromium
```

> Bumping `@playwright/test` is deliberate: keep it on the line whose Chromium
> build the web environment pre-bakes, or a session falls back to the
> `$PLAYWRIGHT_BROWSERS_PATH/chromium` symlink instead of a matched build. See the
> note in `playwright.config.ts`.

## Writing a spec

Import from `../fixtures` (not `@playwright/test`) — it injects the mocked
backend as `api` and re-exports the persona/SSE helpers.

```ts
import type { ApiSchemas } from '../fixtures';

import { expect, json, test } from '../fixtures';

test('closed voting shows the closed banner', async ({ page, api }) => {
	api.use({
		'GET /voting/status': json<ApiSchemas['GetVotingStateOutput']>({
			can_vote: false,
			status: 'disabled',
			voting_start: null,
			voting_end: null
		}),
		'GET /voting/nominations': json<ApiSchemas['ListVotingNominationsOutput']>({ nominations: [] })
	});
	await page.goto('/voting');
	await expect(page.getByText('Голосование сейчас закрыто.')).toBeVisible();
	expect(api.unmatched).toEqual([]); // no endpoint went unmocked
});
```

See `specs/voting.spec.ts`, `specs/offline.spec.ts` and `specs/realtime.spec.ts`
for the closed/open, offline and SSE patterns respectively.

### How mocking works

- One catch-all route over `**/api/**` (`mocks/api.ts`). A registry maps
  `"<METHOD> <path>"` (path **without** `/api`, **with** the trailing slash the
  OpenAPI spec uses — `"GET /me/"`) to a response.
- `mocks/defaults.ts` pre-mocks the **boot-critical** endpoints (`/me/`,
  `/config`, `/debug/health`, `/schedule/`, …) as a logged-out guest. Every test
  starts from this baseline.
- `api.use({ … })` overrides or adds routes for one test; last write wins.
- **Type your bodies** with `json<ApiSchemas['SomeDTO']>({ … })` so a mock that
  drifts from the real contract fails to compile.
- An endpoint nobody mocked returns a **loud 404** and lands in `api.unmatched`.
  Assert `api.unmatched` is empty, or add the missing route.
- **Never inline a large payload in a spec** — put reusable fixtures in `mocks/`.

### Personas (auth)

The session is an HttpOnly cookie JS can't forge, so auth is faked by mocking
`/me/`, not by a real login. `loggedInAs(overrides)` / `organizer()`
(`mocks/personas.ts`) return handlers you layer with `api.use(...)`. Flows that
must exercise the **real** cookie/login handshake belong in a full-stack run, not
here.

### Offline / network failure

The app's offline states are driven by failed requests and the reachability probe,
not `navigator.onLine`. **Simulate a dead network by aborting the reads** — a
mocked route still _fulfils_ under `context.setOffline(true)`, so aborting is what
actually reaches the offline path:

```ts
api.use({ 'GET /voting/nominations': (route) => route.abort() });
await page.goto('/voting');
await expect(page.getByText('Голосование доступно только онлайн')).toBeVisible();
```

The build ships a real service worker, so a cache-backed page can also be tested
across a genuine online→offline edge (load online to populate the cache, then
fail the reads and reload to assert the stale notice) — that's the tier only a
real build reaches.

### Realtime (SSE)

`EventSource` is replaced by a controllable double (`mocks/sse.ts`) — the app
never opens a live `/events` stream. Push an event and assert the UI reacts:

```ts
import { emitSse } from '../fixtures';
await emitSse(page, 'schedule_updated', {});
```

## Layout

```
e2e/
  fixtures.ts        # test/expect + `api` fixture; re-exports helpers — import from here
  mocks/
    api.ts           # ApiMock: catch-all route registry + json() helper + ApiSchemas
    defaults.ts      # baseline (guest) boot handlers
    personas.ts      # loggedInAs() / organizer() / user()
    sse.ts           # EventSource double + emitSse()
  specs/             # *.spec.ts live here
  tsconfig.json
```
