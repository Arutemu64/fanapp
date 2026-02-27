<script lang="ts">
	import { Button, Input, Label, Card, Spinner } from 'flowbite-svelte';
	import { getToastService } from '$lib/stores/toasts.svelte';
	import { client } from '$lib/api';
	import { goto } from '$app/navigation';
	import { getEventsClient } from '$lib/events.svelte';

	let username = $state('');
	const eventsClient = getEventsClient();
	const toastService = getToastService();
	let password = $state('');
	let isLoading = $state(false);

	async function handleLogin(e: Event) {
		e.preventDefault();

		if (!username.trim() || !password.trim()) {
			toastService.add('Введите имя пользователя и пароль', 'warning');
			return;
		}

		isLoading = true;

		try {
			const { data, error, response } = await client.POST('/auth/login', {
				body: {
					username: username.trim(),
					password: password,
					scope: ''
				},
				headers: {
					'Content-Type': 'application/x-www-form-urlencoded'
				}
			});

			if (error) {
				console.error('Login error:', error);
				const errorMessage = typeof error.detail === 'string' ? error.detail : 'Ошибка авторизации';
				throw new Error(errorMessage);
			}

			toastService.add('Успешный вход!', 'success');
			eventsClient?.restart();
			goto('/', { invalidateAll: true });
		} catch (err) {
			toastService.error(err);
		} finally {
			isLoading = false;
		}
	}
</script>

<div class="flex h-full items-center justify-center">
	<Card class="w-full max-w-md p-6 sm:p-8">
		<form onsubmit={handleLogin} class="space-y-6">
			<h2 class="mb-6 text-center text-2xl font-bold text-gray-900 dark:text-white">
				Вход в FAN App
			</h2>

			<div class="space-y-2">
				<Label for="username">Имя пользователя</Label>
				<Input
					id="username"
					type="text"
					bind:value={username}
					placeholder="Введите имя пользователя"
					required
					disabled={isLoading}
				/>
			</div>

			<div class="space-y-2">
				<Label for="password">Пароль</Label>
				<Input
					id="password"
					type="password"
					bind:value={password}
					placeholder="Введите пароль"
					required
					disabled={isLoading}
				/>
			</div>

			<Button
				type="submit"
				class="mt-4 min-h-11 w-full rounded-xl font-medium transition-all hover:-translate-y-0.5 hover:shadow-md"
				disabled={isLoading}
			>
				{#if isLoading}
					<Spinner size="4" class="mr-2" color="gray" />
					Вход...
				{:else}
					Войти
				{/if}
			</Button>

			<p class="text-center text-sm text-gray-500 dark:text-gray-400">
				Нет аккаунта? <a
					href="/signup"
					class="text-primary-600 hover:underline dark:text-primary-500">Зарегистрироваться</a
				>
			</p>
		</form>
	</Card>
</div>
