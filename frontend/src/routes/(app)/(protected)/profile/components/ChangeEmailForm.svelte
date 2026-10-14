<script lang="ts">
	import type { PinInputCell } from 'bits-ui';

	import { Mail } from '@lucide/svelte';
	import { createMutation, useQueryClient } from '@tanstack/svelte-query';
	import { onDestroy } from 'svelte';

	import type { ChangeEmailInput } from '#lib/api/generated/index.js';

	import { getApiErrorCode, getApiErrorDetail, getApiFieldError } from '#lib/api/errors.js';
	import {
		changeCurrentUserEmailMutation,
		confirmEmailCodeMutation,
		getCurrentUserQueryKey
	} from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import * as Alert from '#lib/components/ui/alert/index.js';
	import { Button } from '#lib/components/ui/button/index.js';
	import * as Dialog from '#lib/components/ui/dialog/index.js';
	import * as Field from '#lib/components/ui/field/index.js';
	import * as InputOTP from '#lib/components/ui/input-otp/index.js';
	import { Input } from '#lib/components/ui/input/index.js';
	import { Label } from '#lib/components/ui/label/index.js';
	import { Spinner } from '#lib/components/ui/spinner/index.js';
	import { ResendCooldown } from '#lib/services/cooldown.svelte.js';
	import { getToastService } from '#lib/services/toasts.svelte.js';
	import { isValidEmail, isValidOtp, normalizeEmail } from '#lib/utils/validation.js';

	interface Props {
		currentEmail?: string | null;
		onclose: () => void;
	}

	let { currentEmail, onclose }: Props = $props();
	const queryClient = useQueryClient();
	const toastService = getToastService();

	// Sends the code — first from the email step, then as «Отправить код ещё раз».
	const changeEmailMutation = createMutation(() => changeCurrentUserEmailMutation());
	// The toast lives here, not in `mutate()`'s callbacks: those are dropped if the
	// dialog is dismissed while the request is in flight, which would lose the
	// confirmation of an address that was in fact verified.
	// Not awaited: the refreshed user flips `currentEmail`, and with it this
	// dialog's title, so the dialog closes first.
	const confirmMutation = createMutation(() => ({
		...confirmEmailCodeMutation(),
		onSuccess: () => {
			toastService.add('Почта подтверждена', 'success');
			void queryClient.invalidateQueries({ queryKey: getCurrentUserQueryKey() });
		}
	}));
	let isBusy = $derived(changeEmailMutation.isPending || confirmMutation.isPending);

	// Two-step flow: 'email' collects and sends the OTP, 'verify' confirms it.
	let step = $state<'email' | 'verify'>('email');
	let newEmail = $state('');
	let emailError = $state('');

	let verificationCode = $state('');
	let verificationCodeError = $state('');

	const cooldown = new ResendCooldown();

	let formError = $state('');

	// Screen-reader description for the dialog (visually the form speaks for itself).
	let dialogDescription = $derived(
		currentEmail
			? 'Измени адрес электронной почты — понадобится код из письма.'
			: 'Добавь адрес электронной почты — понадобится код из письма.'
	);

	function handleEmailInput() {
		emailError = '';
		formError = '';
	}

	function sendOtp() {
		if (changeEmailMutation.isPending) return;

		verificationCodeError = '';
		formError = '';
		changeEmailMutation.mutate(
			{ body: { new_email: normalizeEmail(newEmail) } },
			{
				onSuccess: () => {
					verificationCode = '';
					toastService.add('Код для подтверждения отправлен на почту', 'success');
					cooldown.start();
				},
				onError: (error) => {
					formError = getApiErrorDetail(error) ?? 'Не удалось отправить код подтверждения';
				}
			}
		);
	}

	function handleSubmit(e: Event) {
		e.preventDefault();
		emailError = '';

		const trimmedEmail = normalizeEmail(newEmail);

		if (!isValidEmail(trimmedEmail)) {
			emailError = 'Введи адрес в формате name@example.com';
			return;
		}

		const body: ChangeEmailInput = { new_email: trimmedEmail };
		changeEmailMutation.mutate(
			{ body },
			{
				onSuccess: () => {
					toastService.add('Код подтверждения отправлен на новый адрес.', 'success');
					step = 'verify';
					cooldown.start();
				},
				onError: (error) => {
					const emailFieldError = getApiFieldError(error, 'new_email');
					if (emailFieldError) {
						emailError = emailFieldError;
						return;
					}
					if (getApiErrorCode(error) === 'EMAIL_ALREADY_EXISTS') {
						emailError = getApiErrorDetail(error) ?? 'Этот адрес уже используется';
						return;
					}
					formError = getApiErrorDetail(error) ?? 'Не удалось отправить код подтверждения';
				}
			}
		);
	}

	function submitVerificationCode() {
		verificationCodeError = '';

		if (verificationCode.length !== 6) {
			verificationCodeError = 'Введи код из письма';
			return;
		}

		if (!isValidOtp(verificationCode)) {
			verificationCodeError = 'Код должен состоять из 6 цифр';
			return;
		}

		confirmMutation.mutate(
			{ body: { code: verificationCode } },
			{
				onSuccess: onclose,
				onError: (error) => {
					const codeFieldError = getApiFieldError(error, 'code');
					if (codeFieldError) {
						verificationCodeError = codeFieldError;
						return;
					}
					if (getApiErrorCode(error) === 'INVALID_OTP_CODE') {
						verificationCodeError = getApiErrorDetail(error) ?? 'Неверный или устаревший код';
						return;
					}
					formError = getApiErrorDetail(error) ?? 'Не удалось подтвердить код';
				}
			}
		);
	}

	onDestroy(() => {
		cooldown.stop();
	});
</script>

<Dialog.Header>
	<Dialog.Title class="flex items-center gap-2">
		<Mail class="size-5 text-muted-foreground" />
		{currentEmail ? 'Изменить эл. почту' : 'Добавить эл. почту'}
	</Dialog.Title>
	<Dialog.Description class="sr-only">{dialogDescription}</Dialog.Description>
</Dialog.Header>

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
					<Field.FieldLabel>Текущая эл. почта</Field.FieldLabel>
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
				<Field.FieldLabel for="new_email">Новая эл. почта</Field.FieldLabel>
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
						{currentEmail
							? 'На новый адрес придёт код. Почта изменится только после подтверждения.'
							: 'На этот адрес придёт письмо с кодом подтверждения.'}
					</Field.FieldDescription>
				{/if}
			</Field.Field>
		</Field.FieldGroup>

		<Button type="submit" class="w-full" disabled={changeEmailMutation.isPending}>
			{#if changeEmailMutation.isPending}
				<Spinner data-icon="inline-start" />
				Отправка кода…
			{:else}
				{currentEmail ? 'Отправить код' : 'Добавить адрес'}
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
			<Field.FieldLabel>Новая эл. почта</Field.FieldLabel>
			<div class="relative flex items-center">
				<Mail class="pointer-events-none absolute left-3 size-4 text-muted-foreground" />
				<Input type="text" value={normalizeEmail(newEmail)} disabled class="pl-9" />
			</div>
			<Field.FieldDescription>Код подтверждения отправлен на этот адрес.</Field.FieldDescription>
		</Field.Field>

		<div class="flex flex-col items-center gap-2">
			<Label>Код подтверждения</Label>
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
				<p class="text-center text-sm text-muted-foreground">Введи 6 цифр из письма.</p>
			{/if}
		</div>

		<div class="flex flex-col gap-2 pt-2">
			<Button class="w-full" disabled={isBusy} onclick={submitVerificationCode}>
				{#if confirmMutation.isPending}
					<Spinner data-icon="inline-start" />
					Проверяем…
				{:else}
					Подтвердить код
				{/if}
			</Button>

			<Button
				type="button"
				variant="outline"
				class="w-full"
				disabled={isBusy || cooldown.remaining > 0}
				onclick={sendOtp}
			>
				{#if changeEmailMutation.isPending}
					<Spinner data-icon="inline-start" />
					Отправляем…
				{:else if cooldown.remaining > 0}
					Отправить код ещё раз ({cooldown.remaining} сек.)
				{:else}
					Отправить код ещё раз
				{/if}
			</Button>
		</div>
	</div>
{/if}
