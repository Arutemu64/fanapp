import type { Mutation, QueryClient } from '@tanstack/svelte-query';

import { getApiErrorCode, gotNoApiAnswer } from '#lib/api/errors.js';
import {
	awardQuestPointsMutation,
	getSubscriptionsQueryKey,
	listQuestAwardsQueryKey,
	submitFeedbackMutation
} from '#lib/api/generated/@tanstack/svelte-query.gen.js';
import {
	deleteSubscription,
	type DeleteSubscriptionData,
	newSubscription,
	type NewSubscriptionData,
	type Options
} from '#lib/api/generated/index.js';

/**
 * The writes that wait out a lost connection instead of failing (ADR-0038):
 * each is safe to send twice — the award by its client ID (ADR-0034), the
 * subscription by its one-per-event key, the unsubscribe by its target — or,
 * for feedback, cheap to receive twice. Every other write stays online-only
 * (ADR-0022): a vote, a profile edit or a staff tool must answer while its
 * screen is still open.
 */
export const QUEUED_WRITES = {
	subscribe: ['newSubscription'],
	unsubscribe: ['deleteSubscription'],
	award: ['awardQuestPoints'],
	feedback: ['submitFeedback']
} as const;

export type QueuedWriteKind = keyof typeof QUEUED_WRITES;

const KIND_BY_KEY = new Map<string, QueuedWriteKind>(
	Object.entries(QUEUED_WRITES).map(([kind, [key]]) => [key, kind as QueuedWriteKind])
);

/** Which queued write a mutation is, or null for an online-only one. */
export function queuedWriteKind(mutation: Mutation): QueuedWriteKind | null {
	const [key] = mutation.options.mutationKey ?? [];
	return typeof key === 'string' ? (KIND_BY_KEY.get(key) ?? null) : null;
}

// A retry is a replay when the first attempt landed but its answer was lost
// (a gateway timeout, a dropped connection). The server then answers with the
// state already reached, which is the outcome the person asked for.

async function subscribe(variables: Options<NewSubscriptionData>) {
	try {
		const { data } = await newSubscription({ ...variables, throwOnError: true });
		return data;
	} catch (error) {
		if (getApiErrorCode(error) === 'SUBSCRIPTION_ALREADY_EXISTS') return null;
		throw error;
	}
}

async function unsubscribe(variables: Options<DeleteSubscriptionData>) {
	try {
		await deleteSubscription({ ...variables, throwOnError: true });
	} catch (error) {
		if (getApiErrorCode(error) === 'SUBSCRIPTION_NOT_FOUND') return;
		throw error;
	}
}

// Components build their mutation from these, so the key, and with it the
// defaults below, always match. They carry no `onSuccess`: an option set here
// would replace the default's invalidation for the mutations this screen sends.

// One scope per act, so its subscribe and unsubscribe go out in the order they
// were made: queued writes otherwise resume in parallel, and an unsubscribe that
// lands after a later subscribe would delete the reminder the person asked for.
// TanStack runs mutations that share a scope serially, and the scope is saved
// with a persisted write
// (https://tanstack.com/query/latest/docs/framework/react/guides/mutations#mutation-scopes).
function subscriptionScope(eventId: string) {
	return { id: `subscription:${eventId}` };
}

export function queuedSubscribeOptions(eventId: string) {
	return {
		mutationKey: QUEUED_WRITES.subscribe,
		mutationFn: subscribe,
		scope: subscriptionScope(eventId)
	};
}

export function queuedUnsubscribeOptions(eventId: string) {
	return {
		mutationKey: QUEUED_WRITES.unsubscribe,
		mutationFn: unsubscribe,
		scope: subscriptionScope(eventId)
	};
}

export function queuedAwardOptions() {
	return { ...awardQuestPointsMutation(), mutationKey: QUEUED_WRITES.award };
}

export function queuedFeedbackOptions() {
	return { ...submitFeedbackMutation(), mutationKey: QUEUED_WRITES.feedback };
}

/**
 * Register the queued writes' defaults. Call before the persisted cache is
 * restored: a write saved by an earlier visit comes back with its key and
 * variables only, and takes its `mutationFn` and invalidation from here
 * (https://tanstack.com/query/latest/docs/framework/react/guides/mutations#persisting-offline-mutations).
 */
export function registerQueuedWrites(queryClient: QueryClient): void {
	// `online`, not the app's `always`: offline (by the reachability probe that
	// drives onlineManager) the write pauses rather than failing, and fires on the
	// offline→online edge. A request that got no answer retries until one comes —
	// it pauses again once the probe confirms the outage — while an API error is
	// the server's verdict and fails at once.
	const queued = {
		networkMode: 'online',
		retry: (_failureCount: number, error: unknown) => gotNoApiAnswer(error)
	} as const;
	// Returned, so the write stays pending until the fresh list lands and a
	// queued subscription doesn't blink out between the two.
	const refreshSubscriptions = () =>
		queryClient.invalidateQueries({ queryKey: getSubscriptionsQueryKey() });

	queryClient.setMutationDefaults(QUEUED_WRITES.subscribe, {
		...queued,
		mutationFn: subscribe,
		onSuccess: refreshSubscriptions
	});
	queryClient.setMutationDefaults(QUEUED_WRITES.unsubscribe, {
		...queued,
		mutationFn: unsubscribe,
		onSuccess: refreshSubscriptions
	});
	queryClient.setMutationDefaults(QUEUED_WRITES.award, {
		...queued,
		...queuedAwardOptions(),
		onSuccess: () => queryClient.invalidateQueries({ queryKey: listQuestAwardsQueryKey() })
	});
	queryClient.setMutationDefaults(QUEUED_WRITES.feedback, {
		...queued,
		...queuedFeedbackOptions()
	});
}

/** Only waiting writes are saved: one in flight has already left the device. */
export function shouldPersistMutation(mutation: Mutation): boolean {
	return mutation.state.isPaused && queuedWriteKind(mutation) !== null;
}

/**
 * Drop every write still waiting. `Session` calls this when an account ends, so
 * the next person on a shared phone never sends the last one's writes.
 */
export function dropQueuedWrites(queryClient: QueryClient): void {
	const mutationCache = queryClient.getMutationCache();
	for (const mutation of mutationCache.getAll()) {
		if (queuedWriteKind(mutation) !== null && mutation.state.status === 'pending') {
			mutationCache.remove(mutation);
		}
	}
}

/** Cancel a subscription not yet sent; false if it is in flight or may have landed. */
export function cancelQueuedSubscribe(queryClient: QueryClient, eventId: string): boolean {
	const mutationCache = queryClient.getMutationCache();
	const queued = mutationCache
		.findAll({ mutationKey: QUEUED_WRITES.subscribe })
		.find((mutation) => {
			const variables = mutation.state.variables as Options<NewSubscriptionData> | undefined;
			// Never attempted: one that failed may have landed with its answer lost,
			// and dropping it would leave that reminder on the server.
			const neverSent = mutation.state.isPaused && mutation.state.failureCount === 0;
			return neverSent && variables?.body.event_id === eventId;
		});
	if (!queued) return false;
	mutationCache.remove(queued);
	return true;
}

export type QueuedWriteOutcome =
	{ kind: QueuedWriteKind; ok: true } | { kind: QueuedWriteKind; ok: false; error: unknown };

/**
 * Report how each write that waited in the queue ended. A screen hands a write
 * to the queue once it pauses (`handOffWhenQueued`), and it may be long gone —
 * or the app restarted — by the time the write is sent, so the outcome is told
 * from here rather than by the screen. Call once from the root layout; returns
 * the teardown.
 */
export function watchQueuedWrites(
	queryClient: QueryClient,
	report: (outcome: QueuedWriteOutcome) => void
): () => void {
	const mutationCache = queryClient.getMutationCache();
	const waited = new WeakSet<Mutation>();

	function noteIfWaiting(mutation: Mutation) {
		if (shouldPersistMutation(mutation)) waited.add(mutation);
	}

	// Writes restored from an earlier visit are already waiting.
	for (const mutation of mutationCache.getAll()) noteIfWaiting(mutation);

	return mutationCache.subscribe((event) => {
		if (event.type !== 'added' && event.type !== 'updated') return;
		// The cache event types its mutation with `any` generics.
		const mutation = event.mutation as Mutation;
		noteIfWaiting(mutation);
		if (event.type !== 'updated' || !waited.has(mutation)) return;

		const kind = queuedWriteKind(mutation);
		if (kind === null) return;
		if (event.action.type === 'success') report({ kind, ok: true });
		if (event.action.type === 'error') report({ kind, ok: false, error: event.action.error });
	});
}
