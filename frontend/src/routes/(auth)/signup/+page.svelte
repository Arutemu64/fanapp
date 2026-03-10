<script lang="ts">
	import { Button, Input, Label, Card, Spinner, Helper, Alert } from 'flowbite-svelte';
	import { getToastService } from '$lib/stores/toasts.svelte';
	import { client } from '$lib/api';
	import { goto } from '$app/navigation';
	import { EnvelopeSolid, LockSolid, EyeOutline, EyeSlashOutline } from 'flowbite-svelte-icons';

	let email = $state('');
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
	const isPasswordValid = $derived(password ? validatePassword(password) : null);

	const emailColor = $derived(email ? (isEmailValid ? 'green' : 'red') : undefined);
	const passwordColor = $derived(password ? (isPasswordValid ? 'green' : 'red') : undefined);

	async function handleSignup(e: Event) {
		e.preventDefault();

		serverError = '';

		const trimmedEmail = email.trim();
		if (!trimmedEmail || !password) {
			serverError = 'Заполните все поля';
			return;
		}

		if (!validateEmail(trimmedEmail)) {
			serverError = 'Введите корректный email';
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

<Card class="w-full p-4 sm:p-6">
	<form onsubmit={handleSignup} class="space-y-4">
		<h2 class="text-center text-2xl font-bold text-gray-900 dark:text-white">
			Регистрация в FAN App
		</h2>

		{#if serverError}
			<Alert color="red">
				{serverError}
			</Alert>
		{/if}

		<div>
			<Label for="email" color={emailColor} class="mb-2">Email</Label>
			<Input
				id="email"
				type="email"
				bind:value={email}
				placeholder="you@example.com"
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
				<Helper color="red" class="mt-1">Введите корректный адрес электронной почты</Helper>
			{/if}
		</div>

		<div>
			<Label for="password" color={passwordColor} class="mb-2">Пароль</Label>
			<Input
				id="password"
				type={showPassword ? 'text' : 'password'}
				bind:value={password}
				placeholder="••••••••"
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
						aria-label={showPassword ? 'Скрыть пароль' : 'Показать пароль'}
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
				<Helper color="red" class="mt-1">
					Пароль должен быть от 8 до 128 символов и содержать хотя бы одну букву и одну цифру
				</Helper>
			{:else}
				<Helper class="mt-1 text-sm">Минимум 8 символов, должна быть буква и цифра</Helper>
			{/if}
		</div>

		<Button
			type="submit"
			color="primary"
			class="min-h-11 w-full rounded-xl font-medium transition-all hover:-translate-y-0.5 hover:shadow-md"
			disabled={isLoading}
		>
			{#if isLoading}
				<Spinner size="4" class="mr-2" color="primary" />
				Регистрация...
			{:else}
				Зарегистрироваться
			{/if}
		</Button>

		<p class="text-center text-sm text-gray-500 dark:text-gray-400">
			Уже есть аккаунт?
			<a href="/login" class="text-primary-600 hover:underline dark:text-primary-500">Войти</a>
		</p>
	</form>
</Card>
