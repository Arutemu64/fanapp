<script lang="ts">
	import { PUBLIC_API_URL } from '$env/static/public';
	import { Button, Card, Spinner } from 'flowbite-svelte';
	import IconTelegram from '~icons/simple-icons/telegram';

	import CodeLoginForm from './components/CodeLoginForm.svelte';
	import PasswordLoginForm from './components/PasswordLoginForm.svelte';

	let email = $state('');
	let showPasswordForm = $state(false);
	// CodeLoginForm owns the send; we only need to know whether it happened, so
	// this is derived from its state rather than mirrored into a second flag.
	let codeSentTo = $state('');
	let isWaitingForCode = $derived(!!codeSentTo);
	// The form submit is a native full-page navigation, so nothing here resets
	// this — the page unloads. It exists to keep the button from looking inert
	// while the browser waits for the redirect to Telegram.
	let isRedirectingToTelegram = $state(false);
</script>

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
				<!--
					A form POST, not a link: a GET flow-start is triggerable cross-site
					by any page (image, iframe, prefetch), which is why the endpoint now
					takes POST only and checks the request initiator. SvelteKit's router
					leaves non-GET submits to the browser, so this navigates natively.
					Use the configured API base so OAuth works in every environment.
				-->
				<form
					method="POST"
					action={`${PUBLIC_API_URL}/auth/login/telegram`}
					onsubmit={() => (isRedirectingToTelegram = true)}
				>
					<Button
						type="submit"
						color="alternative"
						class="min-h-11 w-full rounded-xl font-medium"
						disabled={isRedirectingToTelegram}
					>
						{#if isRedirectingToTelegram}
							<Spinner size="4" class="me-2" color="primary" />
							Переходим в Telegram…
						{:else}
							<IconTelegram class="me-2 h-5 w-5 text-sky-500" />
							Войти через Telegram
						{/if}
					</Button>
				</form>

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
