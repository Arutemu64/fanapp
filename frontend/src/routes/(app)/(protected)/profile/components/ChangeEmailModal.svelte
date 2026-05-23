<script lang="ts">
	import { Modal, Input, Label, Button, Spinner, Helper, Alert } from 'flowbite-svelte';
	import { EnvelopeSolid } from 'flowbite-svelte-icons';
	import { client } from '$lib/api';
	import { getApiErrorDetail } from '$lib/api/errors';
	import { getToastService } from '$lib/services/toasts.svelte';
	import type { components } from '$lib/api/v1';
	import { onDestroy, untrack } from 'svelte';
	import OtpInput from '$lib/components/OtpInput.svelte';

	type ChangeEmailInput = components['schemas']['ChangeEmailInput'];

	interface Props {
		open: boolean;
		currentEmail?: string | null;
		pendingEmail?: string | null;
		initialStep?: 'email' | 'verify';
		onSuccess?: () => void;
	}

	let {
		open = $bindable(false),
		currentEmail,
		pendingEmail,
		initialStep = 'email',
		onSuccess
	}: Props = $props();

	let hasExistingEmail = $derived(Boolean(currentEmail || pendingEmail));

	// State management
	let step = $state<'email' | 'verify'>('email');
	let newEmail = $state('');
	let emailError = $state('');
	let isLoading = $state(false);
	let isResumed = $state(false);

	let verificationCode = $state('');
	let verificationCodeError = $state('');
	let isVerifying = $state(false);
	let isRequestingVerification = $state(false);

	let resendCooldown = $state(0);
	let resendInterval: ReturnType<typeof setInterval>;

	const toastService = getToastService();
	let formError = $state('');

	// Computed value: where the code is sent
	let emailSentTo = $derived.by(() => {
		if (newEmail.trim()) {
			return newEmail.trim().toLowerCase();
		}
		return pendingEmail || currentEmail || '';
	});

	function isValidEmail(value: string): boolean {
		return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value.trim());
	}

	let emailColor = $derived.by((): 'green' | 'red' | undefined => {
		if (emailError) {
			return 'red';
		}

		if (!newEmail) {
			return undefined;
		}

		return isValidEmail(newEmail) ? 'green' : 'red';
	});

	function isValid(): boolean {
		return isValidEmail(newEmail);
	}

	function handleEmailInput() {
		emailError = '';
		formError = '';
	}

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

	// Trigger verification code email
	async function requestVerification() {
		if (isRequestingVerification) return;

		isRequestingVerification = true;
		verificationCodeError = '';
		formError = '';

		try {
			const { error, response } = await client.POST('/auth/request-email-code');

			if (error || !response.ok) {
				formError = getApiErrorDetail(error) ?? 'Не удалось запросить новый код подтверждения';
				return;
			}

			verificationCode = '';
			toastService.add('Код для подтверждения отправлен на почту', 'success');
			startCooldown();
			isResumed = false;
		} catch (err) {
			formError = 'Произошла непредвиденная ошибка';
		} finally {
			isRequestingVerification = false;
		}
	}

	// Submit entered verification code
	async function submitVerificationCode() {
		verificationCodeError = '';

		if (verificationCode.length !== 6) {
			verificationCodeError = 'Введи код из письма';
			return;
		}

		if (!/^\d{6}$/.test(verificationCode)) {
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
			open = false; // Close modal on success
			if (onSuccess) onSuccess();
		} catch (err) {
			formError = 'Произошла непредвиденная ошибка';
		} finally {
			isVerifying = false;
		}
	}

	// Step 1: Save new email address
	async function handleSubmit(e: Event) {
		e.preventDefault();
		emailError = '';

		const trimmedEmail = newEmail.trim().toLowerCase();

		if (!isValidEmail(trimmedEmail)) {
			emailError = 'Введи адрес в формате name@example.com';
			return;
		}

		isLoading = true;

		const body: ChangeEmailInput = {
			new_email: trimmedEmail
		};

		const { error, response } = await client.POST('/me/email', {
			body
		});

		isLoading = false;

		if (error) {
			if (response.status === 409) {
				emailError = getApiErrorDetail(error) ?? 'Этот адрес уже используется';
				return;
			}

			formError = getApiErrorDetail(error) ?? 'Не удалось сохранить адрес почты';
			return;
		}

		toastService.add('Новый адрес сохранён. Код подтверждения отправлен на почту.', 'success');

		// Transition to Step 2: Verification
		step = 'verify';
		startCooldown();
	}

	// Synchronize step when the modal is opened
	$effect(() => {
		if (open) {
			untrack(() => {
				step = initialStep;
				isResumed = initialStep === 'verify';
				// Reset inputs
				newEmail = '';
				emailError = '';
				verificationCode = '';
				verificationCodeError = '';
				formError = '';
			});
		} else {
			untrack(() => {
				// Clear interval on modal close to prevent memory leaks
				clearInterval(resendInterval);
				resendCooldown = 0;
			});
		}
	});

	onDestroy(() => {
		clearInterval(resendInterval);
	});
</script>

<Modal bind:open size="sm" outsideclose={step !== 'verify'}>
	{#snippet header()}
		<div class="flex items-center gap-2">
			<EnvelopeSolid class="h-5 w-5 text-gray-500 dark:text-gray-400" />
			<h3 class="text-lg font-bold text-gray-900 dark:text-white">
				{#if step === 'email'}
					{hasExistingEmail ? 'Изменить эл. почту' : 'Добавить эл. почту'}
				{:else}
					Подтверждение эл. почты
				{/if}
			</h3>
		</div>
	{/snippet}

	{#if step === 'email'}
		<!-- Step 1: Input Email Form -->
		<form onsubmit={handleSubmit} class="space-y-4">
			{#if formError}
				<Alert color="red" class="rounded-xl text-sm">
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
			{#if !currentEmail && pendingEmail}
				<div>
					<Label class="mb-2 block text-yellow-500 dark:text-yellow-400"
						>Адрес ожидает подтверждения</Label
					>
					<Input
						type="text"
						name="pending_email"
						value={pendingEmail}
						disabled
						autocomplete="email"
						class="ps-9"
					>
						{#snippet left()}
							<EnvelopeSolid class="h-5 w-5 text-yellow-500" />
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
						{hasExistingEmail
							? 'На новый адрес придёт письмо. Текущая почта останется активной до подтверждения.'
							: 'На этот адрес придёт письмо с кодом подтверждения.'}
					</Helper>
				{/if}
			</div>

			<Button type="submit" color="primary" class="w-full" disabled={isLoading || !isValid()}>
				{#if isLoading}
					<span class="flex items-center gap-2">
						<Spinner size="4" />
						Сохранение…
					</span>
				{:else}
					{hasExistingEmail ? 'Сохранить адрес' : 'Добавить адрес'}
				{/if}
			</Button>
		</form>
	{:else}
		<!-- Step 2: Verification Code Entry -->
		<div class="space-y-4">
			{#if formError}
				<Alert color="red" class="rounded-xl text-sm">
					{formError}
				</Alert>
			{/if}

			{#if isResumed}
				<Alert color="yellow" class="text-sm">
					Для подтверждения адреса <span class="font-medium break-all">{emailSentTo}</span> введите 6-значный
					код из письма. Если код устарел, вы можете запросить новый ниже.
				</Alert>
			{:else}
				<Alert color="blue" class="text-sm">
					Код подтверждения отправлен на <span class="font-medium break-all">{emailSentTo}</span>
				</Alert>
			{/if}

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
					class="min-h-11 w-full rounded-xl font-medium"
					disabled={isVerifying || isRequestingVerification || verificationCode.length < 6}
					onclick={submitVerificationCode}
				>
					{#if isVerifying}
						<Spinner size="4" class="me-2" />
						Проверяем…
					{:else}
						Подтвердить код
					{/if}
				</Button>

				<Button
					type="button"
					color="alternative"
					class="min-h-11 w-full rounded-xl font-medium"
					disabled={isVerifying || isRequestingVerification || resendCooldown > 0}
					onclick={requestVerification}
				>
					{#if isRequestingVerification}
						<Spinner size="4" class="me-2" />
						Отправляем…
					{:else if resendCooldown > 0}
						Отправить код ещё раз ({resendCooldown} сек.)
					{:else}
						Отправить код ещё раз
					{/if}
				</Button>
			</div>
		</div>
	{/if}
</Modal>
