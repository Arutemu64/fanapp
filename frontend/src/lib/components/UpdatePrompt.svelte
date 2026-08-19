<script lang="ts">
	import { Button, Toast } from 'flowbite-svelte';
	import { RefreshOutline } from 'flowbite-svelte-icons';
	import { onMount } from 'svelte';

	// A waiting service worker means a newer build is cached and ready. We never
	// activate it mid-session (that could swap assets under the user); instead we
	// surface this prompt and let the user choose when to reload.
	let waitingWorker = $state<ServiceWorker | null>(null);
	let reloading = false;

	// Held so we can poll for new builds ourselves (see checkForUpdate). SvelteKit's
	// auto-registration registers the worker once on load and never re-checks, so
	// without this an installed PWA kept open all event day would not notice a
	// hot-fix deploy until a manual reload.
	let registration: ServiceWorkerRegistration | null = null;

	// How often to ask the browser to re-check the worker script while the app is
	// open. Tuned for a live event where a fix may ship mid-session; the request is
	// a cheap conditional GET that 304s when nothing changed.
	const UPDATE_POLL_MS = 15 * 60 * 1000;

	function promptFor(registration: ServiceWorkerRegistration) {
		const worker = registration.waiting;
		if (worker) {
			waitingWorker = worker;
		}
	}

	// Ask the browser to re-fetch the worker script; if it changed, the normal
	// updatefound/statechange flow below surfaces the prompt. Errors (offline) are
	// ignored — the next check retries.
	function checkForUpdate() {
		if (document.visibilityState !== 'visible') return;
		// Skip while offline (nothing to fetch) or while an install is already in
		// flight — re-checking then just races our own update flow. navigator.onLine
		// is trusted only as a negative here, matching the reachability layer.
		if (!navigator.onLine) return;
		if (registration?.installing) return;
		registration?.update().catch(() => undefined);
	}

	// Watch an installing worker and prompt once it reaches `installed`. The
	// controller check distinguishes an update (prompt) from the first-ever
	// install (no prompt — nothing to replace). Shared by the two entry points
	// below: the `updatefound` event and a worker found already mid-install at
	// mount, whose `updatefound` has already fired.
	function watchInstalling(reg: ServiceWorkerRegistration, worker: ServiceWorker) {
		worker.addEventListener('statechange', () => {
			if (worker.state === 'installed' && navigator.serviceWorker.controller) {
				promptFor(reg);
			}
		});
	}

	function applyUpdate() {
		// Tell the waiting worker to activate; the `controllerchange` listener
		// reloads the page once it takes control.
		waitingWorker?.postMessage('skipWaiting');
	}

	onMount(() => {
		if (!('serviceWorker' in navigator)) return;

		// Whether a worker already controls this page at startup. On a first-ever
		// visit there is no controller: the SW installs, activates, and calls
		// `clients.claim()`, which fires `controllerchange` even though nothing was
		// updated. Without this guard that initial claim would trigger a needless
		// full reload right after first paint. A genuine update always has a prior
		// controller, so gating the reload on this keeps the update flow working.
		const hadController = !!navigator.serviceWorker.controller;

		// `ready` (unlike getRegistration()) waits until the registration has an
		// active worker. On a first-ever visit SvelteKit's auto-registration may
		// still be in flight when this mounts — getRegistration() would resolve
		// `undefined` and silently disable update polling for the whole session.
		void navigator.serviceWorker.ready.then((reg) => {
			registration = reg;

			// A build may already be waiting from a previous visit.
			promptFor(reg);

			// Or one may already be installing when this mounts — e.g. the browser's
			// own on-navigation update check started it before we got here. Its
			// `updatefound` has already fired, so the listener below would miss it and
			// `reg.waiting` is still null; watch it directly or the prompt never shows
			// (an intermittent miss depending on install timing).
			if (reg.installing) {
				watchInstalling(reg, reg.installing);
			}

			// Or one finishes installing while this tab is open.
			reg.addEventListener('updatefound', () => {
				if (reg.installing) {
					watchInstalling(reg, reg.installing);
				}
			});

			// Re-check immediately in case a deploy landed while the app was closed,
			// then keep polling for the rest of the session.
			checkForUpdate();
		});

		const onControllerChange = () => {
			// Ignore the first-install claim (no prior controller) — only reload when
			// an existing worker was swapped out by an accepted update.
			if (reloading || !hadController) return;
			reloading = true;
			window.location.reload();
		};
		navigator.serviceWorker.addEventListener('controllerchange', onControllerChange);

		const pollId = setInterval(checkForUpdate, UPDATE_POLL_MS);

		return () => {
			navigator.serviceWorker.removeEventListener('controllerchange', onControllerChange);
			clearInterval(pollId);
		};
	});
</script>

<!-- Re-check on foreground so reopening the installed PWA picks up a deploy that
	landed while it was backgrounded, without waiting for the poll interval. -->
<svelte:document onvisibilitychange={checkForUpdate} />

{#if waitingWorker}
	<!-- Persistent by design: a prompt carrying an action must never auto-dismiss
		(WCAG 2.2.1), so this is a plain Toast with no close button and no timer.
		Shares the bottom band and z-layer with the status toasts; on the rare tick
		where a reload is pending and an action toast fires at the same time the two
		may overlap, which we accept rather than couple them across layouts.
		pointer-events-none on the full-width wrapper keeps taps outside the card from
		being swallowed; the card itself re-enables them. -->
	<div
		role="status"
		aria-live="polite"
		aria-atomic="true"
		class="pointer-events-none fixed inset-x-0 bottom-[calc(4.5rem+env(safe-area-inset-bottom))] z-(--z-overlay) flex justify-center px-4 md:bottom-4 md:px-6 lg:px-8"
	>
		<Toast
			align={false}
			color="primary"
			dismissable={false}
			class="pointer-events-auto w-full max-w-sm shadow"
		>
			<!-- No text-* override on the icon: it inherits the Toast icon badge's
				tonal colour (primary-500 light / primary-200 dark), which is what keeps
				it legible on the primary-100 / primary-800 badge in both themes. Hard-
				coding a single shade collapsed the contrast in dark mode. -->
			{#snippet icon()}
				<RefreshOutline class="h-5 w-5" aria-hidden="true" />
			{/snippet}
			<div class="text-sm leading-snug font-normal text-gray-700 dark:text-gray-200">
				Доступна новая версия приложения.
			</div>
			<div class="mt-3">
				<Button size="sm" color="primary" class="w-full" onclick={applyUpdate}>Обновить</Button>
			</div>
		</Toast>
	</div>
{/if}
