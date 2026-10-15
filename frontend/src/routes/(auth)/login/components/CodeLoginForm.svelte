<script lang="ts">
	import { Mail } from '@lucide/svelte';
	import { createMutation } from '@tanstack/svelte-query';
	import { onDestroy } from 'svelte';

	import { getApiErrorDetail, getApiFieldError } from '#lib/api/errors.js';
	import { requestLoginCodeMutation } from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import CaptchaWidget, { captchaEnabled } from '#lib/components/CaptchaWidget.svelte';
	import * as Alert from '#lib/components/ui/alert/index.js';
	import { Button } from '#lib/components/ui/button/index.js';
	import * as Field from '#lib/components/ui/field/index.js';
	import { Input } from '#lib/components/ui/input/index.js';
	import { Spinner } from '#lib/components/ui/spinner/index.js';
	import { m } from '#lib/paraglide/messages.js';
	import { CaptchaGate } from '#lib/services/captcha.svelte.js';
	import { isValidEmail, normalizeEmail } from '#lib/utils/validation.js';

	interface Props {
		email: string;
		// Move on to the verify step for the address the code went to.
		onCodeSent: (sentTo: string) => void;
		// Switch to the password form (a factor under this same email identity).
		onPasswordLogin?: () => void;
	}

	let { email = $bindable(''), onCodeSent, onPasswordLogin }: Props = $props();

	const requestCodeMutation = createMutation(() => requestLoginCodeMutation());
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
	let isRequesting = $derived(requestCodeMutation.isPending || captchaGate.awaitingCaptcha);

	// Fulfill a deferred submit the moment the invisible captcha solves.
	function handleCaptchaSolved() {
		if (captchaGate.awaitingCaptcha) {
			handleLoginCodeRequest();
		}
	}

	onDestroy(() => {
		captchaGate.clear();
	});

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
			emailError = m.validation_email_required();
			return false;
		}

		if (!isValidEmail(normalizedEmail)) {
			emailError = m.validation_email_format();
			return false;
		}

		return true;
	}

	function handleLoginCodeRequest() {
		if (requestCodeMutation.isPending) {
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
				formError = m.captcha_failed();
			});
			return;
		}

		captchaGate.release();
		const trimmedEmail = normalizedEmail;

		requestCodeMutation.mutate(
			{ body: { email: trimmedEmail, captcha_token: captchaToken } },
			{
				// A `mutate` callback on purpose: TanStack drops it once this step
				// unmounts. The user can leave (back gesture or «Назад») while the
				// request runs, and a code that lands afterwards must not pull them back
				// into the flow they just left.
				onSuccess: () => onCodeSent(trimmedEmail),
				onError: (error) => {
					const emailFieldError = getApiFieldError(error, 'email');
					if (emailFieldError) {
						emailError = emailFieldError;
					} else {
						formError = getApiErrorDetail(error) ?? m.login_code_send_failed();
					}
					// The token is single-use, so fetch a fresh one before a retry.
					resetCaptcha?.();
					captchaToken = null;
				}
			}
		);
	}

	function handleSubmit(event: SubmitEvent) {
		event.preventDefault();
		if (requestCodeMutation.isPending) return;
		handleLoginCodeRequest();
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
		<Field.FieldLabel for="code-email">{m.email_label()}</Field.FieldLabel>
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
				{m.login_code_hint()}
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
			{m.common_sending()}
		{:else}
			{m.common_continue()}
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
			{m.login_with_password()}
		</button>
	</div>
</form>
