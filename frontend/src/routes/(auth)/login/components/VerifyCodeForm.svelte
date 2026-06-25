<script lang="ts">
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { createApiClient } from '$lib/api';
	const client = createApiClient();
	import { getApiErrorDetail } from '$lib/api/errors';
	import CaptchaWidget, { captchaEnabled } from '$lib/components/CaptchaWidget.svelte';
	import OtpInput from '$lib/components/OtpInput.svelte';
	import { getEventsClient } from '$lib/services/events.svelte';
	import { getToastService } from '$lib/services/toasts.svelte';
	import { isValidOtp } from '$lib/utils/validation';
	import { Alert, Button, Helper, Label, Spinner } from 'flowbite-svelte';
	import { ArrowLeftOutline, RefreshOutline } from 'flowbite-svelte-icons';
	import { onMount } from 'svelte';

	interface Props {
		email: string;
		isBusy?: boolean;
		onBack?: () => void;
	}

	let { email, isBusy = $bindable(false), onBack }: Props = $props();

	type ActiveAction = 'code-request' | 'code-login' | null;

	let loginCode = $state('');
	let activeAction = $state<ActiveAction>(null);
	let loginCodeError = $state('');
	let formError = $state('');

	let resendCooldown = $state(60);
	let resendInterval: ReturnType<typeof setInterval>;

	// Captcha state for the "resend code" request (same endpoint as the first one).
	let captchaToken = $state<string | null>(null);
	let resetCaptcha = $state<(() => void) | undefined>(undefined);

	// Set when the user taps resend before the invisible captcha has a token.
	let awaitingCaptcha = $state(false);

	// Safety net: if the invisible captcha never resolves (widget/network error),
	// don't spin forever — fall back to a retryable error after this long.
	const CAPTCHA_WAIT_TIMEOUT_MS = 10000;
	let captchaWaitTimer: ReturnType<typeof setTimeout> | undefined;

	function clearCaptchaWait() {
		clearTimeout(captchaWaitTimer);
		captchaWaitTimer = undefined;
	}

	// Resend is in flight when its request runs or we're holding it for the captcha.
	let isResending = $derived(activeAction === 'code-request' || awaitingCaptcha);
	// Any in-flight work in this form (verifying the code, or resending it).
	let busy = $derived(activeAction !== null || awaitingCaptcha);

	const eventsClient = getEventsClient();
	const toastService = getToastService();

	$effect(() => {
		isBusy = busy;
	});

	// Fulfill a deferred resend the moment the invisible captcha solves.
	$effect(() => {
		if (awaitingCaptcha && captchaToken) {
			void handleLoginCodeRequest();
		}
	});

	function startCooldown() {
		resendCooldown = 60;
		clearInterval(resendInterval);
		resendInterval = setInterval(() => {
			if (resendCooldown > 0) {
				resendCooldown -= 1;
			} else {
				clearInterval(resendInterval);
			}
		}, 1000);
	}

	onMount(() => {
		startCooldown();
		return () => {
			clearInterval(resendInterval);
			clearCaptchaWait();
		};
	});

	function resetLoginCodeFeedback() {
		loginCodeError = '';
		formError = '';
	}

	async function finishLogin(successMessage: string) {
		toastService.add(successMessage, 'success');
		await goto(resolve('/'), { invalidateAll: true });
		eventsClient?.restart();
	}

	async function submitLoginCode() {
		if (activeAction !== null) {
			return;
		}

		if (loginCode.length !== 6) {
			loginCodeError = 'Введи код из письма';
			return;
		}

		if (!isValidOtp(loginCode)) {
			loginCodeError = 'Код должен состоять из 6 цифр';
			return;
		}

		activeAction = 'code-login';
		loginCodeError = '';
		formError = '';

		try {
			const { error, response } = await client.POST('/auth/login-with-code', {
				body: { email, code: loginCode }
			});

			if (error) {
				if (response.status === 400) {
					loginCodeError = getApiErrorDetail(error) ?? 'Неверный или устаревший код';
					return;
				}
				formError = getApiErrorDetail(error) ?? 'Не удалось выполнить вход';
				return;
			}

			await finishLogin('Вход выполнен');
		} catch (err) {
			console.error('Login code submit exception:', err);
			formError = 'Произошла непредвиденная ошибка. Попробуй ещё раз';
		} finally {
			activeAction = null;
		}
	}

	async function handleLoginCodeRequest() {
		// The captcha runs invisibly. If its token isn't ready yet, hold the
		// resend; the effect above re-runs this once the token arrives.
		if (captchaEnabled && !captchaToken) {
			awaitingCaptcha = true;
			clearCaptchaWait();
			captchaWaitTimer = setTimeout(() => {
				if (awaitingCaptcha) {
					awaitingCaptcha = false;
					formError = 'Не удалось пройти проверку. Попробуй ещё раз';
				}
			}, CAPTCHA_WAIT_TIMEOUT_MS);
			return;
		}

		awaitingCaptcha = false;
		clearCaptchaWait();
		activeAction = 'code-request';
		loginCodeError = '';
		formError = '';

		try {
			const { error, response } = await client.POST('/auth/request-login-code', {
				body: { email, turnstile_token: captchaToken }
			});

			if (error || !response.ok) {
				console.error('Login code request error:', error);
				formError = getApiErrorDetail(error) ?? 'Не удалось отправить код повторно';
				// The token is single-use, so fetch a fresh one before a retry.
				resetCaptcha?.();
				captchaToken = null;
				return;
			}

			loginCode = '';
			toastService.add('Код отправлен повторно', 'success');
			// Each resend needs its own fresh token.
			resetCaptcha?.();
			captchaToken = null;
			startCooldown();
		} catch (err) {
			console.error('Login code request exception:', err);
			formError = 'Произошла ошибка при повторной отправке кода';
			resetCaptcha?.();
			captchaToken = null;
		} finally {
			activeAction = null;
		}
	}

	function handleSubmit(event: SubmitEvent) {
		event.preventDefault();
		if (activeAction !== null) return;
		void submitLoginCode();
	}
</script>

<form onsubmit={handleSubmit} class="space-y-4">
	{#if formError}
		<Alert color="red" class="rounded-xl text-sm">
			{formError}
		</Alert>
	{/if}

	<Alert color="green">
		Код отправлен на <span class="font-medium">{email}</span>.
	</Alert>

	<div>
		<Label class="mb-2 block text-center">Код подтверждения</Label>
		<OtpInput
			bind:value={loginCode}
			disabled={busy}
			hasError={Boolean(loginCodeError)}
			onInput={resetLoginCodeFeedback}
			onComplete={submitLoginCode}
		/>
		{#if loginCodeError}
			<Helper color="red" class="mt-1 block text-center">{loginCodeError}</Helper>
		{:else}
			<Helper class="mt-1 block text-center">
				Введи 6 цифр из письма. Не пришло — проверь папку «Спам».
			</Helper>
		{/if}
	</div>

	<Button
		type="submit"
		color="primary"
		class="min-h-11 w-full rounded-xl font-medium"
		disabled={busy || loginCode.length < 6}
	>
		{#if activeAction === 'code-login'}
			<Spinner size="4" class="mr-2" color="primary" />
			Проверяем…
		{:else}
			Войти по коду
		{/if}
	</Button>

	<div class="flex flex-col space-y-2">
		<CaptchaWidget bind:token={captchaToken} bind:reset={resetCaptcha} />

		<Button
			type="button"
			color="alternative"
			class="min-h-11 w-full rounded-xl font-medium"
			disabled={busy || resendCooldown > 0}
			onclick={() => void handleLoginCodeRequest()}
		>
			{#if isResending}
				<Spinner size="4" class="mr-2" color="primary" />
				Отправляем…
			{:else if resendCooldown > 0}
				Отправить код ещё раз ({resendCooldown} сек.)
			{:else}
				<RefreshOutline class="me-2 h-4 w-4" />
				Отправить код ещё раз
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
	</div>
</form>
