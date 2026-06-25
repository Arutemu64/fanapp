<script lang="ts">
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { createApiClient } from '$lib/api';
	const client = createApiClient();
	import { getApiErrorDetail } from '$lib/api/errors';
	import { getEventsClient } from '$lib/services/events.svelte';
	import { getToastService } from '$lib/services/toasts.svelte';
	import { isValidEmail, normalizeEmail } from '$lib/utils/validation';
	import { Alert, Button, Helper, Input, Label, Spinner } from 'flowbite-svelte';
	import {
		ArrowLeftOutline,
		EnvelopeSolid,
		EyeOutline,
		EyeSlashOutline,
		LockSolid
	} from 'flowbite-svelte-icons';

	let {
		email = $bindable(''),
		isBusy = $bindable(false),
		onBack
	} = $props<{
		email: string;
		isBusy?: boolean;
		onBack?: () => void;
	}>();

	type ActiveAction = 'password' | null;

	let password = $state('');
	let activeAction = $state<ActiveAction>(null);
	let showPassword = $state(false);
	let emailError = $state('');
	let passwordError = $state('');
	let formError = $state('');

	const eventsClient = getEventsClient();
	const toastService = getToastService();

	let busy = $derived(activeAction !== null);

	$effect(() => {
		isBusy = busy;
	});

	let normalizedEmail = $derived(normalizeEmail(email));
	let isEmailValid = $derived(email ? isValidEmail(normalizedEmail) : null);
	let emailColor = $derived.by((): 'green' | 'red' | undefined => {
		if (emailError) return 'red';
		if (!email) return undefined;
		return isEmailValid ? 'green' : 'red';
	});
	let passwordColor = $derived.by((): 'red' | undefined => {
		return passwordError ? 'red' : undefined;
	});

	function resetEmailFeedback() {
		emailError = '';
		formError = '';
	}

	function resetPasswordFeedback() {
		passwordError = '';
		formError = '';
	}

	function validatePasswordForm(): boolean {
		emailError = '';
		passwordError = '';

		if (!normalizedEmail) {
			emailError = 'Введи адрес эл. почты';
		} else if (!isValidEmail(normalizedEmail)) {
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
		if (activeAction !== null) {
			return;
		}

		if (!validatePasswordForm()) {
			return;
		}

		const trimmedEmail = normalizedEmail;

		activeAction = 'password';

		try {
			const { error, response } = await client.POST('/auth/login', {
				body: {
					email: trimmedEmail,
					password
				},
				headers: {
					'Content-Type': 'application/x-www-form-urlencoded'
				}
			});

			if (error || !response.ok) {
				console.error('Login error:', error);
				formError = getApiErrorDetail(error) ?? 'Неверная почта или пароль';
				return;
			}

			await finishLogin('Вход выполнен');
		} catch (err) {
			console.error('Password login exception:', err);
			formError = 'Произошла непредвиденная ошибка';
		} finally {
			activeAction = null;
		}
	}

	function handlePasswordSubmit(event: SubmitEvent) {
		event.preventDefault();

		if (activeAction !== null) {
			return;
		}

		void submitPasswordLogin();
	}
</script>

<form onsubmit={handlePasswordSubmit} class="space-y-4">
	{#if formError}
		<Alert color="red" class="rounded-xl text-sm">
			{formError}
		</Alert>
	{/if}

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
			disabled={busy}
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
			disabled={busy}
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
					class="pointer-events-auto -mr-2 flex min-h-11 min-w-11 items-center justify-center rounded-lg hover:bg-gray-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 dark:hover:bg-gray-700"
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
		disabled={busy}
	>
		{#if activeAction === 'password'}
			<Spinner size="4" class="mr-2" color="primary" />
			Входим…
		{:else}
			Войти
		{/if}
	</Button>

	<Button
		type="button"
		color="light"
		class="min-h-11 w-full rounded-xl font-medium"
		disabled={busy}
		onclick={() => onBack?.()}
	>
		<ArrowLeftOutline class="me-2 h-4 w-4" />
		Назад
	</Button>
</form>
