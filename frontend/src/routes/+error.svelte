<script lang="ts">
	import { page } from '$app/state';
	import { Card, Button } from 'flowbite-svelte';
	import {
		ExclamationCircleSolid,
		LockSolid,
		ArrowLeftOutline
	} from 'flowbite-svelte-icons';

	// Reactive states based on page status and error messages
	let status = $derived(page.status);
	let errorMessage = $derived(page.error?.message);

	let title = $derived.by(() => {
		if (status === 403) return 'Доступ ограничен';
		if (status === 404) return 'Страница не найдена';
		return 'Что-то пошло не так';
	});

	let description = $derived.by(() => {
		if (errorMessage) return errorMessage;
		if (status === 403) return 'У тебя нет прав для просмотра этой страницы.';
		if (status === 404) return 'Похоже, эта страница не существует, была удалена или перенесена.';
		return 'Произошла непредвиденная ошибка на сервере или отсутствует интернет-соединение.';
	});

	function handleGoBack() {
		if (typeof window !== 'undefined') {
			window.history.back();
		}
	}

	function handleRetry() {
		if (typeof window !== 'undefined') {
			window.location.reload();
		}
	}
</script>

<svelte:head>
	<title>{title} ({status})</title>
</svelte:head>

<div class="flex min-h-dvh items-center justify-center bg-gray-50 px-4 py-6 sm:py-10 dark:bg-gray-950">
	<Card class="w-full max-w-md p-6 text-center sm:p-8">
		<div class="flex flex-col items-center justify-center">
			<!-- Visual Icon -->
			{#if status === 403}
				<div class="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-red-100 text-red-500 dark:bg-red-900/30 dark:text-red-400">
					<LockSolid class="h-8 w-8" />
				</div>
			{:else}
				<div class="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-red-100 text-red-500 dark:bg-red-900/30 dark:text-red-400">
					<ExclamationCircleSolid class="h-8 w-8" />
				</div>
			{/if}

			<!-- Status Code -->
			<span class="mb-1 text-xs font-semibold tracking-wider text-gray-400 uppercase dark:text-gray-500">
				Ошибка {status}
			</span>

			<!-- Title -->
			<h2 class="mb-2 text-xl font-bold text-gray-900 dark:text-white sm:text-2xl">
				{title}
			</h2>

			<!-- Description -->
			<p class="mb-6 text-sm text-gray-500 dark:text-gray-400">
				{description}
			</p>

			<!-- Action Buttons -->
			<div class="flex w-full flex-col gap-2">
				{#if status >= 500}
					<Button
						color="primary"
						class="min-h-11 w-full rounded-xl font-medium"
						onclick={handleRetry}
					>
						Попробовать снова
					</Button>
				{/if}

				<Button
					href="/"
					color={status >= 500 ? 'alternative' : 'primary'}
					class="min-h-11 w-full rounded-xl font-medium"
				>
					На главную
				</Button>

				<Button
					type="button"
					color="light"
					class="min-h-11 w-full rounded-xl font-medium"
					onclick={handleGoBack}
				>
					<ArrowLeftOutline class="me-2 h-4 w-4" />
					Вернуться назад
				</Button>
			</div>
		</div>
	</Card>
</div>
