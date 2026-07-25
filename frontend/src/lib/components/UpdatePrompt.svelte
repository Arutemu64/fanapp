<!--
@component
Banner offering a reload when a newer build's service worker is waiting.

Mounted once in the root layout. A waiting worker is never activated
automatically — that would swap assets mid-session — so this prompt is the
only path to `skipWaiting`, and the page reloads on `controllerchange`.
It also re-polls for new builds itself (SvelteKit registers the worker once
and never re-checks), so an installed PWA left open all event day still
notices a hot-fix deploy.
-->
<script lang="ts">
	import { browser } from '$app/environment';
	import { Button } from 'flowbite-svelte';
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
		registration?.update().catch(() => undefined);
	}

	function applyUpdate() {
		// Tell the waiting worker to activate; the `controllerchange` listener
		// reloads the page once it takes control.
		waitingWorker?.postMessage('skipWaiting');
	}

	onMount(() => {
		if (!browser || !('serviceWorker' in navigator)) return;

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

			// Or one finishes installing while this tab is open.
			reg.addEventListener('updatefound', () => {
				const installing = reg.installing;
				if (!installing) return;
				installing.addEventListener('statechange', () => {
					// `installed` + an existing controller means it's an update,
					// not the first install — only then do we prompt.
					if (installing.state === 'installed' && navigator.serviceWorker.controller) {
						promptFor(reg);
					}
				});
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
	<div
		role="status"
		class="fixed inset-x-0 bottom-0 z-[110] flex justify-center px-4 pb-[calc(6rem+env(safe-area-inset-bottom))] md:pb-[calc(env(safe-area-inset-bottom)+0.75rem)]"
	>
		<div
			class="flex w-full max-w-md items-center gap-3 rounded-xl border border-gray-200 bg-white px-4 py-3 shadow-lg dark:border-gray-700 dark:bg-gray-800"
		>
			<RefreshOutline class="h-5 w-5 shrink-0 text-primary-600" aria-hidden="true" />
			<p class="flex-1 text-sm leading-snug text-gray-700 dark:text-gray-200">
				Доступна новая версия приложения.
			</p>
			<Button size="sm" color="primary" class="shrink-0" onclick={applyUpdate}>Обновить</Button>
		</div>
	</div>
{/if}
