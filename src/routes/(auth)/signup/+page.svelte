<script lang="ts">
	import { Button, Input, Label, Card } from 'flowbite-svelte';
	import { toastService } from '$lib/stores/toasts.svelte';
	import { client } from '$lib/api';
	import { goto } from '$app/navigation';

	let email = $state('');
	let username = $state('');
	let password = $state('');
	let isLoading = $state(false);

	function validateEmail(email: string): boolean {
		const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
		return emailRegex.test(email);
	}

	function validateUsername(username: string): boolean {
		return username.trim().length >= 3;
	}

	function validatePassword(password: string): boolean {
		if (password.length < 8 || password.length > 128) {
			return false;
		}
		const hasLetter = /[a-zA-Z]/.test(password);
		const hasNumber = /[0-9]/.test(password);
		return hasLetter && hasNumber;
	}

	async function handleSignup(e: Event) {
		e.preventDefault();

		const trimmedEmail = email.trim();
		const trimmedUsername = username.trim();

		if (!trimmedEmail || !trimmedUsername || !password) {
			toastService.add('Заполните все поля', 'warning');
			return;
		}

		if (!validateEmail(trimmedEmail)) {
			toastService.add('Введите корректный email', 'warning');
			return;
		}

		if (!validateUsername(trimmedUsername)) {
			toastService.add('Имя пользователя должно содержать минимум 3 символа', 'warning');
			return;
		}

		if (!validatePassword(password)) {
			toastService.add(
				'Пароль должен быть от 8 до 128 символов и содержать хотя бы одну букву и одну цифру',
				'warning'
			);
			return;
		}

		isLoading = true;

		try {
			const { data, error, response } = await client.POST('/auth/register', {
				body: {
					email: trimmedEmail,
					username: trimmedUsername,
					password: password
				}
			});

			if (error) {
				console.error('Registration error:', error);
				const errorMessage = typeof error.detail === 'string' ? error.detail : 'Ошибка регистрации';
				throw new Error(errorMessage);
			}

			toastService.add('Регистрация успешна! Войдите в аккаунт.', 'success');
			goto('/login');
		} catch (err) {
			toastService.error(err);
		} finally {
			isLoading = false;
		}
	}
</script>

<div class="flex h-full items-center justify-center">
	<Card class="w-full max-w-md p-6 sm:p-8">
		<form onsubmit={handleSignup} class="space-y-6">
			<h2 class="mb-6 text-center text-2xl font-bold text-gray-900 dark:text-white">
				Регистрация в FAN App
			</h2>

			<div class="space-y-2">
				<Label for="email">Email</Label>
				<Input
					id="email"
					type="email"
					bind:value={email}
					placeholder="Введите email"
					required
					disabled={isLoading}
				/>
			</div>

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
				<p class="text-sm text-gray-500 dark:text-gray-400">
					Минимум 8 символов, должна быть буква и цифра
				</p>
			</div>

			<Button type="submit" class="mt-4 min-h-11 w-full" disabled={isLoading}>
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
					Регистрация...
				{:else}
					Зарегистрироваться
				{/if}
			</Button>

			<p class="text-center text-sm text-gray-500 dark:text-gray-400">
				Уже есть аккаунт? <a
					href="/login"
					class="text-primary-600 hover:underline dark:text-primary-500">Войти</a
				>
			</p>
		</form>
	</Card>
</div>
