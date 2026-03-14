<script lang="ts">
	import { Card, Button } from 'flowbite-svelte';
	import { CheckCircleOutline, CloseCircleOutline } from 'flowbite-svelte-icons';

	let { data } = $props();
</script>

<svelte:head>
	<title>Подтверждение почты</title>
</svelte:head>

<div class="flex h-full items-center justify-center p-4">
	<Card class="w-full max-w-md p-6 text-center sm:p-8">
		<div class="flex flex-col items-center justify-center">
			{#if data.status === 'success'}
				<CheckCircleOutline class="mx-auto mb-4 h-16 w-16 text-green-500" />
				<h2 class="mb-2 text-xl font-bold text-gray-900 dark:text-white">
					Почта успешно подтверждена!
				</h2>
				<p class="mb-6 text-gray-500 dark:text-gray-400">
					Вы можете закрыть эту страницу или перейти в приложение.
				</p>
				<Button
					href="/"
					class="min-h-11 w-full rounded-xl"
					>Перейти на главную</Button
				>
			{:else}
				<CloseCircleOutline class="mx-auto mb-4 h-16 w-16 text-red-500" />
				<h2 class="mb-2 text-xl font-bold text-gray-900 dark:text-white">Ошибка проверки</h2>
				<p class="mb-6 text-gray-500 dark:text-gray-400">
					{data.errorMessage}
				</p>
				<Button
					href="/login"
					outline
					color="dark"
					class="min-h-11 w-full rounded-xl"
				>
					Вернуться ко входу
				</Button>
			{/if}
		</div>
	</Card>
</div>
