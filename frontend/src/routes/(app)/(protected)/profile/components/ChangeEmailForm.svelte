<script lang="ts">
	import Mail from '@lucide/svelte/icons/mail';

	import type { ChangeEmailInput } from '#lib/api/generated/index.js';

	import { getApiErrorCode, getApiErrorDetail, getApiFieldError } from '#lib/api/errors.js';
	import FormError from '#lib/components/FormError.svelte';
	import ResendCodeButton from '#lib/components/ResendCodeButton.svelte';
	import { Button } from '#lib/components/ui/button/index.js';
	import * as Dialog from '#lib/components/ui/dialog/index.js';
	import * as Field from '#lib/components/ui/field/index.js';
	import * as InputGroup from '#lib/components/ui/input-group/index.js';
	import { Spinner } from '#lib/components/ui/spinner/index.js';
	import VerificationCodeInput from '#lib/components/VerificationCodeInput.svelte';
	import { m } from '#lib/paraglide/messages.js';
	import { ResendCooldown } from '#lib/services/cooldown.svelte.js';
	import { getToastService } from '#lib/services/toasts.svelte.js';
	import { isValidEmail, isValidOtp, normalizeEmail } from '#lib/utils/validation.js';

	interface Props {
		currentEmail?: string | null;
		sending: boolean;
		confirming: boolean;
		/** Sends a code to the new address; rejects with the API error body. */
		onSendCode: (body: ChangeEmailInput) => Promise<void>;
		/** Confirms the code; rejects with the API error body. */
		onConfirm: (code: string) => Promise<void>;
	}

	let { currentEmail, sending, confirming, onSendCode, onConfirm }: Props = $props();
	const toastService = getToastService();

	let isBusy = $derived(sending || confirming);

	// Two-step flow: 'email' collects and sends the OTP, 'verify' confirms it.
	// Mounted fresh on every open (inside Dialog.Content), so each open starts at
	// the email step with an idle cooldown (its interval clears itself on unmount).
	let step = $state<'email' | 'verify'>('email');
	let newEmail = $state('');
	let emailError = $state('');

	let verificationCode = $state('');
	let verificationCodeError = $state('');

	const cooldown = new ResendCooldown();

	let formError = $state('');

	function handleEmailInput() {
		emailError = '';
		formError = '';
	}

	async function sendOtp() {
		if (sending) return;

		verificationCodeError = '';
		formError = '';
		try {
			await onSendCode({ new_email: normalizeEmail(newEmail) });
		} catch (error) {
			formError = getApiErrorDetail(error) ?? m.email_change_send_code_failed();
			return;
		}
		verificationCode = '';
		toastService.add(m.email_change_code_sent_toast(), 'success');
		cooldown.start();
	}

	async function handleSubmit(e: Event) {
		e.preventDefault();
		emailError = '';

		const trimmedEmail = normalizeEmail(newEmail);

		if (!isValidEmail(trimmedEmail)) {
			emailError = m.validation_email_format();
			return;
		}

		try {
			await onSendCode({ new_email: trimmedEmail });
		} catch (error) {
			const emailFieldError = getApiFieldError(error, 'new_email');
			if (emailFieldError) {
				emailError = emailFieldError;
				return;
			}
			if (getApiErrorCode(error) === 'EMAIL_ALREADY_EXISTS') {
				emailError = getApiErrorDetail(error) ?? m.error_email_already_exists();
				return;
			}
			formError = getApiErrorDetail(error) ?? m.email_change_send_code_failed();
			return;
		}
		toastService.add(m.email_change_code_sent_new(), 'success');
		step = 'verify';
		cooldown.start();
	}

	async function submitVerificationCode() {
		verificationCodeError = '';

		if (verificationCode.length !== 6) {
			verificationCodeError = m.validation_code_required();
			return;
		}

		if (!isValidOtp(verificationCode)) {
			verificationCodeError = m.validation_code_length();
			return;
		}

		try {
			await onConfirm(verificationCode);
		} catch (error) {
			const codeFieldError = getApiFieldError(error, 'code');
			if (codeFieldError) {
				verificationCodeError = codeFieldError;
				return;
			}
			if (getApiErrorCode(error) === 'INVALID_OTP_CODE') {
				verificationCodeError = getApiErrorDetail(error) ?? m.error_invalid_otp_code();
				return;
			}
			formError = getApiErrorDetail(error) ?? m.email_change_verify_failed();
		}
	}
</script>

{#if step === 'email'}
	<!-- novalidate: the browser's own type="email" bubble would pre-empt the
	     field error handleSubmit shows. -->
	<form onsubmit={handleSubmit} novalidate class="flex flex-col gap-4">
		<FormError message={formError} />

		<Field.FieldGroup class="gap-4">
			{#if currentEmail}
				<Field.Field data-disabled={true}>
					<Field.FieldLabel>{m.email_current_label()}</Field.FieldLabel>
					<InputGroup.Root data-disabled="true">
						<InputGroup.Addon>
							<Mail aria-hidden="true" />
						</InputGroup.Addon>
						<InputGroup.Input
							type="text"
							name="current_email"
							value={currentEmail}
							disabled
							autocomplete="email"
						/>
					</InputGroup.Root>
				</Field.Field>
			{/if}

			<Field.Field data-invalid={emailError ? true : undefined}>
				<Field.FieldLabel for="new_email">{m.email_new_label()}</Field.FieldLabel>
				<InputGroup.Root>
					<InputGroup.Addon>
						<Mail aria-hidden="true" />
					</InputGroup.Addon>
					<InputGroup.Input
						id="new_email"
						name="new_email"
						type="email"
						placeholder="name@example.com"
						autocomplete="email"
						inputmode="email"
						autocapitalize="off"
						spellcheck={false}
						bind:value={newEmail}
						aria-invalid={emailError ? true : undefined}
						oninput={handleEmailInput}
					/>
				</InputGroup.Root>
				{#if emailError}
					<Field.FieldError>{emailError}</Field.FieldError>
				{:else}
					<Field.FieldDescription>
						{currentEmail ? m.email_change_hint() : m.email_add_hint()}
					</Field.FieldDescription>
				{/if}
			</Field.Field>
		</Field.FieldGroup>

		<div class="flex flex-col-reverse gap-2 sm:grid sm:grid-cols-2">
			<Dialog.Close>
				{#snippet child({ props })}
					<Button variant="outline" {...props}>{m.common_cancel()}</Button>
				{/snippet}
			</Dialog.Close>
			<Button type="submit" disabled={sending}>
				{#if sending}
					<Spinner data-icon="inline-start" />
					{m.email_sending_code()}
				{:else}
					{currentEmail ? m.email_send_code() : m.email_add_address()}
				{/if}
			</Button>
		</div>
	</form>
{:else}
	<div class="flex flex-col gap-4">
		<FormError message={formError} />

		<Field.Field data-disabled={true}>
			<Field.FieldLabel>{m.email_new_label()}</Field.FieldLabel>
			<InputGroup.Root data-disabled="true">
				<InputGroup.Addon>
					<Mail aria-hidden="true" />
				</InputGroup.Addon>
				<InputGroup.Input type="text" value={normalizeEmail(newEmail)} disabled />
			</InputGroup.Root>
			<Field.FieldDescription>{m.email_code_sent_here()}</Field.FieldDescription>
		</Field.Field>

		<VerificationCodeInput
			id="email-change-code"
			bind:value={verificationCode}
			hint={m.verification_code_hint()}
			error={verificationCodeError}
			busy={isBusy}
			onValueChange={() => {
				verificationCodeError = '';
				formError = '';
			}}
			onComplete={submitVerificationCode}
		/>

		<div class="flex flex-col gap-2 pt-2">
			<Button class="w-full" disabled={isBusy} onclick={submitVerificationCode}>
				{#if confirming}
					<Spinner data-icon="inline-start" />
					{m.common_checking()}
				{:else}
					{m.email_confirm_code()}
				{/if}
			</Button>

			<ResendCodeButton {sending} remaining={cooldown.remaining} busy={isBusy} onclick={sendOtp} />
		</div>
	</div>
{/if}
