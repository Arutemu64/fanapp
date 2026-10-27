import { MutationObserver, onlineManager, QueryClient } from '@tanstack/svelte-query';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { droppedConnectionError } from '#lib/testing/connection.js';

import {
	cancelQueuedSubscribe,
	dropQueuedWrites,
	queuedSubscribeOptions,
	queuedUnsubscribeOptions,
	type QueuedWriteOutcome,
	registerQueuedWrites,
	shouldPersistMutation,
	watchQueuedWrites
} from './writeQueue';

const { deleteSubscription, newSubscription } = vi.hoisted(() => ({
	deleteSubscription: vi.fn(),
	newSubscription: vi.fn()
}));
vi.mock('#lib/api/generated/index.js', async (importOriginal) => ({
	...(await importOriginal<object>()),
	deleteSubscription,
	newSubscription
}));

const SUBSCRIBE = { body: { event_id: 'event-1', lead_minutes: 15 } };

function subscribeObserver(queryClient: QueryClient) {
	return new MutationObserver(queryClient, queuedSubscribeOptions('event-1'));
}

function pendingWrites(queryClient: QueryClient) {
	return queryClient.getMutationCache().findAll({ status: 'pending' });
}

describe('write queue', () => {
	let queryClient: QueryClient;

	beforeEach(() => {
		queryClient = new QueryClient({ defaultOptions: { mutations: { networkMode: 'always' } } });
		registerQueuedWrites(queryClient);
		queryClient.mount();
		newSubscription.mockResolvedValue({ data: { subscription_id: 'sub-1' } });
	});

	afterEach(() => {
		queryClient.unmount();
		onlineManager.setOnline(true);
		vi.clearAllMocks();
	});

	it('waits offline, is saved, and goes out when the connection returns', async () => {
		onlineManager.setOnline(false);
		void subscribeObserver(queryClient).mutate(SUBSCRIBE);
		await vi.waitFor(() => expect(pendingWrites(queryClient)).toHaveLength(1));

		const [waiting] = pendingWrites(queryClient);
		expect(waiting?.state.isPaused).toBe(true);
		expect(waiting && shouldPersistMutation(waiting)).toBe(true);
		expect(newSubscription).not.toHaveBeenCalled();

		onlineManager.setOnline(true);
		await vi.waitFor(() => expect(pendingWrites(queryClient)).toHaveLength(0));
		expect(newSubscription).toHaveBeenCalledOnce();
	});

	it('pauses a write that got no answer instead of failing it', async () => {
		newSubscription.mockRejectedValueOnce(await droppedConnectionError());
		const sent = subscribeObserver(queryClient).mutate(SUBSCRIBE);
		await vi.waitFor(() => expect(newSubscription).toHaveBeenCalledOnce());
		onlineManager.setOnline(false);

		onlineManager.setOnline(true);
		await expect(sent).resolves.toEqual({ subscription_id: 'sub-1' });
	});

	it('counts a replayed subscribe the server already has as done', async () => {
		newSubscription.mockRejectedValueOnce({ code: 'SUBSCRIPTION_ALREADY_EXISTS' });

		await expect(subscribeObserver(queryClient).mutate(SUBSCRIBE)).resolves.toBeNull();
	});

	it('cancels a queued subscribe that has not left yet', async () => {
		onlineManager.setOnline(false);
		void subscribeObserver(queryClient).mutate(SUBSCRIBE);
		await vi.waitFor(() => expect(pendingWrites(queryClient)).toHaveLength(1));

		expect(cancelQueuedSubscribe(queryClient, 'other-event')).toBe(false);
		expect(cancelQueuedSubscribe(queryClient, 'event-1')).toBe(true);
		expect(pendingWrites(queryClient)).toHaveLength(0);
	});

	it('drops waiting writes when the account ends', async () => {
		onlineManager.setOnline(false);
		void subscribeObserver(queryClient).mutate(SUBSCRIBE);
		await vi.waitFor(() => expect(pendingWrites(queryClient)).toHaveLength(1));

		dropQueuedWrites(queryClient);
		onlineManager.setOnline(true);

		expect(pendingWrites(queryClient)).toHaveLength(0);
		expect(newSubscription).not.toHaveBeenCalled();
	});

	it('reports the outcome of a write that waited, and only that one', async () => {
		const outcomes: QueuedWriteOutcome[] = [];
		const stop = watchQueuedWrites(queryClient, (outcome) => outcomes.push(outcome));

		await subscribeObserver(queryClient).mutate(SUBSCRIBE);
		expect(outcomes).toEqual([]);

		onlineManager.setOnline(false);
		void subscribeObserver(queryClient).mutate(SUBSCRIBE);
		await vi.waitFor(() => expect(pendingWrites(queryClient)).toHaveLength(1));
		onlineManager.setOnline(true);

		await vi.waitFor(() => expect(outcomes).toEqual([{ kind: 'subscribe', ok: true }]));
		stop();
	});

	it("sends one act's unsubscribe and resubscribe in the order they were made", async () => {
		const sent: string[] = [];
		deleteSubscription.mockImplementation(async () => {
			await new Promise((resolve) => setTimeout(resolve, 20));
			sent.push('unsubscribe');
			return { data: undefined };
		});
		newSubscription.mockImplementation(() => {
			sent.push('subscribe');
			return Promise.resolve({ data: { subscription_id: 'sub-2' } });
		});

		onlineManager.setOnline(false);
		void new MutationObserver(queryClient, queuedUnsubscribeOptions('event-1')).mutate({
			path: { subscription_id: 'sub-1' }
		});
		void subscribeObserver(queryClient).mutate(SUBSCRIBE);
		await vi.waitFor(() => expect(pendingWrites(queryClient)).toHaveLength(2));

		onlineManager.setOnline(true);
		await vi.waitFor(() => expect(sent).toEqual(['unsubscribe', 'subscribe']));
	});

	it('keeps a subscribe that may have landed instead of cancelling it', async () => {
		newSubscription.mockRejectedValueOnce(await droppedConnectionError());
		vi.useFakeTimers();
		try {
			void subscribeObserver(queryClient).mutate(SUBSCRIBE);
			await vi.advanceTimersByTimeAsync(0);
			expect(newSubscription).toHaveBeenCalledOnce();
			onlineManager.setOnline(false);
			await vi.advanceTimersByTimeAsync(1000);
			expect(pendingWrites(queryClient)[0]?.state.isPaused).toBe(true);

			expect(cancelQueuedSubscribe(queryClient, 'event-1')).toBe(false);
		} finally {
			vi.useRealTimers();
		}
	});
});
