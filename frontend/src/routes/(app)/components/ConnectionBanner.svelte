<script lang="ts">
	import { getEventsClient, type ConnectionStatus } from '$lib/services/events.svelte';
	import { getOfflineService } from '$lib/services/offline.svelte';
	import { ExclamationCircleOutline, RefreshOutline } from 'flowbite-svelte-icons';

	// Wait this long before showing the "reconnecting" strip, so a quick blip
	// during navigation or a 1-second reconnect stays silent.
	const RECOVERING_GRACE_MS = 4000;

	type Health = 'healthy' | 'recovering' | 'down';

	// Collapse the six raw connection statuses into three buckets the UI cares about.
	// `disconnected` only happens on logout (intentional), so it stays silent.
	const HEALTH_BY_STATUS: Record<ConnectionStatus, Health> = {
		connected: 'healthy',
		transport_open: 'healthy',
		disconnected: 'healthy',
		connecting: 'recovering',
		error: 'recovering',
		failed: 'down'
	};

	// The client is null outside the browser; treat that as healthy so nothing renders.
	const client = getEventsClient();
	let health = $derived<Health>(client ? HEALTH_BY_STATUS[client.connectionStatus] : 'healthy');

	// Browser-level connectivity. When the device is offline, show a dedicated
	// strip instead of the SSE "connection lost" one — it is the real cause and
	// the clearer message for the user.
	const offline = getOfflineService();
	let isOnline = $derived(offline.isOnline);

	// Latches true only after the connection has stayed in `recovering` past the
	// grace window. Recovery (or hard failure) clears it immediately.
	let recoveringVisible = $state(false);

	$effect(() => {
		if (health !== 'recovering') {
			recoveringVisible = false;
			return;
		}

		const timeoutId = setTimeout(() => (recoveringVisible = true), RECOVERING_GRACE_MS);
		return () => clearTimeout(timeoutId);
	});

	function reconnect() {
		// restart() resets the attempt counter and re-dials the stream.
		client?.restart();
	}
</script>

{#if !isOnline}
	<div
		role="status"
		aria-live="polite"
		class="flex min-h-14 items-center gap-3 border-b border-yellow-200 bg-yellow-50 px-4 py-2.5 text-sm text-yellow-800 sm:px-6 dark:border-yellow-900/50 dark:bg-yellow-950/50 dark:text-yellow-200"
	>
		<ExclamationCircleOutline class="h-5 w-5 shrink-0" aria-hidden="true" />
		<p class="flex-1 leading-snug">Нет соединения</p>
	</div>
{:else if health === 'down'}
	<div
		role="alert"
		class="flex min-h-14 items-center gap-3 border-b border-red-200 bg-red-50 px-4 py-2.5 text-sm text-red-800 sm:px-6 dark:border-red-900/50 dark:bg-red-950/60 dark:text-red-200"
	>
		<ExclamationCircleOutline class="h-5 w-5 shrink-0" aria-hidden="true" />
		<p class="flex-1 leading-snug">Соединение потеряно</p>
		<button
			type="button"
			onclick={reconnect}
			class="inline-flex min-h-11 shrink-0 items-center rounded-lg bg-red-600 px-3 text-sm font-medium text-white hover:bg-red-700 focus-visible:ring-2 focus-visible:ring-red-400 focus-visible:ring-offset-2 focus-visible:ring-offset-red-50 focus-visible:outline-none dark:focus-visible:ring-offset-red-950"
		>
			Обновить
		</button>
	</div>
{:else if recoveringVisible}
	<div
		role="status"
		aria-live="polite"
		class="flex min-h-14 items-center gap-2.5 border-b border-yellow-200 bg-yellow-50 px-4 py-2 text-sm text-yellow-800 sm:px-6 dark:border-yellow-900/50 dark:bg-yellow-950/50 dark:text-yellow-200"
	>
		<RefreshOutline class="h-4 w-4 shrink-0 motion-safe:animate-spin" aria-hidden="true" />
		<!-- Honest wording: covers both a real reconnect and an offline device whose
			navigator.onLine wrongly reports online (common in installed PWAs). -->
		<p class="leading-snug">Нет соединения. Переподключаемся…</p>
	</div>
{/if}
