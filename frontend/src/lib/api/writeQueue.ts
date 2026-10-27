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
import { trackEvent } from '#lib/services/analytics.js';

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

export function queuedWriteKind(mutation: Mutation): QueuedWriteKind | null {
	const [key] = mutation.options.mutationKey ?? [];
	return typeof key === 'string' ? (KIND_BY_KEY.get(key) ?? null) : null;
}

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

export function registerQueuedWrites(queryClient: QueryClient): void {
	const queued = {
		networkMode: 'online',
		retry: (_failureCount: number, error: unknown) => gotNoApiAnswer(error)
	} as const;
	const refreshSubscriptions = () =>
		queryClient.invalidateQueries({ queryKey: getSubscriptionsQueryKey() });

	// Defaults also run for writes replayed after a reload, so the events are tracked here.
	queryClient.setMutationDefaults(QUEUED_WRITES.subscribe, {
		...queued,
		mutationFn: subscribe,
		onSuccess: () => {
			trackEvent('event-subscribe');
			return refreshSubscriptions();
		}
	});
	queryClient.setMutationDefaults(QUEUED_WRITES.unsubscribe, {
		...queued,
		mutationFn: unsubscribe,
		onSuccess: () => {
			trackEvent('event-unsubscribe');
			return refreshSubscriptions();
		}
	});
	queryClient.setMutationDefaults(QUEUED_WRITES.award, {
		...queued,
		...queuedAwardOptions(),
		onSuccess: () => queryClient.invalidateQueries({ queryKey: listQuestAwardsQueryKey() })
	});
	queryClient.setMutationDefaults(QUEUED_WRITES.feedback, {
		...queued,
		...queuedFeedbackOptions(),
		onSuccess: () => trackEvent('feedback-send')
	});
}

export function shouldPersistMutation(mutation: Mutation): boolean {
	return mutation.state.isPaused && queuedWriteKind(mutation) !== null;
}

export function dropQueuedWrites(queryClient: QueryClient): void {
	const mutationCache = queryClient.getMutationCache();
	for (const mutation of mutationCache.getAll()) {
		if (queuedWriteKind(mutation) !== null && mutation.state.status === 'pending') {
			mutationCache.remove(mutation);
		}
	}
}

export function cancelQueuedSubscribe(queryClient: QueryClient, eventId: string): boolean {
	const mutationCache = queryClient.getMutationCache();
	const queued = mutationCache
		.findAll({ mutationKey: QUEUED_WRITES.subscribe })
		.find((mutation) => {
			const variables = mutation.state.variables as Options<NewSubscriptionData> | undefined;
			const neverSent = mutation.state.isPaused && mutation.state.failureCount === 0;
			return neverSent && variables?.body.event_id === eventId;
		});
	if (!queued) return false;
	mutationCache.remove(queued);
	return true;
}

export type QueuedWriteOutcome =
	{ kind: QueuedWriteKind; ok: true } | { kind: QueuedWriteKind; ok: false; error: unknown };

export function watchQueuedWrites(
	queryClient: QueryClient,
	report: (outcome: QueuedWriteOutcome) => void
): () => void {
	const mutationCache = queryClient.getMutationCache();
	const waited = new WeakSet<Mutation>();

	function noteIfWaiting(mutation: Mutation) {
		if (shouldPersistMutation(mutation)) waited.add(mutation);
	}

	for (const mutation of mutationCache.getAll()) noteIfWaiting(mutation);

	return mutationCache.subscribe((event) => {
		if (event.type !== 'added' && event.type !== 'updated') return;
		const mutation = event.mutation as Mutation;
		noteIfWaiting(mutation);
		if (event.type !== 'updated' || !waited.has(mutation)) return;

		const kind = queuedWriteKind(mutation);
		if (kind === null) return;
		if (event.action.type === 'success') report({ kind, ok: true });
		if (event.action.type === 'error') report({ kind, ok: false, error: event.action.error });
	});
}
