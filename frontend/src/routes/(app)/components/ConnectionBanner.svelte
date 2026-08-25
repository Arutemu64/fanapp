<script lang="ts">
	import { type ConnectionStatus, getEventsClient } from '$lib/services/events.svelte';
	import { getOfflineService } from '$lib/services/offline.svelte';
	import { reachability } from '$lib/services/reachability';
	import { ExclamationCircleOutline, RefreshOutline } from 'flowbite-svelte-icons';
	import { slide } from 'svelte/transition';

	// Wait this long before showing the "reconnecting" strip. 8s absorbs the
	// normal SSE reconnect after foregrounding (visibility resume, radio wake)
	// without alarming the user — the SSE client reconnects in 1-3s on a healthy
	// network. Only a genuinely struggling connection exceeds this window.
	const RECOVERING_GRACE_MS = 8000;

	// Once shown, keep the banner visible for at least this long even if the
	// issue resolves sooner. Prevents the jarring flash of a banner appearing
	// and vanishing in under a second on brief connectivity blips.
	// Material Design 3 snackbar spec recommends a 4s minimum display.
	const MIN_DISPLAY_MS = 4000;

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

	// Backend reachability. When the server can't be reached, show a dedicated
	// strip instead of the SSE "connection lost" one — it is the real cause and
	// the clearer message for the user.
	const offline = getOfflineService();
	let isOnline = $derived(offline.isOnline);

	// Device-level connectivity, to tell "no internet" apart from "server
	// unreachable" — see reachability.ts. A `false` is a trustworthy negative.
	let deviceOnline = $derived(reachability.deviceOnline);

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

	// Pick at most one banner; an unreachable server (the real cause) outranks a
	// lost SSE stream, which outranks the delayed "reconnecting" strip. When the
	// server can't be reached, distinguish a truly offline device ("Нет
	// интернета") from an online device that just can't reach the server ("Нет
	// связи с сервером") — never blame the user's internet for a server outage.
	// The recovery poll clears both on its own, so neither offers a retry button.
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

	// Enforce a minimum display: once the banner appears, keep it for MIN_DISPLAY_MS
	// even if the underlying issue resolves sooner. This prevents the quick flash
	// of a banner appearing and vanishing on a brief blip.
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
				onclick={reconnect}
				class="inline-flex min-h-9 shrink-0 items-center rounded-lg bg-red-600 px-2.5 text-xs font-medium text-white hover:bg-red-700 focus-visible:ring-2 focus-visible:ring-red-400 focus-visible:ring-offset-2 focus-visible:ring-offset-red-50 focus-visible:outline-none dark:focus-visible:ring-offset-red-950"
			>
				Обновить
			</button>
		{/if}
	</div>
{/if}
