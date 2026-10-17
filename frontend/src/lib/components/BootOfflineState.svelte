<script lang="ts">
	import { RotateCw, WifiOff } from '@lucide/svelte';

	import { Button } from '#lib/components/ui/button/index.js';
	import * as Card from '#lib/components/ui/card/index.js';
	import { Spinner } from '#lib/components/ui/spinner/index.js';
	import { m } from '#lib/paraglide/messages.js';
	import { probeReachability, reachability } from '#lib/services/reachability.js';

	// Shown by the root layout in place of the app when boot found no copy, saved or
	// fresh, of identity or the public config (see the root load).

	// `navigator.onLine === false` is the only trustworthy negative; otherwise the
	// device has a network and the server is what can't be reached, which must not
	// be blamed on the user's connection.
	let deviceOffline = $derived(!reachability.deviceOnline);
	let title = $derived(deviceOffline ? m.connection_no_internet() : m.connection_no_server());
	let hint = $derived(deviceOffline ? m.boot_offline_hint() : m.boot_server_offline_hint());
	let checking = $state(false);

	// Reload only once the server answers: a reload offline without a service
	// worker yet would trade this screen for the browser's own error page. The
	// reload reruns the whole boot, so every load sees the fetched identity and
	// config rather than the failure it ran with.
	async function handleRetry() {
		checking = true;
		if (await probeReachability()) {
			window.location.reload();
			return;
		}
		checking = false;
	}
</script>

<div class="flex min-h-dvh items-center justify-center bg-background px-4 py-6 sm:py-10">
	<Card.Root class="w-full max-w-md rounded-2xl p-6 text-center sm:p-8">
		<div class="flex flex-col items-center justify-center">
			<div
				class="mb-4 flex size-16 items-center justify-center rounded-full bg-warning/15 text-warning"
			>
				<WifiOff class="size-8" aria-hidden="true" />
			</div>

			<h1 class="mb-2 text-headline text-foreground">
				{title}
			</h1>

			<p class="mb-6 text-body text-muted-foreground">
				{hint}
			</p>

			<Button class="w-full" onclick={handleRetry} disabled={checking}>
				{#if checking}
					<Spinner data-icon="inline-start" />
				{:else}
					<RotateCw data-icon="inline-start" />
				{/if}
				{m.common_try_again()}
			</Button>
		</div>
	</Card.Root>
</div>
