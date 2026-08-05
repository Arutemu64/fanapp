<script lang="ts">
	import type { components } from '$lib/api/schema';

	import { createApiClient } from '$lib/api';
	import { getApiErrorDetail } from '$lib/api/errors';
	import OtpInput from '$lib/components/OtpInput.svelte';
	import { getToastService } from '$lib/services/toasts.svelte';
	import { ResendCooldown } from '$lib/utils/cooldown.svelte';
	import { isValidEmail, isValidOtp, normalizeEmail } from '$lib/utils/validation';
	import { Alert, Button, Helper, Input, Label, Modal, Spinner } from 'flowbite-svelte';
	import { EnvelopeSolid } from 'flowbite-svelte-icons';
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

	let emailColor = $derived.by((): 'green' | 'red' | undefined => {
		if (emailError) return 'red';
		if (!newEmail) return undefined;
		return isValidEmail(normalizeEmail(newEmail)) ? 'green' : 'red';
	});

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

<Modal bind:open size="sm" outsideclose={step !== 'verify'}>
	{#snippet header()}
		<div class="flex items-center gap-2">
			<EnvelopeSolid class="h-5 w-5 text-gray-500 dark:text-gray-400" />
			<h3 class="text-lg font-bold text-gray-900 dark:text-white">
				{currentEmail ? 'Изменить эл. почту' : 'Добавить эл. почту'}
			</h3>
		</div>
	{/snippet}

	{#if step === 'email'}
		<form onsubmit={handleSubmit} class="space-y-4">
			{#if formError}
				<Alert color="red">
					{formError}
				</Alert>
			{/if}

			{#if currentEmail}
				<div>
					<Label class="mb-2 block text-gray-500 dark:text-gray-400">Текущая эл. почта</Label>
					<Input
						type="text"
						name="current_email"
						value={currentEmail}
						disabled
						autocomplete="email"
						class="ps-9"
					>
						{#snippet left()}
							<EnvelopeSolid class="h-5 w-5 text-gray-400" />
						{/snippet}
					</Input>
				</div>
			{/if}

			<div>
				<Label for="new_email" color={emailColor} class="mb-2 block">Новая эл. почта</Label>
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
					class="ps-9"
					color={emailColor}
					oninput={handleEmailInput}
				>
					{#snippet left()}
						<EnvelopeSolid class="h-5 w-5" />
					{/snippet}
				</Input>
				{#if emailError}
					<Helper color="red" class="mt-1">{emailError}</Helper>
				{:else}
					<Helper class="mt-1">
						{currentEmail
							? 'На новый адрес придёт код. Почта изменится только после подтверждения.'
							: 'На этот адрес придёт письмо с кодом подтверждения.'}
					</Helper>
				{/if}
			</div>

			<Button
				type="submit"
				color="primary"
				class="w-full"
				disabled={isLoading || !isValidEmail(normalizeEmail(newEmail))}
			>
				{#if isLoading}
					<span class="flex items-center gap-2">
						<Spinner size="4" class="fill-white" />
						Отправка кода…
					</span>
				{:else}
					{currentEmail ? 'Отправить код' : 'Добавить адрес'}
				{/if}
			</Button>
		</form>
	{:else}
		<div class="space-y-4">
			{#if formError}
				<Alert color="red">
					{formError}
				</Alert>
			{/if}

			<div>
				<Label class="mb-2 block text-gray-500 dark:text-gray-400">Новая эл. почта</Label>
				<Input type="text" value={normalizeEmail(newEmail)} disabled class="ps-9">
					{#snippet left()}
						<EnvelopeSolid class="h-5 w-5 text-gray-400" />
					{/snippet}
				</Input>
				<Helper class="mt-1">Код подтверждения отправлен на этот адрес.</Helper>
			</div>

			<div>
				<Label class="mb-2 block text-center">Код подтверждения</Label>
				<OtpInput
					bind:value={verificationCode}
					disabled={isVerifying || isRequestingVerification}
					hasError={Boolean(verificationCodeError)}
					onInput={() => {
						verificationCodeError = '';
						formError = '';
					}}
					onComplete={submitVerificationCode}
				/>
				{#if verificationCodeError}
					<Helper color="red" class="mt-1 block text-center">{verificationCodeError}</Helper>
				{:else}
					<Helper class="mt-1 block text-center">Введи 6 цифр из письма.</Helper>
				{/if}
			</div>

			<div class="flex flex-col space-y-2 pt-2">
				<Button
					color="primary"
					class="min-h-11 w-full font-medium"
					disabled={isVerifying || isRequestingVerification || verificationCode.length < 6}
					onclick={submitVerificationCode}
				>
					{#if isVerifying}
						<Spinner size="4" class="me-2 fill-white" />
						Проверяем…
					{:else}
						Подтвердить код
					{/if}
				</Button>

				<Button
					type="button"
					color="alternative"
					class="min-h-11 w-full font-medium"
					disabled={isVerifying || isRequestingVerification || cooldown.remaining > 0}
					onclick={sendOtp}
				>
					{#if isRequestingVerification}
						<Spinner size="4" class="me-2" />
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
</Modal>
