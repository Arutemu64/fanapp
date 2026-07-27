<script lang="ts">
	import { type ConnectionStatus, getEventsClient } from '$lib/services/events.svelte';
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

	const client = getEventsClient();
	let health = $derived<Health>(HEALTH_BY_STATUS[client.connectionStatus]);

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
		client.restart();
	}

	type BannerTone = 'yellow' | 'red';

	const TONE_CLASSES: Record<BannerTone, string> = {
		yellow:
			'border-yellow-200 bg-yellow-50 text-yellow-800 dark:border-yellow-900/50 dark:bg-yellow-950/50 dark:text-yellow-200',
		red: 'border-red-200 bg-red-50 text-red-800 dark:border-red-900/50 dark:bg-red-950/60 dark:text-red-200'
	};

	interface Banner {
		tone: BannerTone;
		role: 'status' | 'alert';
		icon: typeof ExclamationCircleOutline;
		iconClass: string;
		message: string;
		showRetry: boolean;
	}

	// Pick at most one banner; offline (real cause) outranks a lost SSE stream,
	// which outranks the delayed "reconnecting" strip. Honest reconnecting wording
	// covers an offline device whose navigator.onLine wrongly reports online
	// (common in installed PWAs).
	let banner = $derived.by<Banner | null>(() => {
		if (!isOnline) {
			return {
				tone: 'yellow',
				role: 'status',
				icon: ExclamationCircleOutline,
				iconClass: 'h-5 w-5',
				message: 'Нет соединения',
				showRetry: false
			};
		}
		if (health === 'down') {
			return {
				tone: 'red',
				role: 'alert',
				icon: ExclamationCircleOutline,
				iconClass: 'h-5 w-5',
				message: 'Соединение потеряно',
				showRetry: true
			};
		}
		if (recoveringVisible) {
			return {
				tone: 'yellow',
				role: 'status',
				icon: RefreshOutline,
				iconClass: 'h-4 w-4 motion-safe:animate-spin',
				message: 'Нет соединения. Переподключаемся…',
				showRetry: false
			};
		}
		return null;
	});
</script>

{#if banner}
	{@const Icon = banner.icon}
	<div
		role={banner.role}
		aria-live={banner.role === 'status' ? 'polite' : undefined}
		class="flex min-h-14 items-center gap-3 border-b px-4 py-2.5 text-sm sm:px-6 {TONE_CLASSES[
			banner.tone
		]}"
	>
		<Icon class="shrink-0 {banner.iconClass}" aria-hidden="true" />
		<p class="flex-1 leading-snug">{banner.message}</p>
		{#if banner.showRetry}
			<button
				type="button"
				onclick={reconnect}
				class="inline-flex min-h-11 shrink-0 items-center rounded-lg bg-red-600 px-3 text-sm font-medium text-white hover:bg-red-700 focus-visible:ring-2 focus-visible:ring-red-400 focus-visible:ring-offset-2 focus-visible:ring-offset-red-50 focus-visible:outline-none dark:focus-visible:ring-offset-red-950"
			>
				Обновить
			</button>
		{/if}
	</div>
{/if}
