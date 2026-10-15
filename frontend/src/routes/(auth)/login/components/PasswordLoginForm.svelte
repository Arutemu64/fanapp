<script lang="ts">
	import { Mail } from '@lucide/svelte';
	import { createMutation } from '@tanstack/svelte-query';

	import { getApiErrorDetail, getApiFieldError } from '#lib/api/errors.js';
	import { loginMutation } from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import PasswordInput from '#lib/components/PasswordInput.svelte';
	import * as Alert from '#lib/components/ui/alert/index.js';
	import { Button } from '#lib/components/ui/button/index.js';
	import * as Field from '#lib/components/ui/field/index.js';
	import { Input } from '#lib/components/ui/input/index.js';
	import { Spinner } from '#lib/components/ui/spinner/index.js';
	import { m } from '#lib/paraglide/messages.js';
	import { getSession } from '#lib/services/session.js';
	import { getToastService } from '#lib/services/toasts.svelte.js';
	import { isValidEmail, normalizeEmail } from '#lib/utils/validation.js';

	interface Props {
		email: string;
		// Return to the email step, which signs in with a code instead.
		onCodeLogin?: () => void;
	}

	let { email = $bindable(''), onCodeLogin }: Props = $props();

	let password = $state('');
	let emailError = $state('');
	let passwordError = $state('');
	let formError = $state('');

	const session = getSession();
	const toastService = getToastService();

	// Pending until session.loggedIn has loaded the new identity and navigated, so
	// the form stays busy until the app moves on.
	const passwordLoginMutation = createMutation(() => ({
		...loginMutation(),
		onSuccess: async () => {
			await session.loggedIn();
			toastService.add(m.login_success(), 'success');
		}
	}));
	let busy = $derived(passwordLoginMutation.isPending);

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
			emailError = m.validation_email_required();
		} else if (!isValidEmail(normalizedEmail)) {
			emailError = m.validation_email_format();
		}

		if (!password.trim()) {
			passwordError = m.validation_password_required();
		}

		return !emailError && !passwordError;
	}

	function submitPasswordLogin() {
		if (busy) {
			return;
		}

		if (!validatePasswordForm()) {
			return;
		}

		const trimmedEmail = normalizedEmail;

		passwordLoginMutation.mutate(
			{ body: { email: trimmedEmail, password } },
			{
				onError: (error) => {
					emailError = getApiFieldError(error, 'email') ?? '';
					passwordError = getApiFieldError(error, 'password') ?? '';
					if (emailError || passwordError) {
						return;
					}
					formError = getApiErrorDetail(error) ?? m.error_invalid_credentials();
				}
			}
		);
	}

	function handlePasswordSubmit(event: SubmitEvent) {
		event.preventDefault();

		if (busy) {
			return;
		}

		submitPasswordLogin();
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
			<Field.FieldLabel for="password-email">{m.email_label()}</Field.FieldLabel>
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
			<Field.FieldLabel for="password">{m.password_label()}</Field.FieldLabel>
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
		{#if busy}
			<Spinner data-icon="inline-start" />
			{m.login_progress()}
		{:else}
			{m.common_login()}
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
			{m.login_with_code()}
		</button>
	</div>
</form>
