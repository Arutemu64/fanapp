<script lang="ts">
	import { goto } from '$app/navigation';
	import { browser } from '$app/environment';
	import { client } from '$lib/api';
	import type { components } from '$lib/api/v1';
	import { getEventsClient } from '$lib/events.svelte';
	import { getToastService } from '$lib/stores/toasts.svelte';
	import { Alert, Button, Card, Helper, Input, Label, Spinner } from 'flowbite-svelte';
	import { EnvelopeSolid, EyeOutline, EyeSlashOutline, LockSolid } from 'flowbite-svelte-icons';
	import { onMount } from 'svelte';

	type ActiveAction = 'password' | 'magic' | 'telegram' | null;
	type TelegramLoginPayload = components['schemas']['LoginTelegramCommand'];

	let email = $state('');
	let password = $state('');
	let passwordMode = $state(false);
	let magicLinkSentTo = $state('');
	let activeAction = $state<ActiveAction>(null);
	let showPassword = $state(false);

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

	async function finishLogin(successMessage: string) {
		toastService.add(successMessage, 'success');
		eventsClient?.restart();
		await goto('/', { invalidateAll: true });
	}

	async function submitPasswordLogin() {
		const trimmedEmail = getNormalizedEmail();

		if (!validateEmail(trimmedEmail) || !password.trim()) {
			toastService.add('Введите email и пароль', 'warning');
			return;
		}

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
		const trimmedEmail = getNormalizedEmail();
		if (!validateEmail(trimmedEmail)) {
			toastService.add('Введите корректный email', 'warning');
			return;
		}

		passwordMode = false;
		password = '';
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

			// Keep the success copy generic so the UI does not confirm whether the email exists.
			magicLinkSentTo = trimmedEmail;
		} catch (error) {
			toastService.error(error);
		} finally {
			activeAction = null;
		}
	}

	async function handlePasswordAction() {
		magicLinkSentTo = '';

		// The first tap switches the screen into password mode without duplicating the email field.
		if (!passwordMode) {
			passwordMode = true;
			return;
		}

		await submitPasswordLogin();
	}

	function handleEnterKey(event: KeyboardEvent) {
		if (event.key !== 'Enter' || isBusy) return;
		event.preventDefault();

		if (passwordMode) {
			void submitPasswordLogin();
			return;
		}

		void handleMagicLinkRequest();
	}

	async function handleTelegramLogin(user: TelegramLoginPayload) {
		activeAction = 'telegram';

		try {
			const { error } = await client.POST('/auth/login_telegram', {
				body: user
			});

			if (error) {
				console.error('Telegram login error:', error);
				toastService.error(error);
				return;
			}

			await finishLogin('Вход через Telegram выполнен');
		} catch (error) {
			toastService.error(error);
		} finally {
			activeAction = null;
		}
	}

	onMount(() => {
		if (!browser) return;

		// The widget calls this global callback after Telegram authentication succeeds.
		// @ts-expect-error Telegram script writes to window at runtime.
		window.onTelegramAuth = handleTelegramLogin;

		const script = document.createElement('script');
		script.src = 'https://telegram.org/js/telegram-widget.js?22';
		script.setAttribute('data-telegram-login', 'fanfanalpha_bot');
		script.setAttribute('data-size', 'large');
		script.setAttribute('data-radius', '12');
		script.setAttribute('data-onauth', 'onTelegramAuth(user)');
		script.setAttribute('data-request-access', 'write');
		script.async = true;

		const container = document.getElementById('telegram-login-container');
		if (container) {
			container.innerHTML = '';
			container.appendChild(script);
		}

		return () => {
			// @ts-expect-error Telegram script writes to window at runtime.
			delete window.onTelegramAuth;
		};
	});
</script>

<div class="flex h-full items-center justify-center p-4">
	<Card class="w-full max-w-md p-6 sm:p-8">
		<div class="space-y-6">
			<div class="space-y-2 text-center">
				<h2 class="text-2xl font-bold text-gray-900 dark:text-white">Вход в FAN App</h2>
				<p class="text-sm text-gray-500 dark:text-gray-400">
					Введите email. Ссылка для входа работает без пароля и создаёт аккаунт при первом входе.
				</p>
			</div>

			<div class="space-y-5">
				<div class="space-y-2">
					<Label for="email">Email</Label>
					<Input
						id="email"
						type="email"
						bind:value={email}
						placeholder="Введите email"
						required
						disabled={isBusy}
						class="ps-9"
						oninput={() => (magicLinkSentTo = '')}
						onkeydown={handleEnterKey}
					>
						{#snippet left()}
							<EnvelopeSolid class="h-5 w-5" />
						{/snippet}
					</Input>
					{#if passwordMode}
						<Helper>Для входа по паролю используйте этот email.</Helper>
					{:else}
						<Helper>Отправим одноразовую ссылку. Если аккаунта ещё нет, создадим его автоматически.</Helper>
					{/if}
				</div>

				{#if passwordMode}
					<div class="space-y-2">
						<Label for="password">Пароль</Label>
						<Input
							id="password"
							type={showPassword ? 'text' : 'password'}
							bind:value={password}
							placeholder="Введите пароль"
							required
							disabled={isBusy}
							class="ps-9"
							onkeydown={handleEnterKey}
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
						<p class="text-sm text-gray-500 dark:text-gray-400">
							Нет пароля? <a
								href="/signup"
								class="text-primary-600 hover:underline dark:text-primary-500"
							>
								Зарегистрироваться
							</a>
						</p>
					</div>
				{/if}

				{#if magicLinkSentTo}
					<Alert color="green">
						Мы отправили ссылку для входа на <span class="font-medium">{magicLinkSentTo}</span>.
						Если это первый вход, аккаунт создастся автоматически.
					</Alert>
				{/if}

				<div class="grid gap-3 sm:grid-cols-2">
					<Button
						type="button"
						color={passwordMode ? 'alternative' : 'dark'}
						class="min-h-11 w-full rounded-xl font-medium transition-all hover:-translate-y-0.5 hover:shadow-md"
						disabled={isBusy}
						onclick={handleMagicLinkRequest}
					>
						{#if activeAction === 'magic'}
							<Spinner size="4" class="mr-2" color="gray" />
							Отправляем...
						{:else}
							Войти по ссылке
						{/if}
					</Button>
					<Button
						type="button"
						color={passwordMode ? 'dark' : 'alternative'}
						class="min-h-11 w-full rounded-xl font-medium transition-all hover:-translate-y-0.5 hover:shadow-md"
						disabled={isBusy}
						onclick={handlePasswordAction}
					>
						{#if activeAction === 'password'}
							<Spinner size="4" class="mr-2" color="gray" />
							Входим...
						{:else}
							Войти с паролем
						{/if}
					</Button>
				</div>
			</div>

			<div class="relative flex items-center py-1">
				<div class="grow border-t border-gray-200 dark:border-gray-700"></div>
				<span class="mx-4 shrink text-sm text-gray-400">или</span>
				<div class="grow border-t border-gray-200 dark:border-gray-700"></div>
			</div>

			<div class="flex flex-col items-center justify-center space-y-3">
				<p class="text-sm text-gray-500 dark:text-gray-400">Быстрый вход через Telegram</p>
				<div id="telegram-login-container" class="min-h-11"></div>
				{#if activeAction === 'telegram'}
					<div class="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
						<Spinner size="4" />
						<span>Подтверждаем вход...</span>
					</div>
				{/if}
			</div>
		</div>
	</Card>
</div>
