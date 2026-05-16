<script lang="ts">
	import { PUBLIC_API_URL } from '$env/static/public';
	import { Button, Card, Tabs, TabItem } from 'flowbite-svelte';
	import IconTelegram from '~icons/simple-icons/telegram';
	import CodeLoginForm from './CodeLoginForm.svelte';
	import PasswordLoginForm from './PasswordLoginForm.svelte';

	let email = $state('');
	let isBusy = $state(false);
</script>

<svelte:head>
	<title>Вход — ФАН ФАН</title>
</svelte:head>

<Card class="w-full p-4 sm:p-6">
	<div class="space-y-4">
		<h2 class="text-center text-2xl font-bold text-gray-900 dark:text-white">Вход в ФАН ФАН</h2>

		<Tabs tabStyle="underline" classes={{ content: 'mt-3' }}>
			<TabItem open title="По коду">
				<CodeLoginForm bind:email bind:isBusy />
			</TabItem>

			<TabItem title="С паролем">
				<PasswordLoginForm bind:email bind:isBusy />
			</TabItem>
		</Tabs>

		<div class="relative flex items-center">
			<div class="grow border-t border-gray-200 dark:border-gray-700"></div>
			<span class="mx-4 shrink text-sm text-gray-400">или</span>
			<div class="grow border-t border-gray-200 dark:border-gray-700"></div>
		</div>

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
	</div>
</Card>
