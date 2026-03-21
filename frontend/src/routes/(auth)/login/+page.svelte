<script lang="ts">
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { PUBLIC_API_URL } from '$env/static/public';
	import { client } from '$lib/api';
	import { getEventsClient } from '$lib/services/events.svelte';
	import { getToastService } from '$lib/services/toasts.svelte';
	import {
		Alert,
		Button,
		Card,
		Helper,
		Input,
		Label,
		Spinner,
		Tabs,
		TabItem
	} from 'flowbite-svelte';
	import { EnvelopeSolid, EyeOutline, EyeSlashOutline, LockSolid } from 'flowbite-svelte-icons';

	type ActiveAction = 'password' | 'magic' | null;

	let email = $state('');
	let password = $state('');
	let magicLinkSentTo = $state('');
	let activeAction = $state<ActiveAction>(null);
	let showPassword = $state(false);
	let emailError = $state('');
	let passwordError = $state('');

	const eventsClient = getEventsClient();
	const toastService = getToastService();
	const isBusy = $derived(activeAction !== null);

	function validateEmail(value: string): boolean {
		if (!value) return false;
		const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
		return emailRegex.test(value);
	}

	function getNormalizedEmail(): string {
		return email.trim().toLowerCase();
	}

	// Держим ошибки рядом с полями, чтобы пользователь мог исправить ввод без лишних toast-сообщений.
	let normalizedEmail = $derived(getNormalizedEmail());
	let isEmailValid = $derived(email ? validateEmail(normalizedEmail) : null);
	let emailColor = $derived.by((): 'green' | 'red' | undefined => {
		if (emailError) {
			return 'red';
		}

		if (!email) {
			return undefined;
		}

		return isEmailValid ? 'green' : 'red';
	});
	let passwordColor = $derived.by((): 'red' | undefined => {
		return passwordError ? 'red' : undefined;
	});

	function resetEmailFeedback() {
		emailError = '';
		magicLinkSentTo = '';
	}

	function resetPasswordFeedback() {
		passwordError = '';
	}

	function validateMagicLinkForm(): boolean {
		emailError = '';
		passwordError = '';

		if (!normalizedEmail) {
			emailError = 'Введите адрес эл. почты';
			return false;
		}

		if (!validateEmail(normalizedEmail)) {
			emailError = 'Введите адрес в формате name@example.com';
			return false;
		}

		return true;
	}

	function validatePasswordForm(): boolean {
		emailError = '';
		passwordError = '';

		if (!normalizedEmail) {
			emailError = 'Введите адрес эл. почты';
		} else if (!validateEmail(normalizedEmail)) {
			emailError = 'Введите адрес в формате name@example.com';
		}

		if (!password.trim()) {
			passwordError = 'Введите пароль';
		}

		return !emailError && !passwordError;
	}

	async function finishLogin(successMessage: string) {
		toastService.add(successMessage, 'success');
		await goto(resolve('/'), { invalidateAll: true });
		eventsClient?.restart();
	}

	async function submitPasswordLogin() {
		if (!validatePasswordForm()) {
			return;
		}

		const trimmedEmail = normalizedEmail;

		activeAction = 'password';
		magicLinkSentTo = '';

		try {
			const { error } = await client.POST('/auth/login', {
				body: {
					email: trimmedEmail,
					password
				},
				headers: {
					'Content-Type': 'application/x-www-form-urlencoded'
				}
			});

			if (error) {
				console.error('Login error:', error);
				toastService.error(error);
				return;
			}

			await finishLogin('Вход выполнен');
		} catch (error) {
			toastService.error(error);
		} finally {
			activeAction = null;
		}
	}

	async function handleMagicLinkRequest() {
		if (!validateMagicLinkForm()) {
			return;
		}

		const trimmedEmail = normalizedEmail;

		activeAction = 'magic';
		magicLinkSentTo = '';

		try {
			const { error } = await client.POST('/auth/request-magic-link', {
				body: {
					email: trimmedEmail
				}
			});

			if (error) {
				console.error('Magic link request error:', error);
				toastService.error(error);
				return;
			}

			magicLinkSentTo = trimmedEmail;
		} catch (error) {
			toastService.error(error);
		} finally {
			activeAction = null;
		}
	}

	function handleMagicLinkSubmit(event: SubmitEvent) {
		event.preventDefault();

		if (isBusy) {
			return;
		}

		void handleMagicLinkRequest();
	}

	function handlePasswordSubmit(event: SubmitEvent) {
		event.preventDefault();

		if (isBusy) {
			return;
		}

		void submitPasswordLogin();
	}
</script>

<Card class="w-full p-4 sm:p-6">
	<div class="space-y-4">
		<h2 class="text-center text-2xl font-bold text-gray-900 dark:text-white">Вход в FAN FAN</h2>

		<Tabs tabStyle="underline" contentClass="mt-3">
			<TabItem open title="По ссылке">
				<form onsubmit={handleMagicLinkSubmit} class="space-y-3">
					<div>
						<Label for="magic-email" color={emailColor} class="mb-2">Эл. почта</Label>
						<Input
							id="magic-email"
							name="email"
							type="email"
							bind:value={email}
							placeholder="name@example.com"
							autocomplete="email"
							inputmode="email"
							autocapitalize="off"
							spellcheck={false}
							required
							disabled={isBusy}
							class="ps-9"
							color={emailColor}
							oninput={resetEmailFeedback}
						>
							{#snippet left()}
								<EnvelopeSolid class="h-5 w-5" />
							{/snippet}
						</Input>
						{#if emailError}
							<Helper color="red" class="mt-1">{emailError}</Helper>
						{:else if email && isEmailValid === false}
							<Helper color="red" class="mt-1">Введите адрес в формате name@example.com</Helper>
						{/if}
					</div>

					{#if magicLinkSentTo}
						<Alert color="green">
							Ссылка отправлена на <span class="font-medium">{magicLinkSentTo}</span>
						</Alert>
					{/if}

					<Button
						type="submit"
						color="primary"
						class="min-h-11 w-full rounded-xl font-medium"
						disabled={isBusy}
					>
						{#if activeAction === 'magic'}
							<Spinner size="4" class="mr-2" color="primary" />
							Отправляем…
						{:else}
							Отправить ссылку
						{/if}
					</Button>
				</form>
			</TabItem>

			<TabItem title="С паролем">
				<form onsubmit={handlePasswordSubmit} class="space-y-4">
					<div>
						<Label for="password-email" color={emailColor} class="mb-2">Эл. почта</Label>
						<Input
							id="password-email"
							name="email"
							type="email"
							bind:value={email}
							placeholder="name@example.com"
							autocomplete="username"
							inputmode="email"
							autocapitalize="off"
							spellcheck={false}
							required
							disabled={isBusy}
							class="ps-9"
							color={emailColor}
							oninput={resetEmailFeedback}
						>
							{#snippet left()}
								<EnvelopeSolid class="h-5 w-5" />
							{/snippet}
						</Input>
						{#if emailError}
							<Helper color="red" class="mt-1">{emailError}</Helper>
						{:else if email && isEmailValid === false}
							<Helper color="red" class="mt-1">Введите адрес в формате name@example.com</Helper>
						{/if}
					</div>

					<div>
						<Label for="password" class="mb-2">Пароль</Label>
						<Input
							id="password"
							name="password"
							type={showPassword ? 'text' : 'password'}
							bind:value={password}
							placeholder="••••••••"
							autocomplete="current-password"
							required
							disabled={isBusy}
							class="ps-9"
							color={passwordColor}
							oninput={resetPasswordFeedback}
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
						{/if}
					</div>

					<Button
						type="submit"
						color="primary"
						class="min-h-11 w-full rounded-xl font-medium"
						disabled={isBusy}
					>
						{#if activeAction === 'password'}
							<Spinner size="4" class="mr-2" color="primary" />
							Входим…
						{:else}
							Войти
						{/if}
					</Button>

					<p class="text-center text-sm text-gray-500 dark:text-gray-400">
						Нет аккаунта?
						<a
							href={resolve('/signup')}
							class="text-primary-600 hover:underline dark:text-primary-500"
						>
							Зарегистрироваться
						</a>
					</p>
				</form>
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
				Войти через Telegram
			</Button>
		</div>
	</div>
</Card>
