<script lang="ts">
	import type { PinInputCell } from 'bits-ui';

	import { createApiClient } from '$lib/api';
	const client = createApiClient();
	import { getApiErrorDetail } from '$lib/api/errors';
	import CaptchaWidget, { captchaEnabled } from '$lib/components/CaptchaWidget.svelte';
	import * as Alert from '$lib/components/ui/alert';
	import { Button } from '$lib/components/ui/button';
	import * as InputOTP from '$lib/components/ui/input-otp';
	import { Label } from '$lib/components/ui/label';
	import { Spinner } from '$lib/components/ui/spinner';
	import { CaptchaGate } from '$lib/services/captcha.svelte';
	import { ResendCooldown } from '$lib/services/cooldown.svelte';
	import { getEventsClient } from '$lib/services/events.svelte';
	import { getToastService } from '$lib/services/toasts.svelte';
	import { completeLogin } from '$lib/utils/auth';
	import { isValidOtp } from '$lib/utils/validation';
	import { ArrowLeft, RotateCw } from '@lucide/svelte';
	import { onMount } from 'svelte';

	interface Props {
		email: string;
		onBack?: () => void;
	}

	let { email, onBack }: Props = $props();

	type ActiveAction = 'code-request' | 'code-login' | null;

	let loginCode = $state('');
	let activeAction = $state<ActiveAction>(null);
	let loginCodeError = $state('');
	let formError = $state('');

	const cooldown = new ResendCooldown();

	// Captcha state for the "resend code" request (same endpoint as the first one).
	let captchaToken = $state<string | null>(null);
	let resetCaptcha = $state<(() => void) | undefined>(undefined);
	let executeCaptcha = $state<(() => void) | undefined>(undefined);

	// Holds a resend the user tapped before the invisible captcha had a token.
	const captchaGate = new CaptchaGate();

	// Resend is in flight when its request runs or we're holding it for the captcha.
	let isResending = $derived(activeAction === 'code-request' || captchaGate.awaitingCaptcha);
	// Any in-flight work in this form (verifying the code, or resending it).
	let busy = $derived(activeAction !== null || captchaGate.awaitingCaptcha);

	const eventsClient = getEventsClient();
	const toastService = getToastService();

	// Fulfill a deferred resend the moment the invisible captcha solves.
	function handleCaptchaSolved() {
		if (captchaGate.awaitingCaptcha) {
			void handleLoginCodeRequest();
		}
	}

	onMount(() => {
		cooldown.start();
		return () => {
			cooldown.stop();
			captchaGate.clear();
		};
	});

	function resetLoginCodeFeedback() {
		loginCodeError = '';
		formError = '';
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

			await completeLogin(toastService, eventsClient, 'Вход выполнен');
		} catch (err) {
			console.error('Login code submit exception:', err);
			formError = 'Произошла непредвиденная ошибка. Попробуй ещё раз';
		} finally {
			activeAction = null;
		}
	}

	async function handleLoginCodeRequest() {
		// The captcha runs invisibly. If its token isn't ready yet, start the
		// challenge and hold the resend; handleCaptchaSolved re-runs this once the
		// token arrives.
		if (captchaEnabled && !captchaToken) {
			executeCaptcha?.();
			captchaGate.hold(() => {
				formError = 'Не удалось пройти проверку. Попробуй ещё раз';
			});
			return;
		}

		captchaGate.release();
		activeAction = 'code-request';
		loginCodeError = '';
		formError = '';

		try {
			const { error, response } = await client.POST('/auth/request-login-code', {
				body: { email, captcha_token: captchaToken }
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
			cooldown.start();
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

<form onsubmit={handleSubmit} class="flex flex-col gap-4">
	{#if formError}
		<Alert.Root variant="destructive">
			<Alert.Description>{formError}</Alert.Description>
		</Alert.Root>
	{/if}

	<Alert.Root variant="success">
		<Alert.Description>Код отправлен на <span class="font-medium">{email}</span>.</Alert.Description
		>
	</Alert.Root>

	<div class="flex flex-col items-center gap-2">
		<Label>Код подтверждения</Label>
		<InputOTP.Root
			maxlength={6}
			bind:value={loginCode}
			disabled={busy}
			aria-invalid={Boolean(loginCodeError)}
			onValueChange={resetLoginCodeFeedback}
			onComplete={submitLoginCode}
		>
			{#snippet children({ cells }: { cells: PinInputCell[] })}
				<InputOTP.Group>
					{#each cells.slice(0, 3) as cell, index (index)}
						<InputOTP.Slot {cell} class="size-11 text-lg font-bold sm:size-12 sm:text-xl" />
					{/each}
				</InputOTP.Group>
				<InputOTP.Separator />
				<InputOTP.Group>
					{#each cells.slice(3, 6) as cell, index (index + 3)}
						<InputOTP.Slot {cell} class="size-11 text-lg font-bold sm:size-12 sm:text-xl" />
					{/each}
				</InputOTP.Group>
			{/snippet}
		</InputOTP.Root>
		{#if loginCodeError}
			<p class="text-center text-xs text-destructive">{loginCodeError}</p>
		{:else}
			<p class="text-center text-xs text-muted-foreground">
				Введи 6 цифр из письма. Не пришло — проверь папку «Спам».
			</p>
		{/if}
	</div>

	<Button type="submit" class="min-h-11 w-full font-medium" disabled={busy || loginCode.length < 6}>
		{#if activeAction === 'code-login'}
			<Spinner data-icon="inline-start" />
			Проверяем…
		{:else}
			Войти по коду
		{/if}
	</Button>

	<div class="flex flex-col gap-2">
		<CaptchaWidget
			bind:token={captchaToken}
			bind:reset={resetCaptcha}
			bind:execute={executeCaptcha}
			onSolve={handleCaptchaSolved}
		/>

		<Button
			type="button"
			variant="outline"
			class="min-h-11 w-full font-medium"
			disabled={busy || cooldown.remaining > 0}
			onclick={() => void handleLoginCodeRequest()}
		>
			{#if isResending}
				<Spinner data-icon="inline-start" />
				Отправляем…
			{:else if cooldown.remaining > 0}
				Отправить код ещё раз ({cooldown.remaining} сек.)
			{:else}
				<RotateCw data-icon="inline-start" />
				Отправить код ещё раз
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
	</div>
</form>
