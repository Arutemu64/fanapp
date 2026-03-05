<script lang="ts">
	import { Button, Input, Label, Card, Spinner } from 'flowbite-svelte';
	import { getToastService } from '$lib/stores/toasts.svelte';
	import { client } from '$lib/api';
	import { goto } from '$app/navigation';
	import { getEventsClient } from '$lib/events.svelte';
	import { UserSolid, LockSolid, EyeOutline, EyeSlashOutline } from 'flowbite-svelte-icons';
	import { onMount } from 'svelte';
	import { browser } from '$app/environment';

	let login = $state('');
	const eventsClient = getEventsClient();
	const toastService = getToastService();
	let password = $state('');
	let isLoading = $state(false);
	let showPassword = $state(false);

	async function handleLogin(e: Event) {
		e.preventDefault();

		if (!login.trim() || !password.trim()) {
			toastService.add('Введите имя пользователя и пароль', 'warning');
			return;
		}

		isLoading = true;

		try {
			const { data, error, response } = await client.POST('/auth/login', {
				body: {
					username: login.trim(),
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

	async function handleTelegramLogin(user: any) {
		isLoading = true;
		try {
			const { error } = await client.POST('/auth/login_telegram', {
				body: user
			});

			if (error) {
				console.error('Telegram login error:', error);
				const errorMessage =
					typeof error.detail === 'string' ? error.detail : 'Ошибка авторизации через Telegram';
				throw new Error(errorMessage);
			}

			toastService.add('Успешный вход через Telegram!', 'success');
			eventsClient?.restart();
			goto('/', { invalidateAll: true });
		} catch (err) {
			toastService.error(err);
		} finally {
			isLoading = false;
		}
	}

	onMount(() => {
		if (browser) {
			// @ts-ignore
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
				container.appendChild(script);
			}

			return () => {
				// @ts-ignore
				delete window.onTelegramAuth;
			};
		}
	});
</script>

<div class="flex h-full items-center justify-center">
	<Card class="w-full max-w-md p-6 sm:p-8">
		<form onsubmit={handleLogin} class="space-y-6">
			<h2 class="mb-6 text-center text-2xl font-bold text-gray-900 dark:text-white">
				Вход в FAN App
			</h2>

			<div class="space-y-2">
				<Label for="login">Имя пользователя или почта</Label>
				<Input
					id="login"
					type="text"
					bind:value={login}
					placeholder="Введите имя пользователя или почту"
					required
					disabled={isLoading}
					class="ps-9"
				>
					{#snippet left()}
						<UserSolid class="h-5 w-5" />
					{/snippet}
				</Input>
			</div>

			<div class="space-y-2">
				<Label for="password">Пароль</Label>
				<Input
					id="password"
					type={showPassword ? 'text' : 'password'}
					bind:value={password}
					placeholder="Введите пароль"
					required
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

			<div class="relative flex items-center py-2">
				<div class="grow border-t border-gray-200 dark:border-gray-700"></div>
				<span class="mx-4 shrink text-sm text-gray-400">или</span>
				<div class="grow border-t border-gray-200 dark:border-gray-700"></div>
			</div>

			<div class="flex flex-col items-center justify-center space-y-4">
				<div id="telegram-login-container" class="min-h-11"></div>
			</div>
		</form>
	</Card>
</div>
