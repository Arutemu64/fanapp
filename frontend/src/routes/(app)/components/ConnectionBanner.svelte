<script lang="ts">
	import { AlertCircle, CheckCircle2 } from '@lucide/svelte';
	import { untrack } from 'svelte';
	import { slide } from 'svelte/transition';

	import { Button } from '#lib/components/ui/button/index.js';
	import { Spinner } from '#lib/components/ui/spinner/index.js';
	import { probeReachability, reachability } from '#lib/services/reachability.js';

	// Material Design 3 snackbar minimum; prevents flash on brief blips.
	const MIN_DISPLAY_MS = 4000;
	// Long enough to read two words, short enough not to linger on a working app.
	const RESTORED_DISPLAY_MS = 3000;
	const RESTORED_MESSAGE = 'Связь восстановлена';

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
		return deviceOnline ? 'Нет связи с сервером' : 'Нет интернета';
	});

	// Held separately from `offlineMessage` so the strip keeps its last wording
	// through the minimum display time instead of vanishing mid-read, then says the
	// connection is back before it slides away (web.dev: tell the user about a
	// change in state as soon as it happens,
	// https://web.dev/articles/offline-ux-design-guidelines).
	let shown = $state<{ kind: 'offline'; message: string } | { kind: 'restored' } | null>(null);
	let offlineHoldUntil = 0;
	let retrying = $state(false);

	let shownMessage = $derived.by(() => {
		if (shown === null) return '';
		if (shown.kind === 'restored') return RESTORED_MESSAGE;
		return shown.message;
	});

	$effect(() => {
		const message = offlineMessage;

		if (message) {
			shown = { kind: 'offline', message };
			offlineHoldUntil = Date.now() + MIN_DISPLAY_MS;
			return;
		}

		// Untracked: the timers below write `shown`, and re-running on that write would
		// clear them. Only a real recovery is confirmed, not a session that never
		// went offline.
		if (untrack(() => shown?.kind) !== 'offline') return;

		let hideTimeoutId: ReturnType<typeof setTimeout> | undefined;
		const restoreTimeoutId = setTimeout(
			() => {
				shown = { kind: 'restored' };
				hideTimeoutId = setTimeout(() => (shown = null), RESTORED_DISPLAY_MS);
			},
			Math.max(0, offlineHoldUntil - Date.now())
		);
		return () => {
			clearTimeout(restoreTimeoutId);
			clearTimeout(hideTimeoutId);
		};
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

{#if shown}
	<div
		transition:slide={{ duration: 200 }}
		class={[
			// One height for both states, so swapping to «восстановлена» (no button)
			// doesn't nudge the page.
			'flex min-h-11 items-center gap-2.5 border-b px-4 py-2 text-sm sm:px-6',
			shown.kind === 'offline' && 'border-warning/30 bg-warning/10 text-warning',
			shown.kind === 'restored' && 'border-success/30 bg-success/10 text-success'
		]}
	>
		{#if shown.kind === 'offline'}
			<AlertCircle class="h-4 w-4 shrink-0" aria-hidden="true" />
		{:else}
			<CheckCircle2 class="h-4 w-4 shrink-0" aria-hidden="true" />
		{/if}
		<p class="flex-1 leading-snug" aria-hidden="true">{shownMessage}</p>
		{#if shown.kind === 'offline'}
			<!-- Negative margin fits the 40px tap target inside the 44px strip. -->
			<Button
				variant="ghost"
				size="sm"
				class="-my-1.5 shrink-0"
				disabled={retrying}
				onclick={handleRetry}
			>
				{#if retrying}
					<Spinner data-icon="inline-start" />
				{/if}
				Повторить
			</Button>
		{/if}
	</div>
{/if}
