import { useMutationState } from '@tanstack/svelte-query';
import { untrack } from 'svelte';

import type {
	DeleteSubscriptionData,
	NewSubscriptionData,
	Options
} from '#lib/api/generated/index.js';
import type { QueuedSubscriptionChanges } from '#lib/utils/scheduleData.js';

import { QUEUED_WRITES } from '#lib/api/writeQueue.js';

export function handOffWhenQueued(
	mutation: { readonly isPaused: boolean; reset: () => void },
	onQueued: () => void
): void {
	$effect(() => {
		if (!mutation.isPaused) return;
		untrack(onQueued);
		mutation.reset();
	});
}

export function useQueuedSubscriptionChanges(): QueuedSubscriptionChanges {
	const subscribing = useMutationState({
		filters: { mutationKey: QUEUED_WRITES.subscribe, status: 'pending' },
		select: (mutation) => (mutation.state.variables as Options<NewSubscriptionData>).body
	});
	const unsubscribing = useMutationState({
		filters: { mutationKey: QUEUED_WRITES.unsubscribe, status: 'pending' },
		select: (mutation) =>
			(mutation.state.variables as Options<DeleteSubscriptionData>).path.subscription_id
	});
	return {
		get subscribing() {
			return subscribing;
		},
		get unsubscribing() {
			return unsubscribing;
		}
	};
}
