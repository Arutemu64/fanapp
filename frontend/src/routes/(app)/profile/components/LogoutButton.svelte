<script lang="ts">
	import LogOut from '@lucide/svelte/icons/log-out';
	import { createMutation } from '@tanstack/svelte-query';

	import { logoutUserMutation } from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import * as AlertDialog from '#lib/components/ui/alert-dialog/index.js';
	import { Button } from '#lib/components/ui/button/index.js';
	import { Spinner } from '#lib/components/ui/spinner/index.js';
	import { m } from '#lib/paraglide/messages.js';
	import { trackEvent } from '#lib/services/analytics.js';
	import { getSession } from '#lib/services/session.js';
	import { getToastService } from '#lib/services/toasts.svelte.js';

	const toastService = getToastService();
	const session = getSession();
	const logoutMutation = createMutation(() => logoutUserMutation());

	let isLoggingOut = $state(false);
	let confirmOpen = $state(false);

	async function handleLogout() {
		if (isLoggingOut) return;

		isLoggingOut = true;
		try {
			await session.logOut(() => logoutMutation.mutateAsync({}));
			trackEvent('logout');
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
		{m.logout_progress()}
	{:else}
		<LogOut data-icon="inline-start" />
		{m.logout_action()}
	{/if}
</Button>

<AlertDialog.Root bind:open={confirmOpen}>
	<AlertDialog.Content>
		<AlertDialog.Header>
			<AlertDialog.Title>{m.logout_confirm_title()}</AlertDialog.Title>
			<AlertDialog.Description>{m.logout_confirm_description()}</AlertDialog.Description>
		</AlertDialog.Header>
		<AlertDialog.Footer>
			<AlertDialog.Cancel>{m.common_cancel()}</AlertDialog.Cancel>
			<AlertDialog.Action variant="destructive" onclick={handleLogout}
				>{m.logout_action()}</AlertDialog.Action
			>
		</AlertDialog.Footer>
	</AlertDialog.Content>
</AlertDialog.Root>
