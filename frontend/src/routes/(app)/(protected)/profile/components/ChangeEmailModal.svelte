<script lang="ts">
	import type { components } from '$lib/api/schema';
	import type { PinInputCell } from 'bits-ui';

	import { createApiClient } from '$lib/api';
	import { getApiErrorDetail } from '$lib/api/errors';
	import * as Alert from '$lib/components/ui/alert';
	import { Button } from '$lib/components/ui/button';
	import * as Dialog from '$lib/components/ui/dialog';
	import * as Field from '$lib/components/ui/field';
	import { Input } from '$lib/components/ui/input';
	import * as InputOTP from '$lib/components/ui/input-otp';
	import { Label } from '$lib/components/ui/label';
	import { Spinner } from '$lib/components/ui/spinner';
	import { ResendCooldown } from '$lib/services/cooldown.svelte';
	import { getToastService } from '$lib/services/toasts.svelte';
	import { isValidEmail, isValidOtp, normalizeEmail } from '$lib/utils/validation';
	import { Mail } from '@lucide/svelte';
	import { onDestroy } from 'svelte';

	const client = createApiClient();

	type ChangeEmailInput = components['schemas']['ChangeEmailInput'];

	interface Props {
		open: boolean;
		currentEmail?: string | null;
		onSuccess?: () => void;
	}

	let { open = $bindable(false), currentEmail, onSuccess }: Props = $props();

	// Two-step flow: 'email' collects and sends the OTP, 'verify' confirms it.
	let step = $state<'email' | 'verify'>('email');
	let newEmail = $state('');
	let emailError = $state('');
	let isLoading = $state(false);

	let verificationCode = $state('');
	let verificationCodeError = $state('');
	let isVerifying = $state(false);
	let isRequestingVerification = $state(false);

	const cooldown = new ResendCooldown();

	const toastService = getToastService();
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

	async function sendOtp() {
		if (isRequestingVerification) return;

		isRequestingVerification = true;
		verificationCodeError = '';
		formError = '';

		try {
			const body: ChangeEmailInput = { new_email: normalizeEmail(newEmail) };
			const { error, response } = await client.POST('/me/email', { body });

			if (error || !response.ok) {
				formError = getApiErrorDetail(error) ?? 'Не удалось отправить код подтверждения';
				return;
			}

			verificationCode = '';
			toastService.add('Код для подтверждения отправлен на почту', 'success');
			cooldown.start();
		} catch {
			formError = 'Произошла непредвиденная ошибка';
		} finally {
			isRequestingVerification = false;
		}
	}

	async function handleSubmit(e: Event) {
		e.preventDefault();
		emailError = '';

		const trimmedEmail = normalizeEmail(newEmail);

		if (!isValidEmail(trimmedEmail)) {
			emailError = 'Введи адрес в формате name@example.com';
			return;
		}

		isLoading = true;

		const body: ChangeEmailInput = { new_email: trimmedEmail };
		const { error, response } = await client.POST('/me/email', { body });

		isLoading = false;

		if (error) {
			if (response.status === 409) {
				emailError = getApiErrorDetail(error) ?? 'Этот адрес уже используется';
				return;
			}
			formError = getApiErrorDetail(error) ?? 'Не удалось отправить код подтверждения';
			return;
		}

		toastService.add('Код подтверждения отправлен на новый адрес.', 'success');
		step = 'verify';
		cooldown.start();
	}

	async function submitVerificationCode() {
		verificationCodeError = '';

		if (verificationCode.length !== 6) {
			verificationCodeError = 'Введи код из письма';
			return;
		}

		if (!isValidOtp(verificationCode)) {
			verificationCodeError = 'Код должен состоять из 6 цифр';
			return;
		}

		isVerifying = true;

		try {
			const { error, response } = await client.POST('/auth/confirm-email-code', {
				body: { code: verificationCode }
			});

			if (error) {
				if (response.status === 400) {
					verificationCodeError = getApiErrorDetail(error) ?? 'Неверный или устаревший код';
					return;
				}
				formError = getApiErrorDetail(error) ?? 'Не удалось подтвердить код';
				return;
			}

			toastService.add('Почта подтверждена', 'success');
			verificationCode = '';
			verificationCodeError = '';
			open = false;
			if (onSuccess) onSuccess();
		} catch {
			formError = 'Произошла непредвиденная ошибка';
		} finally {
			isVerifying = false;
		}
	}

	$effect(() => {
		if (open) {
			step = 'email';
			newEmail = '';
			emailError = '';
			verificationCode = '';
			verificationCodeError = '';
			formError = '';
		} else {
			cooldown.reset();
		}
	});

	onDestroy(() => {
		cooldown.stop();
	});
</script>

<Dialog.Root bind:open>
	<Dialog.Content class="sm:max-w-md">
		<Dialog.Header>
			<Dialog.Title class="flex items-center gap-2">
				<Mail class="size-5 text-muted-foreground" />
				{currentEmail ? 'Изменить эл. почту' : 'Добавить эл. почту'}
			</Dialog.Title>
			<Dialog.Description class="sr-only">{dialogDescription}</Dialog.Description>
		</Dialog.Header>

		{#if step === 'email'}
			<form onsubmit={handleSubmit} class="flex flex-col gap-4">
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

				<Button
					type="submit"
					class="w-full"
					disabled={isLoading || !isValidEmail(normalizeEmail(newEmail))}
				>
					{#if isLoading}
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
					<Field.FieldDescription>Код подтверждения отправлен на этот адрес.</Field.FieldDescription
					>
				</Field.Field>

				<div class="flex flex-col items-center gap-2">
					<Label>Код подтверждения</Label>
					<InputOTP.Root
						maxlength={6}
						bind:value={verificationCode}
						disabled={isVerifying || isRequestingVerification}
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
						<p class="text-center text-xs text-destructive">{verificationCodeError}</p>
					{:else}
						<p class="text-center text-xs text-muted-foreground">Введи 6 цифр из письма.</p>
					{/if}
				</div>

				<div class="flex flex-col gap-2 pt-2">
					<Button
						class="min-h-11 w-full font-medium"
						disabled={isVerifying || isRequestingVerification || verificationCode.length < 6}
						onclick={submitVerificationCode}
					>
						{#if isVerifying}
							<Spinner data-icon="inline-start" />
							Проверяем…
						{:else}
							Подтвердить код
						{/if}
					</Button>

					<Button
						type="button"
						variant="outline"
						class="min-h-11 w-full font-medium"
						disabled={isVerifying || isRequestingVerification || cooldown.remaining > 0}
						onclick={sendOtp}
					>
						{#if isRequestingVerification}
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
	</Dialog.Content>
</Dialog.Root>
