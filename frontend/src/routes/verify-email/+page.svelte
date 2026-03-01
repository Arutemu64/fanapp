<script lang="ts">
	import { onMount } from 'svelte';
	import { client } from '$lib/api';
	import { Card, Button, Spinner } from 'flowbite-svelte';
	import { CheckCircleOutline, CloseCircleOutline } from 'flowbite-svelte-icons';

	let { data } = $props();

	let verificationStatus: 'loading' | 'success' | 'error' = $state('loading');
	let errorMessage: string = $state('');

	onMount(async () => {
		if (!data.token) {
			verificationStatus = 'error';
			errorMessage = 'Токен не найден';
			return;
		}

		try {
			const { error } = await client.POST('/auth/verify-email', {
				body: { token: data.token } as any
			});

			if (error) {
				console.error('Email verification error:', error);
				errorMessage =
					typeof error.detail === 'string' ? error.detail : 'Недействительный или истекший токен';
				verificationStatus = 'error';
			} else {
				verificationStatus = 'success';
			}
		} catch (err) {
			console.error('Unexpected error:', err);
			verificationStatus = 'error';
			errorMessage = 'Произошла ошибка при проверке почты';
		}
	});
</script>

<div class="flex h-full items-center justify-center p-4">
	<Card class="w-full max-w-md p-6 text-center sm:p-8">
		<div class="flex flex-col items-center justify-center">
			{#if verificationStatus === 'loading'}
				<Spinner size="8" class="mb-4" />
				<h2 class="mb-2 text-xl font-bold text-gray-900 dark:text-white">Проверка почты...</h2>
				<p class="text-gray-500 dark:text-gray-400">
					Пожалуйста, подождите, мы проверяем ваш токен.
				</p>
			{:else if verificationStatus === 'success'}
				<CheckCircleOutline class="mx-auto mb-4 h-16 w-16 text-green-500" />
				<h2 class="mb-2 text-xl font-bold text-gray-900 dark:text-white">
					Почта успешно подтверждена!
				</h2>
				<p class="mb-6 text-gray-500 dark:text-gray-400">
					Вы можете закрыть эту страницу или перейти в приложение.
				</p>
				<Button
					href="/"
					class="min-h-11 w-full rounded-xl transition-all hover:-translate-y-0.5 hover:shadow-md"
					>Перейти на главную</Button
				>
			{:else}
				<CloseCircleOutline class="mx-auto mb-4 h-16 w-16 text-red-500" />
				<h2 class="mb-2 text-xl font-bold text-gray-900 dark:text-white">Ошибка проверки</h2>
				<p class="mb-6 text-gray-500 dark:text-gray-400">
					{errorMessage}
				</p>
				<Button
					href="/login"
					outline
					color="dark"
					class="min-h-11 w-full rounded-xl transition-all hover:-translate-y-0.5 hover:shadow-md"
				>
					Вернуться ко входу
				</Button>
			{/if}
		</div>
	</Card>
</div>
