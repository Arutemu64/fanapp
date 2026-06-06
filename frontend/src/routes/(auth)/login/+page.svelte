<script lang="ts">
	import { env } from '$env/dynamic/public';
	import { Button, Card } from 'flowbite-svelte';
	import { ArrowLeftOutline } from 'flowbite-svelte-icons';
	import IconTelegram from '~icons/simple-icons/telegram';
	import CodeLoginForm from './CodeLoginForm.svelte';
	import PasswordLoginForm from './PasswordLoginForm.svelte';

	let email = $state('');
	let isBusy = $state(false);
	let showPasswordForm = $state(false);
	let isWaitingForCode = $state(false);
</script>

<svelte:head>
	<title>Вход или регистрация — ФАН ФАН</title>
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
						href={`${env.PUBLIC_API_URL}/auth/login/telegram`}
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

			<CodeLoginForm bind:email bind:isBusy bind:showPasswordForm bind:isWaitingForCode />
		{:else}
			<PasswordLoginForm bind:email bind:isBusy />
			<div class="mt-4 text-center">
				<Button color="light" class="w-full rounded-xl" onclick={() => (showPasswordForm = false)}>
					<ArrowLeftOutline class="me-2 h-4 w-4" />
					Назад
				</Button>
			</div>
		{/if}
	</div>
</Card>
