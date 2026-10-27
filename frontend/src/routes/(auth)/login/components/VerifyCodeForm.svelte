<script lang="ts">
	import { ParaglideMessage } from '@inlang/paraglide-js-svelte';
	import { createMutation } from '@tanstack/svelte-query';
	import { onMount } from 'svelte';

	import type { MessageTagProps } from '#lib/types/markup.js';

	import { getApiErrorCode, getApiErrorDetail, getApiFieldError } from '#lib/api/errors.js';
	import {
		loginWithCodeMutation,
		requestLoginCodeMutation
	} from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import FormError from '#lib/components/FormError.svelte';
	import ResendCodeButton from '#lib/components/ResendCodeButton.svelte';
	import * as Alert from '#lib/components/ui/alert/index.js';
	import { Button } from '#lib/components/ui/button/index.js';
	import { Spinner } from '#lib/components/ui/spinner/index.js';
	import VerificationCodeInput from '#lib/components/VerificationCodeInput.svelte';
	import { m } from '#lib/paraglide/messages.js';
	import { trackEvent } from '#lib/services/analytics.js';
	import { Captcha } from '#lib/services/captcha.svelte.js';
	import { ResendCooldown } from '#lib/services/cooldown.svelte.js';
	import { getSession } from '#lib/services/session.js';
	import { getToastService } from '#lib/services/toasts.svelte.js';
	import { isValidOtp } from '#lib/utils/validation.js';

	interface Props {
		email: string;
	}

	let { email }: Props = $props();

	const session = getSession();
	const toastService = getToastService();

	const loginMutation = createMutation(() => ({
		...loginWithCodeMutation(),
		onSuccess: async () => {
			trackEvent('login', { method: 'code' });
			await session.loggedIn();
			toastService.add(m.login_success(), 'success');
		}
	}));
	const resendMutation = createMutation(() => requestLoginCodeMutation());

	let loginCode = $state('');
	let loginCodeError = $state('');
	let formError = $state('');

	const cooldown = new ResendCooldown();

	const captcha = new Captcha();

	let isResending = $derived(resendMutation.isPending || captcha.solving);
	let busy = $derived(loginMutation.isPending || isResending);

	onMount(() => {
		cooldown.start();
		return () => {
			cooldown.stop();
			captcha.dispose();
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
			loginCodeError = m.validation_code_required();
			return;
		}

		if (!isValidOtp(loginCode)) {
			loginCodeError = m.validation_code_length();
			return;
		}

		loginCodeError = '';
		formError = '';

		loginMutation.mutate(
			{ body: { email, code: loginCode } },
			{
				onError: (error) => {
					const codeFieldError = getApiFieldError(error, 'code');
					if (codeFieldError) {
						loginCode = '';
						loginCodeError = codeFieldError;
						return;
					}
					if (getApiErrorCode(error) === 'INVALID_OTP_CODE') {
						loginCode = '';
						loginCodeError = getApiErrorDetail(error) ?? m.error_invalid_otp_code();
						return;
					}
					formError = getApiErrorDetail(error) ?? m.login_failed_generic();
				}
			}
		);
	}

	async function handleLoginCodeRequest() {
		if (busy) {
			return;
		}
		loginCodeError = '';
		formError = '';

		let captchaToken: string | null;
		try {
			captchaToken = await captcha.take();
		} catch (error) {
			formError = getApiErrorDetail(error) ?? m.captcha_failed();
			return;
		}

		resendMutation.mutate(
			{ body: { email, captcha_token: captchaToken } },
			{
				onSuccess: () => {
					loginCode = '';
					toastService.add(m.login_code_resent(), 'success');
					cooldown.start();
				},
				onError: (error) => {
					formError = getApiErrorDetail(error) ?? m.login_code_resend_failed();
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
	<FormError message={formError} />

	<Alert.Root variant="success">
		<Alert.Description>
			<ParaglideMessage message={m.login_code_sent_to} inputs={{ email }}>
				{#snippet address({ children }: MessageTagProps)}<span class="font-medium"
						>{@render children?.()}</span
					>{/snippet}
			</ParaglideMessage>
		</Alert.Description>
	</Alert.Root>

	<VerificationCodeInput
		id="login-code"
		bind:value={loginCode}
		hint={m.login_code_hint_with_spam()}
		error={loginCodeError}
		{busy}
		onValueChange={resetLoginCodeFeedback}
		onComplete={submitLoginCode}
	/>

	<Button type="submit" class="w-full" disabled={busy || loginCode.length < 6}>
		{#if loginMutation.isPending}
			<Spinner data-icon="inline-start" />
			{m.common_checking()}
		{:else}
			{m.login_via_code()}
		{/if}
	</Button>

	<ResendCodeButton
		sending={isResending}
		remaining={cooldown.remaining}
		{busy}
		onclick={() => handleLoginCodeRequest()}
	/>
</form>
