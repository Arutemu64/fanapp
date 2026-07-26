<script lang="ts">
	import { PUBLIC_API_URL } from '$env/static/public';
	import { Button, Card } from 'flowbite-svelte';
	import IconTelegram from '~icons/simple-icons/telegram';

	import CodeLoginForm from './components/CodeLoginForm.svelte';
	import PasswordLoginForm from './components/PasswordLoginForm.svelte';

	let email = $state('');
	let showPasswordForm = $state(false);
	// CodeLoginForm owns the send; we only need to know whether it happened, so
	// this is derived from its state rather than mirrored into a second flag.
	let codeSentTo = $state('');
	let isWaitingForCode = $derived(!!codeSentTo);
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
				<div class="flex justify-center">
					<!-- Use the configured API base so OAuth works in every environment. -->
					<Button
						href={`${PUBLIC_API_URL}/auth/login/telegram`}
						color="alternative"
						class="min-h-11 w-full rounded-xl font-medium"
					>
						<IconTelegram class="me-2 h-5 w-5 text-sky-500" />
						Войти через Telegram
					</Button>
				</div>

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
