<script lang="ts">
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { createApiClient } from '$lib/api';
	import { logoutUser } from '$lib/api/generated';
	import * as AlertDialog from '$lib/components/ui/alert-dialog';
	import { Button } from '$lib/components/ui/button';
	import { Spinner } from '$lib/components/ui/spinner';
	import { getEventsClient } from '$lib/services/events.svelte';
	import { getToastService } from '$lib/services/toasts.svelte';
	import { LogOut } from '@lucide/svelte';

	const client = createApiClient();
	const toastService = getToastService();
	const eventsClient = getEventsClient();

	// Disables the button for the round-trip, so a second tap can't fire a second
	// logout into a session the first one is already ending.
	let isLoggingOut = $state(false);
	// Asked once before leaving, so a stray tap doesn't cost a re-login (web.dev's
	// sign-out guidance recommends a confirm step:
	// https://web.dev/articles/sign-out-best-practices).
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
		const { error, response } = await logoutUser({ client });

		if (error || !response?.ok) {
			toastService.error(error);
			return;
		}

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
