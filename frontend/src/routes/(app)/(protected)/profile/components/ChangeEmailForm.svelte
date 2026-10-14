<script lang="ts">
	import type { PinInputCell } from 'bits-ui';

	import { Mail } from '@lucide/svelte';

	import type { ChangeEmailInput } from '#lib/api/generated/index.js';

	import { getApiErrorCode, getApiErrorDetail, getApiFieldError } from '#lib/api/errors.js';
	import * as Alert from '#lib/components/ui/alert/index.js';
	import { Button } from '#lib/components/ui/button/index.js';
	import * as Field from '#lib/components/ui/field/index.js';
	import * as InputOTP from '#lib/components/ui/input-otp/index.js';
	import { Input } from '#lib/components/ui/input/index.js';
	import { Label } from '#lib/components/ui/label/index.js';
	import { Spinner } from '#lib/components/ui/spinner/index.js';
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
			formError = getApiErrorDetail(error) ?? m.email_send_code_failed();
			return;
		}
		verificationCode = '';
		toastService.add(m.email_code_sent(), 'success');
		cooldown.start();
	}

	async function handleSubmit(e: Event) {
		e.preventDefault();
		emailError = '';

		const trimmedEmail = normalizeEmail(newEmail);

		if (!isValidEmail(trimmedEmail)) {
			emailError = m.email_invalid_format();
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
			formError = getApiErrorDetail(error) ?? m.email_send_code_failed();
			return;
		}
		toastService.add(m.email_code_sent_new(), 'success');
		step = 'verify';
		cooldown.start();
	}

	async function submitVerificationCode() {
		verificationCodeError = '';

		if (verificationCode.length !== 6) {
			verificationCodeError = m.email_code_required();
			return;
		}

		if (!isValidOtp(verificationCode)) {
			verificationCodeError = m.email_code_six_digits();
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
			formError = getApiErrorDetail(error) ?? m.email_code_verify_failed();
		}
	}
</script>

{#if step === 'email'}
	<!-- novalidate: the browser's own type="email" bubble would pre-empt the
	     field error handleSubmit shows. -->
	<form onsubmit={handleSubmit} novalidate class="flex flex-col gap-4">
		{#if formError}
			<Alert.Root variant="destructive">
				<Alert.Description>{formError}</Alert.Description>
			</Alert.Root>
		{/if}

		<Field.FieldGroup class="gap-4">
			{#if currentEmail}
				<Field.Field data-disabled={true}>
					<Field.FieldLabel>{m.email_current_label()}</Field.FieldLabel>
					<div class="relative flex items-center">
						<Mail class="pointer-events-none absolute left-3 size-4 text-muted-foreground" />
						<Input
							type="text"
							name="current_email"
							value={currentEmail}
							disabled
							autocomplete="email"
							class="pl-9"
						/>
					</div>
				</Field.Field>
			{/if}

			<Field.Field data-invalid={emailError ? true : undefined}>
				<Field.FieldLabel for="new_email">{m.email_new_label()}</Field.FieldLabel>
				<div class="relative flex items-center">
					<Mail class="pointer-events-none absolute left-3 size-4 text-muted-foreground" />
					<Input
						id="new_email"
						name="new_email"
						type="email"
						placeholder="name@example.com"
						autocomplete="email"
						inputmode="email"
						autocapitalize="off"
						spellcheck={false}
						bind:value={newEmail}
						class="pl-9"
						aria-invalid={emailError ? true : undefined}
						oninput={handleEmailInput}
					/>
				</div>
				{#if emailError}
					<Field.FieldError>{emailError}</Field.FieldError>
				{:else}
					<Field.FieldDescription>
						{currentEmail ? m.email_hint_change() : m.email_hint_add()}
					</Field.FieldDescription>
				{/if}
			</Field.Field>
		</Field.FieldGroup>

		<Button type="submit" class="w-full" disabled={sending}>
			{#if sending}
				<Spinner data-icon="inline-start" />
				{m.email_sending_code()}
			{:else}
				{currentEmail ? m.email_send_code() : m.email_add_address()}
			{/if}
		</Button>
	</form>
{:else}
	<div class="flex flex-col gap-4">
		{#if formError}
			<Alert.Root variant="destructive">
				<Alert.Description>{formError}</Alert.Description>
			</Alert.Root>
		{/if}

		<Field.Field data-disabled={true}>
			<Field.FieldLabel>{m.email_new_label()}</Field.FieldLabel>
			<div class="relative flex items-center">
				<Mail class="pointer-events-none absolute left-3 size-4 text-muted-foreground" />
				<Input type="text" value={normalizeEmail(newEmail)} disabled class="pl-9" />
			</div>
			<Field.FieldDescription>{m.email_code_sent_to_address()}</Field.FieldDescription>
		</Field.Field>

		<div class="flex flex-col items-center gap-2">
			<Label>{m.email_code_label()}</Label>
			<InputOTP.Root
				maxlength={6}
				bind:value={verificationCode}
				disabled={isBusy}
				aria-invalid={Boolean(verificationCodeError)}
				onValueChange={() => {
					verificationCodeError = '';
					formError = '';
				}}
				onComplete={submitVerificationCode}
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
			{#if verificationCodeError}
				<p class="text-center text-sm text-destructive">{verificationCodeError}</p>
			{:else}
				<p class="text-center text-sm text-muted-foreground">{m.email_enter_six_digits()}</p>
			{/if}
		</div>

		<div class="flex flex-col gap-2 pt-2">
			<Button class="w-full" disabled={isBusy} onclick={submitVerificationCode}>
				{#if confirming}
					<Spinner data-icon="inline-start" />
					{m.email_verifying()}
				{:else}
					{m.email_verify()}
				{/if}
			</Button>

			<Button
				type="button"
				variant="outline"
				class="w-full"
				disabled={isBusy || cooldown.remaining > 0}
				onclick={sendOtp}
			>
				{#if sending}
					<Spinner data-icon="inline-start" />
					{m.email_resending()}
				{:else if cooldown.remaining > 0}
					{m.email_resend_cooldown({ seconds: cooldown.remaining })}
				{:else}
					{m.email_resend()}
				{/if}
			</Button>
		</div>
	</div>
{/if}
