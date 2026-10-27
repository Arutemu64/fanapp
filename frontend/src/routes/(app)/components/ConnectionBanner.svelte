<script lang="ts">
	import CircleAlert from '@lucide/svelte/icons/circle-alert';
	import CircleCheck from '@lucide/svelte/icons/circle-check';
	import { useIsFetching, useMutationState } from '@tanstack/svelte-query';
	import { untrack } from 'svelte';
	import { slide } from 'svelte/transition';

	import { shouldPersistMutation } from '#lib/api/writeQueue.js';
	import { Button } from '#lib/components/ui/button/index.js';
	import { Spinner } from '#lib/components/ui/spinner/index.js';
	import { m } from '#lib/paraglide/messages.js';
	import { probeReachability, reachability } from '#lib/services/reachability.js';

	const MIN_DISPLAY_MS = 4000;
	const RESTORED_DISPLAY_MS = 3000;

	let isOnline = $derived(reachability.current);
	let deviceOnline = $derived(reachability.deviceOnline);

	let offlineMessage = $derived.by(() => {
		if (isOnline) return null;
		return deviceOnline ? m.connection_no_server() : m.connection_no_internet();
	});

	let phase = $state<'hidden' | 'offline' | 'catching-up' | 'restored'>('hidden');
	let lastOfflineMessage = $state('');
	let offlineHoldUntil = 0;
	let retrying = $state(false);

	const fetchingOnScreen = useIsFetching({ type: 'active' });

	const queuedWrites = useMutationState({
		filters: { predicate: shouldPersistMutation }
	});
	let queuedLabel = $derived(
		phase === 'offline' && queuedWrites.length > 0
			? m.connection_queued({ count: queuedWrites.length })
			: ''
	);

	let shownMessage = $derived.by(() => {
		if (phase === 'offline') return lastOfflineMessage;
		if (phase === 'catching-up') return m.connection_updating();
		if (phase === 'restored') return m.connection_restored();
		return '';
	});

	$effect(() => {
		const message = offlineMessage;

		if (message) {
			lastOfflineMessage = message;
			phase = 'offline';
			offlineHoldUntil = Date.now() + MIN_DISPLAY_MS;
			return;
		}

		if (untrack(() => phase) !== 'offline') return;

		const holdTimeoutId = setTimeout(
			() => (phase = 'catching-up'),
			Math.max(0, offlineHoldUntil - Date.now())
		);
		return () => clearTimeout(holdTimeoutId);
	});

	$effect(() => {
		if (phase === 'catching-up' && fetchingOnScreen.current === 0) phase = 'restored';
	});

	$effect(() => {
		if (phase !== 'restored') return;
		const hideTimeoutId = setTimeout(() => (phase = 'hidden'), RESTORED_DISPLAY_MS);
		return () => clearTimeout(hideTimeoutId);
	});

	async function handleRetry() {
		retrying = true;
		try {
			await probeReachability();
		} finally {
			retrying = false;
		}
	}
</script>

<div role="status" class="sr-only">{shownMessage} {queuedLabel}</div>

{#if phase !== 'hidden'}
	<div
		transition:slide={{ duration: 200 }}
		class={[
			'flex min-h-11 items-center gap-2.5 border-b px-4 py-2 text-sm sm:px-6',
			phase === 'offline' && 'border-warning/30 bg-warning/10 text-warning',
			phase === 'catching-up' && 'border-info/30 bg-info/10 text-info',
			phase === 'restored' && 'border-success/30 bg-success/10 text-success'
		]}
	>
		{#if phase === 'offline'}
			<CircleAlert class="size-4 shrink-0" aria-hidden="true" />
		{:else if phase === 'catching-up'}
			<Spinner class="shrink-0" aria-hidden="true" />
		{:else}
			<CircleCheck class="size-4 shrink-0" aria-hidden="true" />
		{/if}
		<p class="flex-1 leading-snug" aria-hidden="true">
			{shownMessage}
			{#if queuedLabel}
				<span class="block text-xs opacity-80">{queuedLabel}</span>
			{/if}
		</p>
		{#if phase === 'offline'}
			<Button
				variant="ghost"
				size="sm"
				class="-my-1.5 shrink-0"
				disabled={retrying}
				onclick={handleRetry}
			>
				{#if retrying}
					<Spinner data-icon="inline-start" aria-hidden="true" />
				{/if}
				{m.common_retry()}
			</Button>
		{/if}
	</div>
{/if}
