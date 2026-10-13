<script lang="ts">
	import { LogOut } from '@lucide/svelte';
	import { createMutation } from '@tanstack/svelte-query';

	import { logoutUserMutation } from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import * as AlertDialog from '#lib/components/ui/alert-dialog/index.js';
	import { Button } from '#lib/components/ui/button/index.js';
	import { Spinner } from '#lib/components/ui/spinner/index.js';
	import { getSession } from '#lib/services/session.js';
	import { getToastService } from '#lib/services/toasts.svelte.js';

	const toastService = getToastService();
	const session = getSession();
	const logoutMutation = createMutation(() => logoutUserMutation());

	// Disables the button for the round-trip, so a second tap can't fire a second
	// logout into a session the first one is already ending. Not the mutation's
	// isPending: it also spans the offline path, which sends no request, and the
	// navigation home.
	let isLoggingOut = $state(false);
	// Asked once before leaving: logging out also wipes this device's cached data,
	// so a stray tap costs more than a re-login (web.dev's sign-out guidance
	// recommends a confirm step: https://web.dev/articles/sign-out-best-practices).
	let confirmOpen = $state(false);

	async function handleLogout() {
		if (isLoggingOut) return;

		isLoggingOut = true;
		try {
			await session.logOut(() => logoutMutation.mutateAsync({}));
		} catch (error) {
			toastService.error(error);
		} finally {
			isLoggingOut = false;
		}
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
