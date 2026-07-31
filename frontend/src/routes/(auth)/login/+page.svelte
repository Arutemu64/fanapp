<script lang="ts">
	import { PUBLIC_API_URL } from '$env/static/public';
	import { getToastService } from '$lib/services/toasts.svelte';
	import { clearOAuthErrorParam, OAUTH_LOGIN_ERROR_PARAM } from '$lib/utils/oauthErrors';
	import { Button, Card, Spinner } from 'flowbite-svelte';
	import { onMount } from 'svelte';
	import IconTelegram from '~icons/simple-icons/telegram';

	import type { PageProps } from './$types';

	import CodeLoginForm from './components/CodeLoginForm.svelte';
	import PasswordLoginForm from './components/PasswordLoginForm.svelte';

	let { data }: PageProps = $props();
	const toastService = getToastService();

	let email = $state('');
	let showPasswordForm = $state(false);
	// CodeLoginForm owns the send; we only need to know whether it happened, so
	// this is derived from its state rather than mirrored into a second flag.
	let codeSentTo = $state('');
	let isWaitingForCode = $derived(!!codeSentTo);

	// Cancelling is the user's own choice, so it gets an informational toast —
	// only a flow that actually broke reads as an error.
	const loginErrorToasts = {
		cancelled: { message: 'Вход через Telegram отменён.', type: 'info' },
		failed: { message: 'Не удалось войти через Telegram. Попробуй ещё раз.', type: 'error' }
	} as const;

	// Starting Telegram login is a full-page navigation that waits on our backend
	// and on Telegram's discovery document, so the button has to say it was heard.
	let isOpeningTelegram = $state(false);

	function handleTelegramClick(event: MouseEvent) {
		// A second tap during the wait would burn another OAuth state for nothing.
		if (isOpeningTelegram) {
			event.preventDefault();
			return;
		}

		isOpeningTelegram = true;
	}

	onMount(() => {
		const loginError = data.oauthLoginError;

		if (!loginError) return;

		const toast = loginErrorToasts[loginError];
		toastService.add(toast.message, toast.type);

		clearOAuthErrorParam(OAUTH_LOGIN_ERROR_PARAM);
	});
</script>

<!-- Coming back from Telegram restores this page from the bfcache with its DOM
	frozen mid-navigation, so the spinner would still be running. `pageshow` fires
	on that restore (and on a normal load, where the flag is already false). -->
<svelte:window onpageshow={() => (isOpeningTelegram = false)} />

<svelte:head>
	<title>Вход или регистрация · ФАН ФАН</title>
</svelte:head>

<Card class="w-full p-4 sm:p-6">
	<div class="space-y-4">
		<h2 class="text-center text-2xl font-bold text-gray-900 dark:text-white">
			Вход или регистрация
		</h2>

		{#if !showPasswordForm}
			{#if !isWaitingForCode}
				<!-- Use the configured API base so OAuth works in every environment.
					Flowbite drops `disabled` on an href Button (it renders a bare <a>),
					so the pending state is aria-disabled plus the guard in the handler. -->
				<Button
					href={`${PUBLIC_API_URL}/auth/oauth/telegram/start`}
					color="alternative"
					class="min-h-11 w-full rounded-xl font-medium"
					aria-disabled={isOpeningTelegram}
					onclick={handleTelegramClick}
				>
					{#if isOpeningTelegram}
						<Spinner class="me-2 h-5 w-5" />
						Открываем Telegram…
					{:else}
						<IconTelegram class="me-2 h-5 w-5 text-sky-500" />
						Войти через Telegram
					{/if}
				</Button>

				<div class="relative flex items-center">
					<div class="grow border-t border-gray-200 dark:border-gray-700"></div>
					<span class="mx-4 shrink text-sm text-gray-400">или</span>
					<div class="grow border-t border-gray-200 dark:border-gray-700"></div>
				</div>
			{/if}

			<CodeLoginForm bind:email bind:showPasswordForm bind:codeSentTo />
		{:else}
			<PasswordLoginForm bind:email onBack={() => (showPasswordForm = false)} />
		{/if}
	</div>
</Card>
