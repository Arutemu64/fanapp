<script lang="ts">
	import { createApiClient } from '#lib/api/index.js';
	const client = createApiClient();
	import { Mail } from '@lucide/svelte';

	import { getApiErrorDetail, getApiFieldError } from '#lib/api/errors.js';
	import { login } from '#lib/api/generated/index.js';
	import PasswordInput from '#lib/components/PasswordInput.svelte';
	import * as Alert from '#lib/components/ui/alert/index.js';
	import { Button } from '#lib/components/ui/button/index.js';
	import * as Field from '#lib/components/ui/field/index.js';
	import { Input } from '#lib/components/ui/input/index.js';
	import { Spinner } from '#lib/components/ui/spinner/index.js';
	import { getEventsClient } from '#lib/services/events.svelte.js';
	import { getToastService } from '#lib/services/toasts.svelte.js';
	import { completeLogin } from '#lib/utils/auth.js';
	import { isValidEmail, normalizeEmail } from '#lib/utils/validation.js';

	interface Props {
		email: string;
		// Return to the email step, which signs in with a code instead.
		onCodeLogin?: () => void;
	}

	let { email = $bindable(''), onCodeLogin }: Props = $props();

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
			const { error, response } = await login({
				client,
				body: {
					email: trimmedEmail,
					password
				}
			});

			if (error || !response?.ok) {
				console.error('Login error:', error);
				emailError = getApiFieldError(error, 'email') ?? '';
				passwordError = getApiFieldError(error, 'password') ?? '';
				if (emailError || passwordError) {
					return;
				}
				formError = getApiErrorDetail(error) ?? 'Неверная почта или пароль';
				return;
			}

			await completeLogin(toastService, eventsClient, 'Вход выполнен');
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

<form novalidate onsubmit={handlePasswordSubmit} class="flex flex-col gap-4">
	{#if formError}
		<Alert.Root variant="destructive">
			<Alert.Description>{formError}</Alert.Description>
		</Alert.Root>
	{/if}

	<!-- Errors appear on submit only, and the inputs go read-only rather than
		disabled while signing in — see CodeLoginForm for why. -->
	<Field.FieldGroup class="gap-4">
		<Field.Field data-invalid={emailError ? true : undefined}>
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
					readonly={busy}
					class="pl-9"
					aria-invalid={emailError ? true : undefined}
					aria-describedby={emailError ? 'password-email-error' : undefined}
					oninput={resetEmailFeedback}
				/>
			</div>
			{#if emailError}
				<Field.FieldError id="password-email-error">{emailError}</Field.FieldError>
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
				readonly={busy}
				color={passwordError ? 'red' : undefined}
				describedby={passwordError ? 'password-error' : undefined}
				oninput={resetPasswordFeedback}
			/>
			{#if passwordError}
				<Field.FieldError id="password-error">{passwordError}</Field.FieldError>
			{/if}
		</Field.Field>
	</Field.FieldGroup>

	<Button type="submit" class="w-full" disabled={busy}>
		{#if activeAction === 'password'}
			<Spinner data-icon="inline-start" />
			Входим…
		{:else}
			Войти
		{/if}
	</Button>

	<!-- The way out for a forgotten password: a code needs only the inbox. -->
	<div class="text-center">
		<button
			type="button"
			class="inline-flex min-h-11 items-center justify-center rounded-lg px-3 text-sm font-medium text-primary hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary disabled:opacity-50"
			onclick={() => onCodeLogin?.()}
			disabled={busy}
		>
			Войти по коду без пароля
		</button>
	</div>
</form>
