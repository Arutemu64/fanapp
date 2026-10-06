<script lang="ts">
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { createApiClient } from '$lib/api';
	import { logoutUser } from '$lib/api/generated';
	import { Button } from '$lib/components/ui/button';
	import { Spinner } from '$lib/components/ui/spinner';
	import { getEventsClient } from '$lib/services/events.svelte';
	import { getOfflineService } from '$lib/services/offline.svelte';
	import { getToastService } from '$lib/services/toasts.svelte';
	import { clearUserCache } from '$lib/utils/offlineCache';
	import { markLogoutPending } from '$lib/utils/pendingLogout';
	import { LogOut } from '@lucide/svelte';

	const client = createApiClient();
	const toastService = getToastService();
	const eventsClient = getEventsClient();
	const offline = getOfflineService();

	// Disables the button for the round-trip, so a second tap can't fire a second
	// logout into a session the first one is already ending.
	let isLoggingOut = $state(false);

	async function handleLogout() {
		if (isLoggingOut) return;

		isLoggingOut = true;
		try {
			await logout();
		} finally {
			isLoggingOut = false;
		}
	}

	async function logout() {
		// Offline: we can't reach the server to end the session, and the session
		// cookie is HttpOnly so JS can't clear it either. Record the intent — the
		// queued POST /auth/logout fires on reconnect (see pendingLogout) — and tear
		// down local state now so a shared device stops showing this account at once.
		if (!offline.isOnline) {
			markLogoutPending();
			await finishLogout();
			return;
		}

		const { error, response } = await logoutUser({ client });

		if (error || !response?.ok) {
			toastService.error(error);
			return;
		}

		await finishLogout();
	}

	async function finishLogout() {
		// Drop the previous user's cached data so it can't surface for the next
		// account (or offline) on a shared device. Universal caches (e.g. schedule)
		// stay warm by design.
		await clearUserCache();

		await goto(resolve('/'), { invalidateAll: true });
		eventsClient.restart();
	}
</script>

<Button
	variant="destructive"
	size="lg"
	class="w-full"
	disabled={isLoggingOut}
	onclick={handleLogout}
>
	{#if isLoggingOut}
		<Spinner data-icon="inline-start" />
		Выход…
	{:else}
		<LogOut data-icon="inline-start" />
		Выйти
	{/if}
</Button>
