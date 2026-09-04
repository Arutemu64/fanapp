<script lang="ts">
	import { PUBLIC_API_URL } from '$env/static/public';
	import { Button } from '$lib/components/ui/button';
	import * as Card from '$lib/components/ui/card';
	import { Spinner } from '$lib/components/ui/spinner';
	import { getToastService } from '$lib/services/toasts.svelte';
	import { clearOAuthErrorParam, OAUTH_LOGIN_ERROR_PARAM } from '$lib/utils/oauthErrors';
	import { Mail } from '@lucide/svelte';
	import { onMount } from 'svelte';
	import IconVk from '~icons/simple-icons/vk';

	import type { PageProps } from './$types';

	import CodeLoginForm from './components/CodeLoginForm.svelte';
	import PasswordLoginForm from './components/PasswordLoginForm.svelte';

	let { data }: PageProps = $props();
	const toastService = getToastService();

	// The first screen offers the login options only; the email form (and its
	// third-party captcha script) lives on its own step, so someone using an
	// OAuth provider never loads it. 'password' is a factor under 'email', not a
	// peer option, so it's reached from the email step rather than the options.
	type LoginView = 'options' | 'email' | 'password';
	let view = $state<LoginView>('options');

	// Kept on the parent so it survives the email ⇄ password switch.
	let email = $state('');

	// Cancelling is the user's own choice, so it gets an informational toast —
	// only a flow that actually broke reads as an error.
	const loginErrorToasts = {
		cancelled: { message: 'Вход отменён.', type: 'info' },
		failed: { message: 'Не удалось войти. Попробуй ещё раз.', type: 'error' }
	} as const;

	// Starting an OAuth login is a full-page navigation that waits on our backend
	// and on the provider's discovery/authorize page, so the button has to say it
	// was heard. One flag per provider prevents a double-click on either.
	let isOpeningVk = $state(false);

	function handleVkClick(event: MouseEvent) {
		if (isOpeningVk) {
			event.preventDefault();
			return;
		}

		// Don't cancel a pending offline-logout here — clearing it before OAuth
		// *succeeds* would let a cancelled/abandoned login drop the revoke, leaving the
		// valid HttpOnly cookie to restore the old account. The reconnect/boot flush
		// clears the intent once the old session is actually revoked, which in practice
		// runs before the user reaches this button, so a genuine new login still starts
		// from a cleared intent. (A client-only "did OAuth succeed?" signal can't tell
		// success from an abandoned flow, so we don't try — see the PR discussion.)
		isOpeningVk = true;
	}

	function showOptions() {
		view = 'options';
	}

	function showEmailLogin() {
		view = 'email';
	}

	function showPasswordLogin() {
		view = 'password';
	}

	onMount(() => {
		const loginError = data.oauthLoginError;

		if (!loginError) return;

		const toast = loginErrorToasts[loginError];
		toastService.add(toast.message, toast.type);

		clearOAuthErrorParam(OAUTH_LOGIN_ERROR_PARAM);
	});
</script>

<!-- Coming back from a provider restores this page from the bfcache with its DOM
	frozen mid-navigation, so the spinner would still be running. `pageshow` fires
	on that restore (and on a normal load, where the flags are already false). -->
<svelte:window
	onpageshow={() => {
		isOpeningVk = false;
	}}
/>

<svelte:head>
	<title>Вход · ФАН ФАН</title>
</svelte:head>

<Card.Root class="w-full rounded-2xl p-4 sm:p-6">
	<div class="flex flex-col gap-4">
		<div class="flex flex-col gap-1 text-center">
			<h1 class="text-2xl font-bold text-foreground">Вход в ФАН ФАН</h1>
			{#if view === 'options'}
				<!-- Benefits belong on the entry screen only: once a method is chosen the
					sub-steps are the task, not the pitch. -->
				<p class="text-sm text-muted-foreground">
					Получай персональные уведомления, голосуй за участников и оставляй обратную связь.
				</p>
			{/if}
		</div>

		{#if view === 'options'}
			<Button
				href={`${PUBLIC_API_URL}/auth/oauth/vk/start`}
				variant="outline"
				class="min-h-11 w-full font-medium"
				aria-disabled={isOpeningVk}
				onclick={handleVkClick}
			>
				{#if isOpeningVk}
					<Spinner data-icon="inline-start" />
					Открываем VK ID…
				{:else}
					<IconVk class="text-[#0077FF]" data-icon="inline-start" />
					Войти через VK ID
				{/if}
			</Button>

			<Button
				type="button"
				variant="outline"
				class="min-h-11 w-full font-medium"
				onclick={showEmailLogin}
			>
				<Mail data-icon="inline-start" />
				Войти по почте
			</Button>
		{:else if view === 'email'}
			<CodeLoginForm bind:email onBack={showOptions} onPasswordLogin={showPasswordLogin} />
		{:else}
			<PasswordLoginForm bind:email onBack={showEmailLogin} />
		{/if}
	</div>
</Card.Root>
