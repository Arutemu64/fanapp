# ADR-0033: A hand-written IndexedDB persister, without JSON

- **Status:** Accepted
- **Date:** 2026-10-16
- **Deciders:** Project maintainers

## Context

[ADR-0021](0021-tanstack-query-for-server-state.md) persists the offline
queries with `persistQueryClient` and `createAsyncStoragePersister` over
`idb-keyval`. That persister serializes the whole client with `JSON.stringify`
on every save and types its storage as `AsyncStorage<string>`, so it cannot
hand IndexedDB an object. IndexedDB stores values by structured clone, and
TanStack's docs say it "doesn't require serialization", giving an IndexedDB
persister written directly against the `Persister` interface as the example
([persistQueryClient, "Building a Persister"](https://tanstack.com/query/latest/docs/framework/react/plugins/persistQueryClient#building-a-persister)).

The JSON round-trip cost two things. ADR-0021 keeps a query that failed its
refetch but still holds data, and an `Error` in its state came back as `{}`.
It also re-stringified the whole programme on each save. Its key,
`REACT_QUERY_OFFLINE_CACHE`, was the package default, which the diagnostics
reset had to repeat as a literal to delete the entry.

## Decision

We will persist through `createIdbPersister` in `#lib/api/queryPersister.ts`,
which follows TanStack's example: `set`/`get`/`del` from `idb-keyval`, the
client stored as an object, a trailing 1s throttle (the throttle
`createAsyncStoragePersister` provided), and a failed write reported to
Sentry. The entry is named by an exported `QUERY_CACHE_KEY`
(`fanfan-query-cache`), and the diagnostics reset deletes it through that
constant. `@tanstack/query-async-storage-persister` is removed.

Everything else in ADR-0021 stands: the allowlist, `maxAge`, the `buster`, and
the restore before the guards.

## Consequences

- An `Error` or `Date` in a saved query survives a restart, and a save no
  longer builds a JSON string.
- A value structured clone rejects (a function, a `Headers`) fails the write,
  where JSON would have dropped it silently. The failure goes to Sentry and the
  previous save stays. Query keys and API data are plain objects today.
- The old key is deleted on boot. Each deploy busts the cache anyway, so
  renaming loses no data a client could still use. The cleanup is a `TODO` to
  drop later.
- We own about 20 lines that the package used to cover.

## Alternatives considered

- **Pass identity `serialize`/`deserialize` to `createAsyncStoragePersister`.**
  Rejected: its options are typed to `string`, so this needs a cast that lies
  about the stored type, and the next reader can't trust the types.
- **Keep the JSON default.** Rejected for the error loss and save cost above.
