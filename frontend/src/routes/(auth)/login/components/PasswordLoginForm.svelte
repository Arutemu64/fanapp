<script lang="ts">
	import { createApiClient } from '$lib/api';
	const client = createApiClient();
	import { getApiErrorDetail } from '$lib/api/errors';
	import PasswordInput from '$lib/components/PasswordInput.svelte';
	import * as Alert from '$lib/components/ui/alert';
	import { Button } from '$lib/components/ui/button';
	import * as Field from '$lib/components/ui/field';
	import { Input } from '$lib/components/ui/input';
	import { Spinner } from '$lib/components/ui/spinner';
	import { getEventsClient } from '$lib/services/events.svelte';
	import { getToastService } from '$lib/services/toasts.svelte';
	import { completeLogin } from '$lib/utils/auth';
	import { isValidEmail, normalizeEmail } from '$lib/utils/validation';
	import { ArrowLeft, Mail } from '@lucide/svelte';

	interface Props {
		email: string;
		onBack?: () => void;
	}

	let { email = $bindable(''), onBack }: Props = $props();

	type ActiveAction = 'password' | null;

	let password = $state('');
	let activeAction = $state<ActiveAction>(null);
	let emailError = $state('');
	let passwordError = $state('');
	let formError = $state('');

	const eventsClient = getEventsClient();
	const toastService = getToastService();

	let busy = $derived(activeAction !== null);

	let normalizedEmail = $derived(normalizeEmail(email));
	let isEmailValid = $derived(email ? isValidEmail(normalizedEmail) : null);

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

			await completeLogin(toastService, eventsClient, 'Вход выполнен');
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

<form onsubmit={handlePasswordSubmit} class="flex flex-col gap-4">
	{#if formError}
		<Alert.Root variant="destructive">
			<Alert.Description>{formError}</Alert.Description>
		</Alert.Root>
	{/if}

	<Field.FieldGroup class="gap-4">
		<Field.Field data-invalid={emailError || (email && isEmailValid === false) ? true : undefined}>
			<Field.FieldLabel for="password-email">Эл. почта</Field.FieldLabel>
			<div class="relative flex items-center">
				<Mail class="pointer-events-none absolute left-3 size-4 text-muted-foreground" />
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
					class="pl-9"
					aria-invalid={emailError || (email && isEmailValid === false) ? true : undefined}
					oninput={resetEmailFeedback}
				/>
			</div>
			{#if emailError}
				<Field.FieldError>{emailError}</Field.FieldError>
			{:else if email && isEmailValid === false}
				<Field.FieldError>Введи адрес в формате name@example.com</Field.FieldError>
			{/if}
		</Field.Field>

		<Field.Field data-invalid={passwordError ? true : undefined}>
			<Field.FieldLabel for="password">Пароль</Field.FieldLabel>
			<PasswordInput
				id="password"
				name="password"
				bind:value={password}
				autocomplete="current-password"
				required
				disabled={busy}
				color={passwordError ? 'red' : undefined}
				oninput={resetPasswordFeedback}
			/>
			{#if passwordError}
				<Field.FieldError>{passwordError}</Field.FieldError>
			{/if}
		</Field.Field>
	</Field.FieldGroup>

	<Button type="submit" class="min-h-11 w-full font-medium" disabled={busy}>
		{#if activeAction === 'password'}
			<Spinner data-icon="inline-start" />
			Входим…
		{:else}
			Войти
		{/if}
	</Button>

	<Button
		type="button"
		variant="outline"
		class="min-h-11 w-full font-medium"
		disabled={busy}
		onclick={() => onBack?.()}
	>
		<ArrowLeft data-icon="inline-start" />
		Назад
	</Button>
</form>
