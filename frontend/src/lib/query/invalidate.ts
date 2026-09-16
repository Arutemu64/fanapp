import type { QueryClient } from '@tanstack/svelte-query';

/**
 * Named invalidations for the cached read surfaces, so a mutation or an SSE event
 * says *what changed* instead of repeating a generated key at every call site.
 * These replace the `invalidate('app:…')` dependency keys those pages used while
 * their data came from a `load`.
 *
 * Each matches on the operation id alone. The generated keys are
 * `[{ _id, baseUrl, query?, path? }]` and TanStack matches object keys
 * partially, so this covers every variant of an operation — the notification feed
 * requested at two different page sizes, or the same operation keyed against a
 * differently configured client — without the caller reconstructing the exact key.
 *
 * A query nobody is watching is only marked stale, so these are cheap to call
 * from a page that doesn't render the affected surface.
 */
function invalidateOperation(queryClient: QueryClient, operationId: string): Promise<void> {
	return queryClient.invalidateQueries({ queryKey: [{ _id: operationId }] });
}

/** The public programme itself (an event moved, marked current, or re-imported). */
export function invalidateSchedule(queryClient: QueryClient): Promise<void> {
	return invalidateOperation(queryClient, 'getSchedule');
}

/** The viewer's own event subscriptions — the bell badges on the schedule rows. */
export function invalidateSubscriptions(queryClient: QueryClient): Promise<void> {
	return invalidateOperation(queryClient, 'getSubscriptions');
}

/** The notification feed, at every page size it has been requested with. */
export function invalidateNotifications(queryClient: QueryClient): Promise<void> {
	return invalidateOperation(queryClient, 'listUserNotifications');
}

/** Festival phase and countdown (the home hero, after an organizer edits the dates). */
export function invalidateConfig(queryClient: QueryClient): Promise<void> {
	return invalidateOperation(queryClient, 'getPublicConfig');
}
