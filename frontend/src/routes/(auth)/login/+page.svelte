<script lang="ts">
	import { PUBLIC_API_URL } from '$env/static/public';
	import { getToastService } from '$lib/services/toasts.svelte';
	import { clearOAuthErrorParam, OAUTH_LOGIN_ERROR_PARAM } from '$lib/utils/oauthErrors';
	import { Button, Card, Spinner } from 'flowbite-svelte';
	import { EnvelopeSolid } from 'flowbite-svelte-icons';
	import { onMount } from 'svelte';
	import IconTelegram from '~icons/simple-icons/telegram';
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
	let isOpeningTelegram = $state(false);
	let isOpeningVk = $state(false);

	function handleTelegramClick(event: MouseEvent) {
		if (isOpeningTelegram) {
			event.preventDefault();
			return;
		}

		isOpeningTelegram = true;
	}

	function handleVkClick(event: MouseEvent) {
		if (isOpeningVk) {
			event.preventDefault();
			return;
		}

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
		isOpeningTelegram = false;
		isOpeningVk = false;
	}}
/>

<svelte:head>
	<title>Вход · ФАН ФАН</title>
</svelte:head>

<Card class="w-full rounded-2xl p-4 sm:p-6">
	<div class="space-y-4">
		<div class="space-y-1 text-center">
			<h1 class="text-2xl font-bold text-gray-900 dark:text-white">Вход в ФАН ФАН</h1>
			{#if view === 'options'}
				<!-- Benefits belong on the entry screen only: once a method is chosen the
					sub-steps are the task, not the pitch. -->
				<p class="text-sm text-gray-600 dark:text-gray-400">
					Голосуй за выступления, получай уведомления и оставляй обратную связь.
				</p>
			{/if}
		</div>

		{#if view === 'options'}
			<!-- Use the configured API base so OAuth works in every environment.
				Flowbite drops `disabled` on an href Button (it renders a bare <a>),
				so the pending state is aria-disabled plus the guard in the handler. -->
			<Button
				href={`${PUBLIC_API_URL}/auth/oauth/telegram/start`}
				color="alternative"
				class="min-h-11 w-full font-medium"
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

			<Button
				href={`${PUBLIC_API_URL}/auth/oauth/vk/start`}
				color="alternative"
				class="min-h-11 w-full font-medium"
				aria-disabled={isOpeningVk}
				onclick={handleVkClick}
			>
				{#if isOpeningVk}
					<Spinner class="me-2 h-5 w-5" />
					Открываем VK ID…
				{:else}
					<IconVk class="me-2 h-5 w-5 text-[#0077FF]" />
					Войти через VK ID
				{/if}
			</Button>

			<Button
				type="button"
				color="alternative"
				class="min-h-11 w-full font-medium"
				onclick={showEmailLogin}
			>
				<EnvelopeSolid class="me-2 h-5 w-5" />
				Войти по почте
			</Button>
		{:else if view === 'email'}
			<CodeLoginForm bind:email onBack={showOptions} onPasswordLogin={showPasswordLogin} />
		{:else}
			<PasswordLoginForm bind:email onBack={showEmailLogin} />
		{/if}
	</div>
</Card>
