/**
 * TanStack Query bindings for every API operation, generated from the same
 * OpenAPI spec as the SDK (`openapi-ts.config.ts`, `@tanstack/svelte-query`
 * plugin): `<operation>Options()`, `<operation>QueryKey()`,
 * `<operation>Mutation()` and `<operation>InfiniteOptions()` where the operation
 * paginates.
 *
 * Re-exported here so callers import from `$lib/api/queries` rather than reaching
 * into the generated `@tanstack/` folder, whose path is an implementation detail
 * of the generator. Always pass the context client — `getScheduleOptions({ client })`
 * — so the query key carries the same `baseUrl` everywhere (see `api/context.ts`).
 */
export * from './generated/@tanstack/svelte-query.gen';
