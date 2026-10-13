<script lang="ts">
	import { RotateCw } from '@lucide/svelte';
	import { createMutation, useQueryClient } from '@tanstack/svelte-query';
	import { type PinInputCell, REGEXP_ONLY_DIGITS } from 'bits-ui';
	import { onMount } from 'svelte';

	import { getApiErrorCode, getApiErrorDetail, getApiFieldError } from '#lib/api/errors.js';
	import {
		loginWithCodeMutation,
		requestLoginCodeMutation
	} from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import CaptchaWidget, { captchaEnabled } from '#lib/components/CaptchaWidget.svelte';
	import * as Alert from '#lib/components/ui/alert/index.js';
	import { Button } from '#lib/components/ui/button/index.js';
	import * as InputOTP from '#lib/components/ui/input-otp/index.js';
	import { Label } from '#lib/components/ui/label/index.js';
	import { Spinner } from '#lib/components/ui/spinner/index.js';
	import { CaptchaGate } from '#lib/services/captcha.svelte.js';
	import { ResendCooldown } from '#lib/services/cooldown.svelte.js';
	import { getEventsClient } from '#lib/services/events.svelte.js';
	import { getToastService } from '#lib/services/toasts.svelte.js';
	import { completeLogin } from '#lib/utils/auth.js';
	import { isValidOtp } from '#lib/utils/validation.js';

	interface Props {
		email: string;
	}

	let { email }: Props = $props();

	const eventsClient = getEventsClient();
	const queryClient = useQueryClient();
	const toastService = getToastService();

	// Pending until completeLogin has loaded the new identity and navigated, so
	// the form stays busy until the app moves on.
	const loginMutation = createMutation(() => ({
		...loginWithCodeMutation(),
		onSuccess: () => completeLogin(toastService, eventsClient, queryClient, 'Вход выполнен')
	}));
	const resendMutation = createMutation(() => requestLoginCodeMutation());

	let loginCode = $state('');
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
	let isResending = $derived(resendMutation.isPending || captchaGate.awaitingCaptcha);
	// Any in-flight work in this form (verifying the code, or resending it).
	let busy = $derived(
		loginMutation.isPending || resendMutation.isPending || captchaGate.awaitingCaptcha
	);

	// Fulfill a deferred resend the moment the invisible captcha solves.
	function handleCaptchaSolved() {
		if (captchaGate.awaitingCaptcha) {
			handleLoginCodeRequest();
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

	function submitLoginCode() {
		if (loginMutation.isPending || resendMutation.isPending) {
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

		loginCodeError = '';
		formError = '';

		loginMutation.mutate(
			{ body: { email, code: loginCode } },
			{
				onError: (error) => {
					// A rejected code is cleared so the next attempt starts from the first
					// box; focus never left the input, so typing can resume at once.
					const codeFieldError = getApiFieldError(error, 'code');
					if (codeFieldError) {
						loginCode = '';
						loginCodeError = codeFieldError;
						return;
					}
					if (getApiErrorCode(error) === 'INVALID_OTP_CODE') {
						loginCode = '';
						loginCodeError = getApiErrorDetail(error) ?? 'Неверный или устаревший код';
						return;
					}
					formError = getApiErrorDetail(error) ?? 'Не удалось выполнить вход';
				}
			}
		);
	}

	function handleLoginCodeRequest() {
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
		loginCodeError = '';
		formError = '';

		resendMutation.mutate(
			{ body: { email, captcha_token: captchaToken } },
			{
				onSuccess: () => {
					loginCode = '';
					toastService.add('Код отправлен повторно', 'success');
					// Each resend needs its own fresh token.
					resetCaptcha?.();
					captchaToken = null;
					cooldown.start();
				},
				onError: (error) => {
					formError = getApiErrorDetail(error) ?? 'Не удалось отправить код повторно';
					// The token is single-use, so fetch a fresh one before a retry.
					resetCaptcha?.();
					captchaToken = null;
				}
			}
		);
	}

	function handleSubmit(event: SubmitEvent) {
		event.preventDefault();
		if (loginMutation.isPending || resendMutation.isPending) return;
		submitLoginCode();
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
		<Label for="login-code">Код подтверждения</Label>
		<!-- Read-only, not disabled, while busy so focus and the phone keyboard stay
			put; digits-only so a stray letter can't auto-submit a doomed code. -->
		<InputOTP.Root
			inputId="login-code"
			maxlength={6}
			pattern={REGEXP_ONLY_DIGITS}
			bind:value={loginCode}
			readonly={busy}
			aria-invalid={loginCodeError ? true : undefined}
			aria-describedby="login-code-hint"
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
			<p id="login-code-hint" role="alert" class="text-center text-sm text-destructive">
				{loginCodeError}
			</p>
		{:else}
			<p id="login-code-hint" class="text-center text-sm text-muted-foreground">
				Введи 6 цифр из письма. Не пришло — проверь папку «Спам».
			</p>
		{/if}
	</div>

	<Button type="submit" class="w-full" disabled={busy || loginCode.length < 6}>
		{#if loginMutation.isPending}
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
			class="w-full"
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
	</div>
</form>
