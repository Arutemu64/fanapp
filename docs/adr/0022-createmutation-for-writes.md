# ADR-0022: `createMutation` for writes, online-only

- **Status:** Accepted
- **Date:** 2026-10-13
- **Deciders:** Project maintainers

## Context

ADR-0021 moved reads to TanStack Query but left writes as plain SDK calls in
event handlers: `await sdkCall()`, check `error`, then `invalidateQueries`.
Each handler kept its own busy flag (`isSubmitting`, `isLoading`,
`activeAction`), and some had none. An audit found two bugs that came from
this pattern:

- The subscribe and unsubscribe dialogs had no busy flag, so a double-tap sent
  two requests.
- A vote cleared its optimistic count before the ballot refetch landed, and the
  `onVoted` callback was typed `() => void` and never awaited. For one
  round-trip the count dropped back and the vote button came back.

TanStack's mutation API covers both. `isPending` is the busy flag, and an
`onSuccess` that returns the invalidation keeps the mutation pending until the
refetch has landed
([Mutations](https://tanstack.com/query/latest/docs/framework/react/guides/mutations),
[TkDodo, "Mastering Mutations"](https://tkdodo.eu/blog/mastering-mutations-in-react-query)).
hey-api already generated a `…Mutation()` options factory for every write. No
code used them.

## Decision

We will make every user-triggered write a `createMutation` built from the
generated options. Its invalidation goes in the mutation's own callbacks:

```ts
const subscribeMutation = createMutation(() => ({
  ...newSubscriptionMutation(),
  onSuccess: () =>
    queryClient.invalidateQueries({ queryKey: getSubscriptionsQueryKey() }),
}));
```

- **Mutations never pause offline.** The root `QueryClient` sets
  `defaultOptions.mutations.networkMode: 'always'`. In TanStack's default
  `online` mode a mutation does not fire while `onlineManager` reports offline,
  and it fires later when the connection returns
  ([network mode](https://tanstack.com/query/latest/docs/framework/react/guides/network-mode)).
  Our reachability probe drives `onlineManager`, so a write could otherwise go
  out minutes later, unseen. Writes stay online-only: they fail at once with the
  connection message. Retries stay at TanStack's default of none.
- **Essential work goes on the mutation; UI work goes on the call.** Invalidation
  lives in `createMutation`'s callbacks, which run even after the component
  unmounts. Toasts, closing a dialog and form errors go in `mutate(vars, { … })`
  callbacks, which TanStack skips once the component has unmounted. A toast that
  must survive the refetch removing its component goes on the mutation instead.
- **Return the invalidation by default.** The mutation then stays pending until
  the fresh data arrives. Use `void` when the refetch would change the open
  dialog's own content (password, email), or when it is heavy and the action
  doesn't need it first (schedule edits, settings).
- **`mutate` by default, `mutateAsync` for sequencing.** `mutateAsync` is used
  when the caller needs a promise: a browser-API flow (push subscribe), a child
  that awaits the action (unlinking a provider), or calls that overlap (sync
  sources). `mutate` only runs the callbacks of its latest call.
- **Forms keep their own error state.** A form sets `formError` in `onError`
  rather than deriving it from `mutation.error`, because forms mix client-side
  and API errors and clear them on input. The mutation supplies `isPending`.
- **Errors are thrown bodies.** The generated `mutationFn` calls the SDK with
  `throwOnError: true`, so `onError` receives the API error body (or the
  `fetch` TypeError), the same as `query.error`. It carries no HTTP status, so
  branches match on `getApiErrorCode`.

Plain SDK calls stay where no component makes the request: the queued offline
logout flush (`pendingLogout.ts`), and notifications read-on-view, a background
sync with its own retry bookkeeping. `checkSubscription` stays a plain GET: it
is one step of the browser's push-subscription check and feeds local state, not
the cache.

## Consequences

- A write button can't double-fire without someone removing its `isPending`
  guard on purpose.
- Callbacks that the component passed down only to invalidate after a write
  (`onUpdate`, `onSettingsUpdate`, `onTicketLinked`) are gone. The component
  that writes invalidates.
- One footgun belongs to the Svelte adapter. Reading any property of a mutation
  result reads all of them. So `mutation.reset()` inside an `$effect` subscribes
  that effect to the whole mutation state, and the effect re-runs, and resets
  the mutation, on every change. Call it from an event handler, or wrap it in
  `untrack`.
- Finished mutations stay in the in-memory `MutationCache` for 5 minutes,
  variables included. The persister only dehydrates paused mutations, and with
  `networkMode: 'always'` none pause, so nothing reaches IndexedDB.

## Alternatives considered

- **Keep plain SDK calls and add busy flags where missing.** Rejected. It fixes
  the two bugs one site at a time and leaves the next form to remember the flag.
- **Global invalidation via `MutationCache` + `meta.invalidates`**
  ([TkDodo](https://tkdodo.eu/blog/automatic-query-invalidation-after-mutations)).
  Rejected. About 25 call sites read more clearly with explicit keys, and SSE
  already keeps other clients current.
- **Offline-queued mutations (`setMutationDefaults` + `resumePausedMutations`).**
  Rejected. A write replayed after the moment has passed (a vote after voting
  closed, a "now on stage" mark an act later) is worse than a clear "only
  online" state.
