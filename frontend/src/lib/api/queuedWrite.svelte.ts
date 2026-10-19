import { useMutationState } from '@tanstack/svelte-query';
import { untrack } from 'svelte';

import type { QueuedSubscriptionChanges } from '#lib/utils/scheduleData.js';

import {
	type DeleteSubscriptionData,
	type NewSubscriptionData,
	type Options
} from '#lib/api/generated/index.js';
import { QUEUED_WRITES } from '#lib/api/writeQueue.js';

/**
 * Hand a write to the queue (`writeQueue.ts`) once it pauses for want of a
 * connection: `onQueued` tells the person it will go out later and lets the
 * screen move on (close the dialog, clear the form), and the mutation is
 * detached from this screen. It keeps waiting in the cache, and the root
 * layout's queue watcher reports how it ends, so the screen's own success and
 * error callbacks never run for it — the person hears the outcome once, wherever
 * they are by then. Call during component init.
 */
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

/**
 * The viewer's subscription writes still pending — waiting in the queue or in
 * flight — for `mergeSubscriptions` to lay over the server's list. Call during
 * component init.
 */
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
