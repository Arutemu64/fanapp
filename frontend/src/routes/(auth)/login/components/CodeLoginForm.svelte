<script lang="ts">
	import { createApiClient } from '$lib/api';
	import { requestLoginCode } from '$lib/api/generated';
	const client = createApiClient();
	import { getApiErrorDetail, getApiFieldError } from '$lib/api/errors';
	import CaptchaWidget, { captchaEnabled } from '$lib/components/CaptchaWidget.svelte';
	import * as Alert from '$lib/components/ui/alert';
	import { Button } from '$lib/components/ui/button';
	import * as Field from '$lib/components/ui/field';
	import { Input } from '$lib/components/ui/input';
	import { Spinner } from '$lib/components/ui/spinner';
	import { CaptchaGate } from '$lib/services/captcha.svelte';
	import { isValidEmail, normalizeEmail } from '$lib/utils/validation';
	import { Mail } from '@lucide/svelte';
	import { onDestroy } from 'svelte';

	interface Props {
		email: string;
		// Move on to the verify step for the address the code went to.
		onCodeSent: (sentTo: string) => void;
		// Switch to the password form (a factor under this same email identity).
		onPasswordLogin?: () => void;
	}

	let { email = $bindable(''), onCodeSent, onPasswordLogin }: Props = $props();

	type ActiveAction = 'code-request' | null;

	let activeAction = $state<ActiveAction>(null);
	let emailError = $state('');
	let formError = $state('');

	// Captcha state (only relevant when a SmartCaptcha client key is configured).
	let captchaToken = $state<string | null>(null);
	let resetCaptcha = $state<(() => void) | undefined>(undefined);
	let executeCaptcha = $state<(() => void) | undefined>(undefined);

	// Holds the request when the user submits before the invisible captcha has a
	// token; the widget's onSolve fires it once the token lands, so the user never
	// has to tap "Продолжить" a second time.
	const captchaGate = new CaptchaGate();

	// In flight from the user's point of view: the request is running, or we're
	// holding it until the background captcha resolves.
	let isRequesting = $derived(activeAction === 'code-request' || captchaGate.awaitingCaptcha);

	// Fulfill a deferred submit the moment the invisible captcha solves.
	function handleCaptchaSolved() {
		if (captchaGate.awaitingCaptcha) {
			void handleLoginCodeRequest();
		}
	}

	onDestroy(() => captchaGate.clear());

	let normalizedEmail = $derived(normalizeEmail(email));

	function resetEmailFeedback() {
		emailError = '';
		formError = '';
		// Editing the email cancels any submit we were holding for the captcha.
		captchaGate.release();
	}

	function validateEmailCodeRequestForm(): boolean {
		emailError = '';

		if (!normalizedEmail) {
			emailError = 'Введи адрес эл. почты';
			return false;
		}

		if (!isValidEmail(normalizedEmail)) {
			emailError = 'Введи адрес в формате name@example.com';
			return false;
		}

		return true;
	}

	async function handleLoginCodeRequest() {
		if (activeAction !== null) {
			return;
		}

		if (!validateEmailCodeRequestForm()) {
			captchaGate.release();
			return;
		}

		// The captcha runs invisibly. If its token isn't ready yet, start the
		// challenge and hold the request; handleCaptchaSolved re-runs this once the
		// token arrives.
		if (captchaEnabled && !captchaToken) {
			executeCaptcha?.();
			captchaGate.hold(() => {
				formError = 'Не удалось пройти проверку. Попробуй ещё раз';
			});
			return;
		}

		captchaGate.release();
		const trimmedEmail = normalizedEmail;

		activeAction = 'code-request';

		try {
			const { error, response } = await requestLoginCode({
				client,
				body: { email: trimmedEmail, captcha_token: captchaToken }
			});

			if (error || !response?.ok) {
				console.error('Login code request error:', error);
				const emailFieldError = getApiFieldError(error, 'email');
				if (emailFieldError) {
					emailError = emailFieldError;
				} else {
					formError = getApiErrorDetail(error) ?? 'Не удалось отправить код';
				}
				// The token is single-use, so fetch a fresh one before a retry.
				resetCaptcha?.();
				captchaToken = null;
				return;
			}

			onCodeSent(trimmedEmail);
		} finally {
			activeAction = null;
		}
	}

	function handleSubmit(event: SubmitEvent) {
		event.preventDefault();
		if (activeAction !== null) return;
		void handleLoginCodeRequest();
	}
</script>

<form novalidate onsubmit={handleSubmit} class="flex flex-col gap-4">
	{#if formError}
		<Alert.Root variant="destructive">
			<Alert.Description>{formError}</Alert.Description>
		</Alert.Root>
	{/if}

	<!-- Errors appear on submit only, never while typing: a half-typed address is
		not a mistake yet, and FieldError's role="alert" would announce it mid-word.
		`novalidate` on the form hands that check to us — the browser's own bubble
		would block the submit in the browser's language, not Russian.
		https://design-system.service.gov.uk/patterns/validation/ -->
	<Field.Field data-invalid={emailError ? true : undefined}>
		<Field.FieldLabel for="code-email">Эл. почта</Field.FieldLabel>
		<div class="relative flex items-center">
			<Mail class="pointer-events-none absolute left-3 size-4 text-muted-foreground" />
			<!-- Read-only, not disabled, while sending: disabling a focused input
				drops focus to <body> and closes the phone keyboard. `username`, not
				`email`: password managers offer saved sign-ins on that token, so an
				account with a password autofills its address here too.
				https://web.dev/articles/sign-in-form-best-practices -->
			<Input
				id="code-email"
				name="email"
				type="email"
				bind:value={email}
				placeholder="name@example.com"
				autocomplete="username"
				inputmode="email"
				autocapitalize="off"
				spellcheck={false}
				required
				readonly={isRequesting}
				class="pl-9"
				aria-invalid={emailError ? true : undefined}
				aria-describedby={emailError ? 'code-email-error' : 'code-email-description'}
				oninput={resetEmailFeedback}
			/>
		</div>
		{#if emailError}
			<Field.FieldError id="code-email-error">{emailError}</Field.FieldError>
		{:else}
			<Field.FieldDescription id="code-email-description">
				Пришлём код для входа.
			</Field.FieldDescription>
		{/if}
	</Field.Field>

	<CaptchaWidget
		bind:token={captchaToken}
		bind:reset={resetCaptcha}
		bind:execute={executeCaptcha}
		onSolve={handleCaptchaSolved}
	/>

	<Button type="submit" class="w-full" disabled={isRequesting}>
		{#if isRequesting}
			<Spinner data-icon="inline-start" />
			Отправляем…
		{:else}
			Продолжить
		{/if}
	</Button>

	<!-- Password login is the minority path, so it's a quiet link, not a second button. -->
	<div class="text-center">
		<button
			type="button"
			class="inline-flex min-h-11 items-center justify-center rounded-lg px-3 text-sm font-medium text-primary hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary disabled:opacity-50"
			onclick={() => onPasswordLogin?.()}
			disabled={isRequesting}
		>
			Войти с паролем
		</button>
	</div>
</form>
