<script lang="ts">
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { client } from '$lib/api';
	import { getApiErrorDetail } from '$lib/api/errors';
	import { getEventsClient } from '$lib/services/events.svelte';
	import { getToastService } from '$lib/services/toasts.svelte';
	import { Alert, Button, Helper, Input, Label, Spinner } from 'flowbite-svelte';
	import { EnvelopeSolid } from 'flowbite-svelte-icons';

	let { email = $bindable(''), isBusy = $bindable(false) } = $props();

	type ActiveAction = 'code-request' | 'code-login' | null;

	let loginCode = $state('');
	let codeSentTo = $state('');
	let activeAction = $state<ActiveAction>(null);
	let emailError = $state('');
	let loginCodeError = $state('');

	const eventsClient = getEventsClient();
	const toastService = getToastService();

	// Update parent isBusy state based on local activeAction
	$effect(() => {
		isBusy = activeAction !== null;
	});

	function validateEmail(value: string): boolean {
		if (!value) return false;
		const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
		return emailRegex.test(value);
	}

	function getNormalizedEmail(): string {
		return email.trim().toLowerCase();
	}

	let normalizedEmail = $derived(getNormalizedEmail());
	let isEmailValid = $derived(email ? validateEmail(normalizedEmail) : null);
	let emailColor = $derived.by((): 'green' | 'red' | undefined => {
		if (emailError) return 'red';
		if (!email) return undefined;
		return isEmailValid ? 'green' : 'red';
	});

	function resetEmailFeedback() {
		emailError = '';
		loginCodeError = '';
		codeSentTo = '';
		loginCode = '';
	}

	function resetLoginCodeFeedback() {
		loginCodeError = '';
	}

	function validateEmailCodeRequestForm(): boolean {
		emailError = '';
		loginCodeError = '';

		if (!normalizedEmail) {
			emailError = 'Введи адрес эл. почты';
			return false;
		}

		if (!validateEmail(normalizedEmail)) {
			emailError = 'Введи адрес в формате name@example.com';
			return false;
		}

		return true;
	}

	function validateEmailCodeLoginForm(): boolean {
		if (!validateEmailCodeRequestForm()) {
			return false;
		}

		if (!loginCode.trim()) {
			loginCodeError = 'Введи код из письма';
			return false;
		}

		if (!/^\d{6}$/.test(loginCode.trim())) {
			loginCodeError = 'Код должен состоять из 6 цифр';
			return false;
		}

		return true;
	}

	async function finishLogin(successMessage: string) {
		toastService.add(successMessage, 'success');
		await goto(resolve('/'), { invalidateAll: true });
		eventsClient?.restart();
	}

	async function handleLoginCodeRequest() {
		if (!validateEmailCodeRequestForm()) {
			return;
		}

		const trimmedEmail = normalizedEmail;

		activeAction = 'code-request';
		codeSentTo = '';
		loginCodeError = '';

		try {
			const { error } = await client.POST('/auth/request-login-code', {
				body: { email: trimmedEmail }
			});

			if (error) {
				console.error('Login code request error:', error);
				toastService.error(error);
				return;
			}

			codeSentTo = trimmedEmail;
			loginCode = '';
		} catch (error) {
			toastService.error(error);
		} finally {
			activeAction = null;
		}
	}

	async function submitLoginCode() {
		if (!validateEmailCodeLoginForm()) {
			return;
		}

		activeAction = 'code-login';
		loginCodeError = '';

		try {
			const { error, response } = await client.POST('/auth/login-with-code', {
				body: {
					email: normalizedEmail,
					code: loginCode.trim()
				}
			});

			if (error) {
				if (response.status === 400) {
					loginCodeError = getApiErrorDetail(error) ?? 'Неверный или устаревший код';
					return;
				}

				toastService.error(error);
				return;
			}

			await finishLogin('Вход выполнен');
		} catch (error) {
			toastService.error(error);
		} finally {
			activeAction = null;
		}
	}

	function handleCodeRequestSubmit(event: SubmitEvent) {
		event.preventDefault();

		if (isBusy && activeAction === null) {
			return; // Busy from the other tab
		}

		const submitterAction =
			event.submitter instanceof HTMLButtonElement ? event.submitter.dataset.action : null;

		if (submitterAction === 'login' || (!submitterAction && codeSentTo)) {
			void submitLoginCode();
			return;
		}

		void handleLoginCodeRequest();
	}
</script>

<form onsubmit={handleCodeRequestSubmit} class="space-y-3">
	<div>
		<Label for="code-email" color={emailColor} class="mb-2">Эл. почта</Label>
		<Input
			id="code-email"
			name="email"
			type="email"
			bind:value={email}
			placeholder="name@example.com"
			autocomplete="email"
			inputmode="email"
			autocapitalize="off"
			spellcheck={false}
			required
			disabled={isBusy && activeAction === null}
			class="ps-9"
			color={emailColor}
			oninput={resetEmailFeedback}
		>
			{#snippet left()}
				<EnvelopeSolid class="h-5 w-5" />
			{/snippet}
		</Input>
		{#if emailError}
			<Helper color="red" class="mt-1">{emailError}</Helper>
		{:else if email && isEmailValid === false}
			<Helper color="red" class="mt-1">Введи адрес в формате name@example.com</Helper>
		{/if}
	</div>

	{#if codeSentTo}
		<Alert color="green">
			Код отправлен на <span class="font-medium">{codeSentTo}</span>. Не забудьте проверить папку
			"Спам"
		</Alert>
	{/if}

	{#if codeSentTo}
		<div>
			<Label for="login-code" class="mb-2">Код из письма</Label>
			<Input
				id="login-code"
				name="code"
				type="text"
				bind:value={loginCode}
				placeholder="******"
				autocomplete="one-time-code"
				inputmode="numeric"
				pattern="[0-9]*"
				maxlength={6}
				disabled={isBusy && activeAction === null}
				class="text-center text-lg tracking-widest"
				color={loginCodeError ? 'red' : undefined}
				oninput={() => {
					loginCode = loginCode.replace(/\D/g, '').slice(0, 6);
					resetLoginCodeFeedback();
				}}
			/>
			{#if loginCodeError}
				<Helper color="red" class="mt-1">{loginCodeError}</Helper>
			{:else}
				<Helper class="mt-1">Введи 6 цифр из письма.</Helper>
			{/if}
		</div>
	{/if}

	{#if codeSentTo}
		<Button
			type="submit"
			data-action="login"
			color="primary"
			autofocus
			class="min-h-11 w-full rounded-xl font-medium"
			disabled={isBusy && activeAction === null}
		>
			{#if activeAction === 'code-login'}
				<Spinner size="4" class="mr-2" color="primary" />
				Проверяем…
			{:else}
				Войти по коду
			{/if}
		</Button>

		<Button
			type="button"
			color="alternative"
			class="min-h-11 w-full rounded-xl font-medium"
			disabled={isBusy && activeAction === null}
			onclick={() => void handleLoginCodeRequest()}
		>
			{#if activeAction === 'code-request'}
				<Spinner size="4" class="mr-2" color="primary" />
				Отправляем…
			{:else}
				Отправить код ещё раз
			{/if}
		</Button>
	{:else}
		<Button
			type="submit"
			data-action="request"
			color="primary"
			class="min-h-11 w-full rounded-xl font-medium"
			disabled={isBusy && activeAction === null}
		>
			{#if activeAction === 'code-request'}
				<Spinner size="4" class="mr-2" color="primary" />
				Отправляем…
			{:else}
				Получить код
			{/if}
		</Button>
	{/if}
</form>
