<script lang="ts">
	import { AlertCircle } from '@lucide/svelte';
	import { slide } from 'svelte/transition';

	import { reachability } from '#lib/services/reachability.js';

	// Material Design 3 snackbar minimum; prevents flash on brief blips.
	const MIN_DISPLAY_MS = 4000;

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
	let desiredMessage = $derived.by(() => {
		if (isOnline) return null;
		return deviceOnline ? 'Нет связи с сервером' : 'Нет интернета';
	});

	// Held separately from `desiredMessage` so the strip keeps its last wording
	// through the minimum display time instead of vanishing mid-read.
	let message = $state<string | null>(null);
	let hideLockedUntil = 0;

	$effect(() => {
		const desired = desiredMessage;

		if (desired) {
			message = desired;
			hideLockedUntil = Date.now() + MIN_DISPLAY_MS;
			return;
		}

		const remaining = hideLockedUntil - Date.now();
		if (remaining <= 0) {
			message = null;
			return;
		}

		const holdTimeoutId = setTimeout(() => (message = null), remaining);
		return () => clearTimeout(holdTimeoutId);
	});
</script>

{#if message}
	<div
		role="status"
		aria-live="polite"
		transition:slide={{ duration: 200 }}
		class="flex items-center gap-2.5 border-b border-warning/30 bg-warning/10 px-4 py-2 text-xs text-warning sm:px-6"
	>
		<AlertCircle class="h-4 w-4 shrink-0" aria-hidden="true" />
		<p class="flex-1 leading-snug">{message}</p>
	</div>
{/if}
