<script lang="ts">
	import { createApiClient } from '$lib/api';
	const client = createApiClient();
	import { getApiErrorDetail } from '$lib/api/errors';
	import CaptchaWidget, { captchaEnabled } from '$lib/components/CaptchaWidget.svelte';
	import * as Alert from '$lib/components/ui/alert';
	import { Button } from '$lib/components/ui/button';
	import * as Field from '$lib/components/ui/field';
	import { Input } from '$lib/components/ui/input';
	import { Spinner } from '$lib/components/ui/spinner';
	import { CaptchaGate } from '$lib/services/captcha.svelte';
	import { isValidEmail, normalizeEmail } from '$lib/utils/validation';
	import { ArrowLeft, Mail } from '@lucide/svelte';
	import { onDestroy } from 'svelte';

	import VerifyCodeForm from './VerifyCodeForm.svelte';

	interface Props {
		email: string;
		// Return to the login-options screen.
		onBack?: () => void;
		// Switch to the password form (a factor under this same email identity).
		onPasswordLogin?: () => void;
	}

	let { email = $bindable(''), onBack, onPasswordLogin }: Props = $props();

	// The address the code went to, empty until it's sent — the switch to the
	// verify step. Local now: the options screen no longer needs to know.
	let codeSentTo = $state('');

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
	let isEmailValid = $derived(email ? isValidEmail(normalizedEmail) : null);

	function resetEmailFeedback() {
		emailError = '';
		formError = '';
		codeSentTo = '';
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
		codeSentTo = '';

		try {
			const { error, response } = await client.POST('/auth/request-login-code', {
				body: { email: trimmedEmail, captcha_token: captchaToken }
			});

			if (error || !response.ok) {
				console.error('Login code request error:', error);
				formError = getApiErrorDetail(error) ?? 'Не удалось отправить код';
				// The token is single-use, so fetch a fresh one before a retry.
				resetCaptcha?.();
				captchaToken = null;
				return;
			}

			// OTP input auto-focuses its first box on mount, so no manual focus here.
			codeSentTo = trimmedEmail;
		} catch (err) {
			console.error('Login code request exception:', err);
			formError = 'Произошла непредвиденная ошибка. Попробуй ещё раз';
			resetCaptcha?.();
			captchaToken = null;
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

{#if codeSentTo}
	<VerifyCodeForm email={codeSentTo} onBack={() => (codeSentTo = '')} />
{:else}
	<form onsubmit={handleSubmit} class="flex flex-col gap-4">
		{#if formError}
			<Alert.Root variant="destructive">
				<Alert.Description>{formError}</Alert.Description>
			</Alert.Root>
		{/if}

		<Field.Field data-invalid={emailError || (email && isEmailValid === false) ? true : undefined}>
			<Field.FieldLabel for="code-email">Эл. почта</Field.FieldLabel>
			<div class="relative flex items-center">
				<Mail class="pointer-events-none absolute left-3 size-4 text-muted-foreground" />
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
					disabled={isRequesting}
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

		<CaptchaWidget
			bind:token={captchaToken}
			bind:reset={resetCaptcha}
			bind:execute={executeCaptcha}
			onSolve={handleCaptchaSolved}
		/>

		<Button type="submit" class="min-h-11 w-full font-medium" disabled={isRequesting}>
			{#if isRequesting}
				<Spinner data-icon="inline-start" />
				Отправляем…
			{:else}
				Продолжить
			{/if}
		</Button>

		<!-- Password login is the minority path, so it's a quiet link, not a third button. -->
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

		<Button
			type="button"
			variant="outline"
			class="min-h-11 w-full font-medium"
			disabled={isRequesting}
			onclick={() => onBack?.()}
		>
			<ArrowLeft data-icon="inline-start" />
			Назад
		</Button>
	</form>
{/if}
