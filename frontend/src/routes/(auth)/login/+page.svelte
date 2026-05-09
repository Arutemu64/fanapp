<script lang="ts">
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { PUBLIC_API_URL } from '$env/static/public';
	import { client } from '$lib/api';
	import { getApiErrorDetail } from '$lib/api/errors';
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

	type ActiveAction = 'password' | 'code-request' | 'code-login' | null;

	let email = $state('');
	let password = $state('');
	let loginCode = $state('');
	let codeSentTo = $state('');
	let activeAction = $state<ActiveAction>(null);
	let showPassword = $state(false);
	let emailError = $state('');
	let passwordError = $state('');
	let loginCodeError = $state('');

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
		loginCodeError = '';
		codeSentTo = '';
		loginCode = '';
	}

	function resetPasswordFeedback() {
		passwordError = '';
	}

	function resetLoginCodeFeedback() {
		loginCodeError = '';
	}

	function validateEmailCodeRequestForm(): boolean {
		emailError = '';
		passwordError = '';
		loginCodeError = '';

		if (!normalizedEmail) {
			emailError = 'Введи адрес эл. почты';
			return false;
		}

		if (!validateEmail(normalizedEmail)) {
			emailError = 'Введи адрес в формате name@example.com';
			return false;
		}

		return true;
	}

	function validateEmailCodeLoginForm(): boolean {
		if (!validateEmailCodeRequestForm()) {
			return false;
		}

		if (!loginCode.trim()) {
			loginCodeError = 'Введи код из письма';
			return false;
		}

		if (!/^\d{6}$/.test(loginCode.trim())) {
			loginCodeError = 'Код должен состоять из 6 цифр';
			return false;
		}

		return true;
	}

	function validatePasswordForm(): boolean {
		emailError = '';
		passwordError = '';

		if (!normalizedEmail) {
			emailError = 'Введи адрес эл. почты';
		} else if (!validateEmail(normalizedEmail)) {
			emailError = 'Введи адрес в формате name@example.com';
		}

		if (!password.trim()) {
			passwordError = 'Введи пароль';
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
		codeSentTo = '';
		loginCode = '';
		loginCodeError = '';

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

	async function handleLoginCodeRequest() {
		if (!validateEmailCodeRequestForm()) {
			return;
		}

		const trimmedEmail = normalizedEmail;

		activeAction = 'code-request';
		codeSentTo = '';
		loginCodeError = '';

		try {
			const { error } = await client.POST('/auth/request-login-code', {
				body: {
					email: trimmedEmail
				}
			});

			if (error) {
				console.error('Login code request error:', error);
				toastService.error(error);
				return;
			}

			codeSentTo = trimmedEmail;
			loginCode = '';
		} catch (error) {
			toastService.error(error);
		} finally {
			activeAction = null;
		}
	}

	async function submitLoginCode() {
		if (!validateEmailCodeLoginForm()) {
			return;
		}

		activeAction = 'code-login';
		loginCodeError = '';

		try {
			const { error, response } = await client.POST('/auth/login-with-code', {
				body: {
					email: normalizedEmail,
					code: loginCode.trim()
				}
			});

			if (error) {
				if (response.status === 400) {
					loginCodeError = getApiErrorDetail(error) ?? 'Неверный или устаревший код';
					return;
				}

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

	function handleCodeRequestSubmit(event: SubmitEvent) {
		event.preventDefault();

		if (isBusy) {
			return;
		}

		const submitterAction =
			event.submitter instanceof HTMLButtonElement ? event.submitter.dataset.action : null;

		if (submitterAction === 'login' || (!submitterAction && codeSentTo)) {
			void submitLoginCode();
			return;
		}

		void handleLoginCodeRequest();
	}

	function handlePasswordSubmit(event: SubmitEvent) {
		event.preventDefault();

		if (isBusy) {
			return;
		}

		void submitPasswordLogin();
	}
</script>

<svelte:head>
	<title>Вход — ФАН ФАН</title>
</svelte:head>

<Card class="w-full p-4 sm:p-6">
	<div class="space-y-4">
		<h2 class="text-center text-2xl font-bold text-gray-900 dark:text-white">Вход в ФАН ФАН</h2>

		<Tabs tabStyle="underline" classes={{ content: 'mt-3' }}>
			<TabItem open title="По коду">
				<form onsubmit={handleCodeRequestSubmit} class="space-y-3">
					<div>
						<Label for="code-email" color={emailColor} class="mb-2">Эл. почта</Label>
						<Input
							id="code-email"
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
							<Helper color="red" class="mt-1">Введи адрес в формате name@example.com</Helper>
						{/if}
					</div>

					{#if codeSentTo}
						<Alert color="green">
							Код отправлен на <span class="font-medium">{codeSentTo}</span>. Не забудьте проверить
							папку "Спам"
						</Alert>
					{/if}

					{#if codeSentTo}
						<div>
							<Label for="login-code" class="mb-2">Код из письма</Label>
							<Input
								id="login-code"
								name="code"
								type="text"
								bind:value={loginCode}
								placeholder="******"
								autocomplete="one-time-code"
								inputmode="numeric"
								pattern="[0-9]*"
								maxlength={6}
								disabled={isBusy}
								class="text-center text-lg tracking-widest"
								color={loginCodeError ? 'red' : undefined}
								oninput={() => {
									loginCode = loginCode.replace(/\D/g, '').slice(0, 6);
									resetLoginCodeFeedback();
								}}
							/>
							{#if loginCodeError}
								<Helper color="red" class="mt-1">{loginCodeError}</Helper>
							{:else}
								<Helper class="mt-1">Введи 6 цифр из письма.</Helper>
							{/if}
						</div>
					{/if}

					{#if codeSentTo}
						<Button
							type="submit"
							data-action="login"
							color="primary"
							autofocus
							class="min-h-11 w-full rounded-xl font-medium"
							disabled={isBusy}
						>
							{#if activeAction === 'code-login'}
								<Spinner size="4" class="mr-2" color="primary" />
								Проверяем…
							{:else}
								Войти по коду
							{/if}
						</Button>

						<Button
							type="button"
							color="alternative"
							class="min-h-11 w-full rounded-xl font-medium"
							disabled={isBusy}
							onclick={() => void handleLoginCodeRequest()}
						>
							{#if activeAction === 'code-request'}
								<Spinner size="4" class="mr-2" color="primary" />
								Отправляем…
							{:else}
								Отправить код ещё раз
							{/if}
						</Button>
					{:else}
						<Button
							type="submit"
							data-action="request"
							color="primary"
							class="min-h-11 w-full rounded-xl font-medium"
							disabled={isBusy}
						>
							{#if activeAction === 'code-request'}
								<Spinner size="4" class="mr-2" color="primary" />
								Отправляем…
							{:else}
								Получить код
							{/if}
						</Button>
					{/if}
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
							<Helper color="red" class="mt-1">Введи адрес в формате name@example.com</Helper>
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
									class="pointer-events-auto -m-1 rounded-md p-1 hover:bg-gray-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 dark:hover:bg-gray-700"
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
