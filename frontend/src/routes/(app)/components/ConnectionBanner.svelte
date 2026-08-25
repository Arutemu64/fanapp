<script lang="ts">
	import { type ConnectionStatus, getEventsClient } from '$lib/services/events.svelte';
	import { getOfflineService } from '$lib/services/offline.svelte';
	import { reachability } from '$lib/services/reachability';
	import { ExclamationCircleOutline, RefreshOutline } from 'flowbite-svelte-icons';
	import { slide } from 'svelte/transition';

	// 8s absorbs the normal SSE reconnect after foregrounding without alarming
	// the user; only a genuinely struggling connection exceeds this window.
	const RECOVERING_GRACE_MS = 8000;

	// Material Design 3 snackbar minimum; prevents flash on brief blips.
	const MIN_DISPLAY_MS = 4000;

	type Health = 'healthy' | 'recovering' | 'down';

	// `disconnected` is intentional (logout) — stays silent.
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

	const offline = getOfflineService();
	let isOnline = $derived(offline.isOnline);
	let deviceOnline = $derived(reachability.deviceOnline);

	let recoveringVisible = $state(false);

	$effect(() => {
		if (health !== 'recovering') {
			recoveringVisible = false;
			return;
		}

		const timeoutId = setTimeout(() => (recoveringVisible = true), RECOVERING_GRACE_MS);
		return () => clearTimeout(timeoutId);
	});

	type BannerTone = 'yellow' | 'red';

	const TONE_CLASSES: Record<BannerTone, string> = {
		yellow:
			'border-yellow-200/60 bg-yellow-50/80 text-yellow-800 dark:border-yellow-900/30 dark:bg-yellow-950/40 dark:text-yellow-200/90',
		red: 'border-red-200/60 bg-red-50/80 text-red-800 dark:border-red-900/30 dark:bg-red-950/40 dark:text-red-200/90'
	};

	interface Banner {
		tone: BannerTone;
		role: 'status' | 'alert';
		icon: typeof ExclamationCircleOutline;
		iconClass: string;
		message: string;
		showRetry: boolean;
	}

	// Unreachable server outranks lost SSE stream outranks delayed "reconnecting".
	let desiredBanner = $derived.by<Banner | null>(() => {
		if (!isOnline) {
			return {
				tone: 'yellow',
				role: 'status',
				icon: ExclamationCircleOutline,
				iconClass: 'h-4 w-4',
				message: deviceOnline ? 'Нет связи с сервером' : 'Нет интернета',
				showRetry: false
			};
		}
		if (health === 'down') {
			return {
				tone: 'red',
				role: 'alert',
				icon: ExclamationCircleOutline,
				iconClass: 'h-4 w-4',
				message: 'Соединение потеряно',
				showRetry: true
			};
		}
		if (recoveringVisible) {
			return {
				tone: 'yellow',
				role: 'status',
				icon: RefreshOutline,
				iconClass: 'h-3.5 w-3.5 motion-safe:animate-spin',
				message: 'Восстанавливаем связь…',
				showRetry: false
			};
		}
		return null;
	});

	let banner = $state<Banner | null>(null);
	let hideLockedUntil = 0;
	let holdTimeoutId: ReturnType<typeof setTimeout> | null = null;

	$effect(() => {
		const desired = desiredBanner;

		if (holdTimeoutId !== null) {
			clearTimeout(holdTimeoutId);
			holdTimeoutId = null;
		}

		if (desired) {
			banner = desired;
			hideLockedUntil = Date.now() + MIN_DISPLAY_MS;
		} else {
			const remaining = hideLockedUntil - Date.now();
			if (remaining > 0) {
				holdTimeoutId = setTimeout(() => {
					holdTimeoutId = null;
					banner = null;
				}, remaining);
			} else {
				banner = null;
			}
		}

		return () => {
			if (holdTimeoutId !== null) {
				clearTimeout(holdTimeoutId);
				holdTimeoutId = null;
			}
		};
	});
</script>

{#if banner}
	{@const Icon = banner.icon}
	<div
		role={banner.role}
		aria-live={banner.role === 'status' ? 'polite' : undefined}
		transition:slide={{ duration: 200 }}
		class="flex items-center gap-2.5 border-b px-4 py-2 text-xs sm:px-6 {TONE_CLASSES[banner.tone]}"
	>
		<Icon class="shrink-0 {banner.iconClass}" aria-hidden="true" />
		<p class="flex-1 leading-snug">{banner.message}</p>
		{#if banner.showRetry}
			<button
				type="button"
				onclick={() => client.restart()}
				class="inline-flex min-h-9 shrink-0 items-center rounded-lg bg-red-600 px-2.5 text-xs font-medium text-white hover:bg-red-700 focus-visible:ring-2 focus-visible:ring-red-400 focus-visible:ring-offset-2 focus-visible:ring-offset-red-50 focus-visible:outline-none dark:focus-visible:ring-offset-red-950"
			>
				Обновить
			</button>
		{/if}
	</div>
{/if}
