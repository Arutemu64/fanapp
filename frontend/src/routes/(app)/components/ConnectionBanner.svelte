<script lang="ts">
	import CircleAlert from '@lucide/svelte/icons/circle-alert';
	import CircleCheck from '@lucide/svelte/icons/circle-check';
	import { useIsFetching } from '@tanstack/svelte-query';
	import { untrack } from 'svelte';
	import { slide } from 'svelte/transition';

	import { Button } from '#lib/components/ui/button/index.js';
	import { Spinner } from '#lib/components/ui/spinner/index.js';
	import { m } from '#lib/paraglide/messages.js';
	import { probeReachability, reachability } from '#lib/services/reachability.js';

	// Material Design 3 snackbar minimum; prevents flash on brief blips.
	const MIN_DISPLAY_MS = 4000;
	// Long enough to read two words, short enough not to linger on a working app.
	const RESTORED_DISPLAY_MS = 3000;

	// Only one state reaches the user: whether the backend is reachable. The SSE
	// stream's own reconnects stay silent — it only carries change signals, the
	// pages load over plain HTTP, and an attendee can do nothing about a dropped
	// stream. A drop is already confirmed before `reachability` flips, so the
	// banner needs no grace window of its own.
	let isOnline = $derived(reachability.current);
	let deviceOnline = $derived(reachability.deviceOnline);

	// A trustworthy `navigator.onLine === false` is the device's own connection;
	// otherwise the device is online and the API is unreachable (outage, captive
	// portal, dead VPN) — never blame the user's internet for a server outage.
	let offlineMessage = $derived.by(() => {
		if (isOnline) return null;
		return deviceOnline ? m.connection_no_server() : m.connection_no_internet();
	});

	// What the strip shows, held separately from `offlineMessage`: the offline wording
	// stays through the minimum display time instead of vanishing mid-read, then the
	// strip says the connection is back before it slides away (web.dev: tell the user
	// about a change in state as soon as it happens,
	// https://web.dev/articles/offline-ux-design-guidelines).
	let phase = $state<'hidden' | 'offline' | 'catching-up' | 'restored'>('hidden');
	let lastOfflineMessage = $state('');
	let offlineHoldUntil = 0;
	let retrying = $state(false);

	// Queries on screen fetching right now — on reconnect, the stale ones refetching
	// (`refetchOnReconnect`) and the SSE handshake's catch-up. Counting only these
	// keeps «Обновляем…» literal: it shows while what the user is looking at
	// actually reloads, and a page with nothing to reload skips straight to
	// «Связь восстановлена».
	const fetchingOnScreen = useIsFetching({ type: 'active' });

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

		// Untracked: the timer below writes `phase`, and re-running on that write would
		// clear it. Only a real recovery is confirmed, not a session that never went
		// offline.
		if (untrack(() => phase) !== 'offline') return;

		const holdTimeoutId = setTimeout(
			() => (phase = 'catching-up'),
			Math.max(0, offlineHoldUntil - Date.now())
		);
		return () => clearTimeout(holdTimeoutId);
	});

	// Latched rather than derived: once the catch-up is done, a later fetch (a poll,
	// a stale query on the next screen) must not flip the strip back to «Обновляем…».
	$effect(() => {
		if (phase === 'catching-up' && fetchingOnScreen.current === 0) phase = 'restored';
	});

	$effect(() => {
		if (phase !== 'restored') return;
		const hideTimeoutId = setTimeout(() => (phase = 'hidden'), RESTORED_DISPLAY_MS);
		return () => clearTimeout(hideTimeoutId);
	});

	// The reachability monitor already re-checks on its own, but its backoff grows
	// to 30s; a tap checks now, so someone who just fixed their connection isn't
	// left waiting on the timer.
	async function handleRetry() {
		retrying = true;
		try {
			await probeReachability();
		} finally {
			retrying = false;
		}
	}
</script>

<!-- The live region stays mounted and only its content comes and goes: screen readers
	announce changes inside an existing live region, and JAWS/NVDA stay silent for a
	role="status" inserted together with its text
	(https://github.com/FreedomScientific/standards-support/issues/696). It carries the
	text alone, so the retry button's label and spinner aren't read out as status. -->
<div role="status" class="sr-only">{shownMessage}</div>

{#if phase !== 'hidden'}
	<div
		transition:slide={{ duration: 200 }}
		class={[
			// One height for every state, so dropping the retry button doesn't nudge the
			// page.
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
		<p class="flex-1 leading-snug" aria-hidden="true">{shownMessage}</p>
		{#if phase === 'offline'}
			<!-- Negative margin fits the 40px tap target inside the 44px strip. -->
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
