<script lang="ts">
	import { Button, Input, Label, Card } from 'flowbite-svelte';
	import { toastService } from '$lib/stores/toasts.svelte';

	let username = $state('');
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
			// Send as form-urlencoded for OAuth2 compatibility
			const response = await fetch('http://127.0.0.1:8081/api/auth/token', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/x-www-form-urlencoded'
				},
				body: new URLSearchParams({
					username: username.trim(),
					password: password
				}),
				credentials: 'include'
			});

			if (!response.ok) {
				const errorData = await response.json().catch(() => null);
				throw new Error(errorData?.detail?.message || 'Ошибка авторизации');
			}
			toastService.add('Успешный вход!', 'success');
			window.location.href = '/';
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
			<h2 class="mb-6 text-center text-2xl font-bold text-gray-900 dark:text-white">Вход в FAN App</h2>

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

			<Button type="submit" class="w-full mt-4" disabled={isLoading}>
				{#if isLoading}
					<svg class="mr-2 h-4 w-4 animate-spin" viewBox="0 0 24 24">
						<circle
							class="opacity-25"
							cx="12"
							cy="12"
							r="10"
							stroke="currentColor"
							stroke-width="4"
							fill="none"
						/>
						<path
							class="opacity-75"
							fill="currentColor"
							d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
						/>
					</svg>
					Вход...
				{:else}
					Войти
				{/if}
			</Button>

			<p class="text-center text-sm text-gray-500 dark:text-gray-400">
				Нет аккаунта? <a href="/signup" class="text-primary-600 hover:underline dark:text-primary-500">Зарегистрироваться</a>
			</p>
		</form>
	</Card>
</div>
