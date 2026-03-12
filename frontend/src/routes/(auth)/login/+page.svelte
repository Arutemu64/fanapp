<script lang="ts">
	import { goto } from '$app/navigation';
	import { PUBLIC_API_URL } from '$env/static/public';
	import { client } from '$lib/api';
	import { getEventsClient } from '$lib/events.svelte';
	import { getToastService } from '$lib/stores/toasts.svelte';
	import { Alert, Button, Card, Input, Label, Spinner, Tabs, TabItem } from 'flowbite-svelte';
	import { EnvelopeSolid, EyeOutline, EyeSlashOutline, LockSolid } from 'flowbite-svelte-icons';

	type ActiveAction = 'password' | 'magic' | null;

	let email = $state('');
	let password = $state('');
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
		await goto('/', { invalidateAll: true });
		eventsClient?.restart();
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

	function handleMagicLinkEnter(event: KeyboardEvent) {
		if (event.key !== 'Enter' || isBusy) return;
		event.preventDefault();
		void handleMagicLinkRequest();
	}

	function handlePasswordEnter(event: KeyboardEvent) {
		if (event.key !== 'Enter' || isBusy) return;
		event.preventDefault();
		void submitPasswordLogin();
	}
</script>

<Card class="w-full p-4 sm:p-6">
	<div class="space-y-4">
		<h2 class="text-center text-2xl font-bold text-gray-900 dark:text-white">Вход в FAN App</h2>

		<Tabs tabStyle="underline" contentClass="mt-3">
			<TabItem open title="По ссылке">
				<div class="space-y-3">
					<div>
						<Label for="magic-email" class="mb-2">Email</Label>
						<Input
							id="magic-email"
							type="email"
							bind:value={email}
							placeholder="you@example.com"
							required
							disabled={isBusy}
							class="ps-9"
							oninput={() => (magicLinkSentTo = '')}
							onkeydown={handleMagicLinkEnter}
						>
							{#snippet left()}
								<EnvelopeSolid class="h-5 w-5" />
							{/snippet}
						</Input>
					</div>

					{#if magicLinkSentTo}
						<Alert color="green">
							Ссылка отправлена на <span class="font-medium">{magicLinkSentTo}</span>
						</Alert>
					{/if}

					<Button
						type="button"
						color="primary"
						class="min-h-11 w-full rounded-xl font-medium transition-all hover:-translate-y-0.5 hover:shadow-md"
						disabled={isBusy}
						onclick={handleMagicLinkRequest}
					>
						{#if activeAction === 'magic'}
							<Spinner size="4" class="mr-2" color="primary" />
							Отправляем...
						{:else}
							Отправить ссылку
						{/if}
					</Button>
				</div>
			</TabItem>

			<TabItem title="С паролем">
				<div class="space-y-4">
					<div>
						<Label for="password-email" class="mb-2">Email</Label>
						<Input
							id="password-email"
							type="email"
							bind:value={email}
							placeholder="you@example.com"
							required
							disabled={isBusy}
							class="ps-9"
							onkeydown={handlePasswordEnter}
						>
							{#snippet left()}
								<EnvelopeSolid class="h-5 w-5" />
							{/snippet}
						</Input>
					</div>

					<div>
						<Label for="password" class="mb-2">Пароль</Label>
						<Input
							id="password"
							type={showPassword ? 'text' : 'password'}
							bind:value={password}
							placeholder="••••••••"
							required
							disabled={isBusy}
							class="ps-9"
							onkeydown={handlePasswordEnter}
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
					</div>

					<Button
						type="button"
						color="primary"
						class="min-h-11 w-full rounded-xl font-medium transition-all hover:-translate-y-0.5 hover:shadow-md"
						disabled={isBusy}
						onclick={submitPasswordLogin}
					>
						{#if activeAction === 'password'}
							<Spinner size="4" class="mr-2" color="primary" />
							Входим...
						{:else}
							Войти
						{/if}
					</Button>

					<p class="text-center text-sm text-gray-500 dark:text-gray-400">
						Нет аккаунта?
						<a href="/signup" class="text-primary-600 hover:underline dark:text-primary-500">
							Зарегистрироваться
						</a>
					</p>
				</div>
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
				class="min-h-11 w-full rounded-xl font-medium transition-all hover:-translate-y-0.5 hover:shadow-md"
			>
				Войти через Telegram
			</Button>
		</div>
	</div>
</Card>
