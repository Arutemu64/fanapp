<script lang="ts">
	import { Button, Input, Label, Card, Spinner, Helper, Alert } from 'flowbite-svelte';
	import { getToastService } from '$lib/stores/toasts.svelte';
	import { client } from '$lib/api';
	import { goto } from '$app/navigation';
	import {
		EnvelopeSolid,
		UserSolid,
		LockSolid,
		EyeOutline,
		EyeSlashOutline
	} from 'flowbite-svelte-icons';

	let email = $state('');
	let username = $state('');
	let password = $state('');
	let isLoading = $state(false);
	let showPassword = $state(false);
	let serverError = $state('');

	const toastService = getToastService();

	function validateEmail(e: string): boolean {
		if (!e) return false;
		const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
		return emailRegex.test(e);
	}

	function validateUsername(u: string): boolean {
		if (!u) return false;
		return u.trim().length >= 3;
	}

	function validatePassword(p: string): boolean {
		if (!p) return false;
		if (p.length < 8 || p.length > 128) {
			return false;
		}
		const hasLetter = /[a-zA-Z]/.test(p);
		const hasNumber = /[0-9]/.test(p);
		return hasLetter && hasNumber;
	}

	const isEmailValid = $derived(email ? validateEmail(email) : null);
	const isUsernameValid = $derived(username ? validateUsername(username) : null);
	const isPasswordValid = $derived(password ? validatePassword(password) : null);

	const emailColor = $derived(email ? (isEmailValid ? 'green' : 'red') : undefined);
	const usernameColor = $derived(username ? (isUsernameValid ? 'green' : 'red') : undefined);
	const passwordColor = $derived(password ? (isPasswordValid ? 'green' : 'red') : undefined);

	async function handleSignup(e: Event) {
		e.preventDefault();

		serverError = '';

		const trimmedEmail = email.trim();
		const trimmedUsername = username.trim();

		if (!trimmedEmail || !trimmedUsername || !password) {
			serverError = 'Заполните все поля';
			return;
		}

		if (!validateEmail(trimmedEmail)) {
			serverError = 'Введите корректный email';
			return;
		}

		if (!validateUsername(trimmedUsername)) {
			serverError = 'Имя пользователя должно содержать минимум 3 символа';
			return;
		}

		if (!validatePassword(password)) {
			serverError =
				'Пароль должен быть от 8 до 128 символов и содержать хотя бы одну букву и одну цифру';
			return;
		}

		isLoading = true;

		try {
			const { error } = await client.POST('/auth/register', {
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
		} catch (err: unknown) {
			if (err instanceof Error) {
				serverError = err.message;
			} else {
				serverError = 'Произошла неизвестная ошибка при регистрации';
			}
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

			{#if serverError}
				<Alert color="red">
					{serverError}
				</Alert>
			{/if}

			<div class="space-y-2">
				<Label for="email" color={emailColor}>Email</Label>
				<Input
					id="email"
					type="email"
					bind:value={email}
					placeholder="Введите email"
					required
					size="md"
					class="ps-9"
					color={emailColor}
					disabled={isLoading}
				>
					{#snippet left()}
						<EnvelopeSolid class="h-5 w-5" />
					{/snippet}
				</Input>
				{#if email && isEmailValid === false}
					<Helper color="red">Введите корректный адрес электронной почты</Helper>
				{/if}
			</div>

			<div class="space-y-2">
				<Label for="username" color={usernameColor}>Имя пользователя</Label>
				<Input
					id="username"
					type="text"
					bind:value={username}
					placeholder="Введите имя пользователя"
					required
					color={usernameColor}
					disabled={isLoading}
					class="ps-9"
				>
					{#snippet left()}
						<UserSolid class="h-5 w-5" />
					{/snippet}
				</Input>
				{#if username && isUsernameValid === false}
					<Helper color="red">Имя пользователя должно содержать минимум 3 символа</Helper>
				{/if}
			</div>

			<div class="space-y-2">
				<Label for="password" color={passwordColor}>Пароль</Label>
				<Input
					id="password"
					type={showPassword ? 'text' : 'password'}
					bind:value={password}
					placeholder="Введите пароль"
					required
					color={passwordColor}
					disabled={isLoading}
					class="ps-9"
				>
					{#snippet left()}
						<LockSolid class="h-5 w-5" />
					{/snippet}
					{#snippet right()}
						<button
							type="button"
							class="pointer-events-auto"
							onclick={() => (showPassword = !showPassword)}
							aria-label="Показать пароль"
						>
							{#if showPassword}
								<EyeOutline class="h-5 w-5 text-gray-500 dark:text-gray-400" />
							{:else}
								<EyeSlashOutline class="h-5 w-5 text-gray-500 dark:text-gray-400" />
							{/if}
						</button>
					{/snippet}
				</Input>
				{#if password && isPasswordValid === false}
					<Helper color="red">
						Пароль должен быть от 8 до 128 символов и содержать хотя бы одну букву и одну цифру
					</Helper>
				{:else}
					<Helper class="text-sm">Минимум 8 символов, должна быть буква и цифра</Helper>
				{/if}
			</div>

			<Button type="submit" class="mt-4 min-h-11 w-full" disabled={isLoading}>
				{#if isLoading}
					<Spinner size="4" class="me-2" />
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
