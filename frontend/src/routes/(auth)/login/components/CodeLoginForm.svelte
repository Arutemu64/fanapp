<script lang="ts">
	import { createApiClient } from '$lib/api';
	const client = createApiClient();
	import { getApiFailureMessage } from '$lib/api/errors';
	import CaptchaWidget, { captchaEnabled } from '$lib/components/CaptchaWidget.svelte';
	import { CaptchaGate } from '$lib/utils/captcha.svelte';
	import { isValidEmail, normalizeEmail } from '$lib/utils/validation';
	import { Alert, Button, Helper, Input, Label, Spinner } from 'flowbite-svelte';
	import { EnvelopeSolid } from 'flowbite-svelte-icons';
	import { onDestroy } from 'svelte';

	import VerifyCodeForm from './VerifyCodeForm.svelte';

	interface Props {
		email: string;
		showPasswordForm?: boolean;
		// The address the code went to, empty until it's sent. Bindable because the
		// login page hides the Telegram button once we're waiting for a code; it
		// derives that from this rather than us mirroring a second flag back up.
		codeSentTo?: string;
	}

	let {
		email = $bindable(''),
		showPasswordForm = $bindable(false),
		codeSentTo = $bindable('')
	}: Props = $props();

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
	let emailColor = $derived.by((): 'green' | 'red' | undefined => {
		if (emailError) return 'red';
		if (!email) return undefined;
		return isEmailValid ? 'green' : 'red';
	});

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

			const failure = getApiFailureMessage(error, response, 'Не удалось отправить код');
			if (failure) {
				console.error('Login code request error:', error);
				formError = failure;
				// The token is single-use, so fetch a fresh one before a retry.
				resetCaptcha?.();
				captchaToken = null;
				return;
			}

			// OtpInput auto-focuses its first box on mount, so no manual focus here.
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
	<form onsubmit={handleSubmit} class="space-y-4">
		{#if formError}
			<Alert color="red" class="rounded-xl text-sm">
				{formError}
			</Alert>
		{/if}

		<div>
			<Label for="code-email" color={emailColor} class="mb-2">Эл. почта</Label>
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
			{:else}
				<Helper color="gray" class="mt-1"
					>Если у вас ещё нет аккаунта, он будет создан автоматически.</Helper
				>
			{/if}
		</div>

		<CaptchaWidget
			bind:token={captchaToken}
			bind:reset={resetCaptcha}
			bind:execute={executeCaptcha}
			onSolve={handleCaptchaSolved}
		/>

		<Button
			type="submit"
			color="primary"
			class="min-h-11 w-full rounded-xl font-medium"
			disabled={isRequesting}
		>
			{#if isRequesting}
				<Spinner size="4" class="mr-2" color="primary" />
				Отправляем…
			{:else}
				Продолжить
			{/if}
		</Button>

		<!-- Password login is the minority path, so it's a quiet link, not a third button. -->
		<div class="text-center">
			<button
				type="button"
				class="inline-flex min-h-11 items-center justify-center rounded-lg px-3 text-sm font-medium text-primary-600 hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-600 disabled:opacity-50 dark:text-primary-400"
				onclick={() => (showPasswordForm = true)}
				disabled={isRequesting}
			>
				Войти с паролем
			</button>
		</div>
	</form>
{/if}
