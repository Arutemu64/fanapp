<script lang="ts">
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { createApiClient } from '$lib/api';
	import { logoutUser } from '$lib/api/generated';
	import * as AlertDialog from '$lib/components/ui/alert-dialog';
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
	// Asked once before leaving: logging out also wipes this device's cached data,
	// so a stray tap costs more than a re-login (web.dev's sign-out guidance
	// recommends a confirm step: https://web.dev/articles/sign-out-best-practices).
	let confirmOpen = $state(false);

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
	onclick={() => (confirmOpen = true)}
>
	{#if isLoggingOut}
		<Spinner data-icon="inline-start" />
		Выход…
	{:else}
		<LogOut data-icon="inline-start" />
		Выйти
	{/if}
</Button>

<!-- AlertDialog per the confirmation convention (docs/frontend.md §7): Cancel comes
     first so the safe choice takes focus; Action closes on its own and the work
     runs here, surfacing any failure as a toast. -->
<AlertDialog.Root bind:open={confirmOpen}>
	<AlertDialog.Content>
		<AlertDialog.Header>
			<AlertDialog.Title>Выйти из аккаунта?</AlertDialog.Title>
			<AlertDialog.Description>Чтобы вернуться, нужно будет войти снова.</AlertDialog.Description>
		</AlertDialog.Header>
		<AlertDialog.Footer>
			<AlertDialog.Cancel>Отмена</AlertDialog.Cancel>
			<AlertDialog.Action variant="destructive" onclick={handleLogout}>Выйти</AlertDialog.Action>
		</AlertDialog.Footer>
	</AlertDialog.Content>
</AlertDialog.Root>
