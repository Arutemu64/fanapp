<script lang="ts">
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { client } from '$lib/api';
	import { getApiErrorDetail } from '$lib/api/errors';
	import { getEventsClient } from '$lib/services/events.svelte';
	import { getToastService } from '$lib/services/toasts.svelte';
	import { Alert, Button, Helper, Label, Spinner } from 'flowbite-svelte';
	import { onMount } from 'svelte';
	import OtpInput from '$lib/components/OtpInput.svelte';

	let {
		email,
		isBusy = $bindable(false),
		onBack
	} = $props<{
		email: string;
		isBusy?: boolean;
		onBack?: () => void;
	}>();

	type ActiveAction = 'code-request' | 'code-login' | null;

	let loginCode = $state('');
	let activeAction = $state<ActiveAction>(null);
	let loginCodeError = $state('');
	let formError = $state('');

	let resendCooldown = $state(60);
	let resendInterval: ReturnType<typeof setInterval>;

	const eventsClient = getEventsClient();
	const toastService = getToastService();

	// Update parent isBusy state
	$effect(() => {
		isBusy = activeAction !== null;
	});

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

	onMount(() => {
		startCooldown();
		return () => clearInterval(resendInterval);
	});

	function resetLoginCodeFeedback() {
		loginCodeError = '';
		formError = '';
	}

	async function finishLogin(successMessage: string) {
		toastService.add(successMessage, 'success');
		await goto(resolve('/'), { invalidateAll: true });
		eventsClient?.restart();
	}

	async function submitLoginCode() {
		if (activeAction !== null) {
			return;
		}

		if (loginCode.length !== 6) {
			loginCodeError = 'Введи код из письма';
			return;
		}

		if (!/^\d{6}$/.test(loginCode)) {
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

			await finishLogin('Вход выполнен');
		} catch (err) {
			console.error('Login code submit exception:', err);
			formError = 'Произошла непредвиденная ошибка';
		} finally {
			activeAction = null;
		}
	}

	async function handleLoginCodeRequest() {
		activeAction = 'code-request';
		loginCodeError = '';
		formError = '';

		try {
			const { error, response } = await client.POST('/auth/request-login-code', {
				body: { email }
			});

			if (error || !response.ok) {
				console.error('Login code request error:', error);
				formError = getApiErrorDetail(error) ?? 'Не удалось отправить код повторно';
				return;
			}

			loginCode = '';
			toastService.add('Код отправлен повторно', 'success');
			startCooldown();
		} catch (err) {
			console.error('Login code request exception:', err);
			formError = 'Произошла ошибка при повторной отправке кода';
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

<form onsubmit={handleSubmit} class="space-y-4">
	{#if formError}
		<Alert color="red" class="rounded-xl text-sm">
			{formError}
		</Alert>
	{/if}

	<Alert color="green">
		Код отправлен на <span class="font-medium">{email}</span>.
	</Alert>

	<div>
		<Label class="mb-2 block text-center">Код подтверждения</Label>
		<OtpInput
			bind:value={loginCode}
			disabled={isBusy && activeAction === null}
			hasError={Boolean(loginCodeError)}
			onInput={resetLoginCodeFeedback}
			onComplete={submitLoginCode}
		/>
		{#if loginCodeError}
			<Helper color="red" class="mt-1 block text-center">{loginCodeError}</Helper>
		{:else}
			<Helper class="mt-1 block text-center">Введи 6 цифр из письма.</Helper>
		{/if}
	</div>

	<Button
		type="submit"
		color="primary"
		class="min-h-11 w-full rounded-xl font-medium"
		disabled={(isBusy && activeAction === null) || loginCode.length < 6}
	>
		{#if activeAction === 'code-login'}
			<Spinner size="4" class="mr-2" color="primary" />
			Проверяем…
		{:else}
			Войти по коду
		{/if}
	</Button>

	<div class="flex flex-col space-y-2">
		<Button
			type="button"
			color="alternative"
			class="min-h-11 w-full rounded-xl font-medium"
			disabled={(isBusy && activeAction === null) || resendCooldown > 0}
			onclick={() => void handleLoginCodeRequest()}
		>
			{#if activeAction === 'code-request'}
				<Spinner size="4" class="mr-2" color="primary" />
				Отправляем…
			{:else if resendCooldown > 0}
				Отправить код ещё раз ({resendCooldown} сек.)
			{:else}
				Отправить код ещё раз
			{/if}
		</Button>

		<Button
			type="button"
			color="light"
			class="min-h-11 w-full rounded-xl font-medium"
			disabled={isBusy && activeAction === null}
			onclick={() => onBack?.()}
		>
			Назад
		</Button>
	</div>
</form>
