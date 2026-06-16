<script lang="ts">
	import { browser } from '$app/environment';
	import { onMount } from 'svelte';
	import { Button } from 'flowbite-svelte';
	import { RefreshOutline } from 'flowbite-svelte-icons';

	// A waiting service worker means a newer build is cached and ready. We never
	// activate it mid-session (that could swap assets under the user); instead we
	// surface this prompt and let the user choose when to reload.
	let waitingWorker = $state<ServiceWorker | null>(null);
	let reloading = false;

	function promptFor(registration: ServiceWorkerRegistration) {
		const worker = registration.waiting;
		if (worker) {
			waitingWorker = worker;
		}
	}

	function applyUpdate() {
		// Tell the waiting worker to activate; the `controllerchange` listener
		// reloads the page once it takes control.
		waitingWorker?.postMessage('skipWaiting');
	}

	onMount(() => {
		if (!browser || !('serviceWorker' in navigator)) return;

		navigator.serviceWorker.getRegistration().then((registration) => {
			if (!registration) return;

			// A build may already be waiting from a previous visit.
			promptFor(registration);

			// Or one finishes installing while this tab is open.
			registration.addEventListener('updatefound', () => {
				const installing = registration.installing;
				if (!installing) return;
				installing.addEventListener('statechange', () => {
					// `installed` + an existing controller means it's an update,
					// not the first install — only then do we prompt.
					if (installing.state === 'installed' && navigator.serviceWorker.controller) {
						promptFor(registration);
					}
				});
			});
		});

		const onControllerChange = () => {
			if (reloading) return;
			reloading = true;
			window.location.reload();
		};
		navigator.serviceWorker.addEventListener('controllerchange', onControllerChange);

		return () => {
			navigator.serviceWorker.removeEventListener('controllerchange', onControllerChange);
		};
	});
</script>

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
