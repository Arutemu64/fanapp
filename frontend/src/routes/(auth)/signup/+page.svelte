<script lang="ts">
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { Button, Input, Label, Card, Spinner, Helper, Alert } from 'flowbite-svelte';
	import { getToastService } from '$lib/services/toasts.svelte';
	import { client } from '$lib/api';
	import { getApiErrorDetail } from '$lib/api/errors';
	import { EnvelopeSolid, LockSolid, EyeOutline, EyeSlashOutline } from 'flowbite-svelte-icons';

	let email = $state('');
	let password = $state('');
	let emailError = $state('');
	let passwordError = $state('');
	let isLoading = $state(false);
	let showPassword = $state(false);
	let serverError = $state('');

	const toastService = getToastService();

	// Показываем базовую валидацию рядом с полями, чтобы форма читалась одинаково на всех auth-экранах.

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

	const emailColor = $derived(
		emailError ? 'red' : email ? (isEmailValid ? 'green' : 'red') : undefined
	);
	const passwordColor = $derived(
		passwordError ? 'red' : password ? (isPasswordValid ? 'green' : 'red') : undefined
	);

	function handleEmailInput() {
		emailError = '';
		serverError = '';
	}

	function handlePasswordInput() {
		passwordError = '';
		serverError = '';
	}

	async function handleSignup(e: Event) {
		e.preventDefault();

		serverError = '';
		emailError = '';
		passwordError = '';

		const trimmedEmail = email.trim();
		if (!trimmedEmail || !password) {
			if (!trimmedEmail) {
				emailError = 'Введи адрес эл. почты';
			}

			if (!password) {
				passwordError = 'Введи пароль';
			}

			return;
		}

		if (!validateEmail(trimmedEmail)) {
			emailError = 'Введи адрес в формате name@example.com';
			return;
		}

		if (!validatePassword(password)) {
			passwordError =
				'Пароль должен быть от 8 до 128 символов и содержать хотя бы одну букву и одну цифру';
			return;
		}

		isLoading = true;

		try {
			const { error, response } = await client.POST('/auth/register', {
				body: {
					email: trimmedEmail,
					password: password
				}
			});

			if (error) {
				console.error('Registration error:', error);

				if (response.status === 409) {
					emailError = getApiErrorDetail(error) ?? 'Этот адрес уже используется';
					return;
				}

				serverError = getApiErrorDetail(error) ?? 'Ошибка регистрации';
				return;
			}

			toastService.add('Аккаунт создан. Теперь войди в него.', 'success');
			await goto(resolve('/login'));
		} catch {
			serverError = 'Не удалось создать аккаунт. Попробуй ещё раз.';
		} finally {
			isLoading = false;
		}
	}
</script>

<Card class="w-full p-4 sm:p-6">
	<form onsubmit={handleSignup} class="space-y-4">
		<h2 class="text-center text-2xl font-bold text-gray-900 dark:text-white">
			Регистрация в ФАН ФАН
		</h2>

		{#if serverError}
			<Alert color="red">
				{serverError}
			</Alert>
		{/if}

		<div>
			<Label for="email" color={emailColor} class="mb-2">Эл. почта</Label>
			<Input
				id="email"
				name="email"
				type="email"
				bind:value={email}
				oninput={handleEmailInput}
				placeholder="name@example.com"
				autocomplete="email"
				inputmode="email"
				autocapitalize="off"
				spellcheck={false}
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
			{#if emailError}
				<Helper color="red" class="mt-1">{emailError}</Helper>
			{:else if email && isEmailValid === false}
				<Helper color="red" class="mt-1">Введи адрес в формате name@example.com</Helper>
			{/if}
		</div>

		<div>
			<Label for="password" color={passwordColor} class="mb-2">Пароль</Label>
			<Input
				id="password"
				name="password"
				type={showPassword ? 'text' : 'password'}
				bind:value={password}
				oninput={handlePasswordInput}
				placeholder="••••••••"
				autocomplete="new-password"
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
						aria-pressed={showPassword}
					>
						{#if showPassword}
							<EyeOutline class="h-5 w-5 text-gray-500 dark:text-gray-400" />
						{:else}
							<EyeSlashOutline class="h-5 w-5 text-gray-500 dark:text-gray-400" />
						{/if}
					</button>
				{/snippet}
			</Input>
			{#if passwordError}
				<Helper color="red" class="mt-1">{passwordError}</Helper>
			{:else if password && isPasswordValid === false}
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
			class="min-h-11 w-full rounded-xl font-medium"
			disabled={isLoading}
		>
			{#if isLoading}
				<Spinner size="4" class="mr-2" color="primary" />
				Создаём аккаунт…
			{:else}
				Зарегистрироваться
			{/if}
		</Button>

		<p class="text-center text-sm text-gray-500 dark:text-gray-400">
			Уже есть аккаунт?
			<a href={resolve('/login')} class="text-primary-600 hover:underline dark:text-primary-500">
				Войти
			</a>
		</p>
	</form>
</Card>
