<script lang="ts">
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { client } from '$lib/api';
	import { getApiErrorDetail } from '$lib/api/errors';
	import { getEventsClient } from '$lib/services/events.svelte';
	import { getToastService } from '$lib/services/toasts.svelte';
	import { Alert, Button, Helper, Input, Label, Spinner } from 'flowbite-svelte';
	import { onMount } from 'svelte';

	let {
		email,
		isBusy = $bindable(false),
		showPasswordForm = $bindable(false)
	} = $props<{
		email: string;
		isBusy?: boolean;
		showPasswordForm?: boolean;
	}>();

	type ActiveAction = 'code-request' | 'code-login' | null;

	let codeDigits = $state(['', '', '', '', '', '']);
	let activeAction = $state<ActiveAction>(null);
	let loginCodeError = $state('');

	let resendCooldown = $state(60);
	let resendInterval: ReturnType<typeof setInterval>;

	const eventsClient = getEventsClient();
	const toastService = getToastService();

	let loginCode = $derived(codeDigits.join(''));

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

		try {
			const { error, response } = await client.POST('/auth/login-with-code', {
				body: { email, code: loginCode }
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

	async function handleLoginCodeRequest() {
		activeAction = 'code-request';
		loginCodeError = '';

		try {
			const { error } = await client.POST('/auth/request-login-code', {
				body: { email }
			});

			if (error) {
				console.error('Login code request error:', error);
				toastService.error(error);
				return;
			}

			codeDigits = ['', '', '', '', '', ''];
			toastService.add('Код отправлен повторно', 'success');
			startCooldown();
			setTimeout(() => document.getElementById('code-0')?.focus(), 50);
		} catch (error) {
			toastService.error(error);
		} finally {
			activeAction = null;
		}
	}

	function handlePinKeyup(event: KeyboardEvent, index: number) {
		const target = event.target as HTMLInputElement;

		if (event.key === 'Backspace' && target.value.length === 0 && index > 0) {
			document.getElementById(`code-${index - 1}`)?.focus();
			return;
		}

		if (target.value.length > 0 && index < 5) {
			document.getElementById(`code-${index + 1}`)?.focus();
		}
	}

	function handlePinPaste(event: ClipboardEvent) {
		event.preventDefault();
		// @ts-expect-error - clipboardData is not standard on Window but exists in IE/older Edge
		const windowClipboard = window.clipboardData;
		const pasteData =
			event.clipboardData?.getData('text') || windowClipboard?.getData('text') || '';
		const digits = pasteData.replace(/\D/g, ''); // Only take numbers

		if (!digits) return;

		for (let i = 0; i < 6; i++) {
			if (digits[i]) {
				codeDigits[i] = digits[i];
			}
		}

		const nextEmptyIndex = codeDigits.findIndex((d) => d === '');
		if (nextEmptyIndex !== -1) {
			document.getElementById(`code-${nextEmptyIndex}`)?.focus();
		} else {
			document.getElementById(`code-5`)?.focus();
			if (loginCode.length === 6) {
				void submitLoginCode();
			}
		}

		resetLoginCodeFeedback();
	}

	function handleSubmit(event: SubmitEvent) {
		event.preventDefault();
		if (activeAction !== null) return;
		void submitLoginCode();
	}
</script>

<form onsubmit={handleSubmit} class="space-y-4">
	<Alert color="green">
		Код отправлен на <span class="font-medium">{email}</span>.
	</Alert>

	<div>
		<Label class="mb-2">Код из письма</Label>
		<div class="flex justify-between space-x-2 rtl:space-x-reverse">
			{#each [0, 1, 2, 3, 4, 5] as i (i)}
				<div>
					<label for={`code-${i}`} class="sr-only">Code digit {i + 1}</label>
					<Input
						type="text"
						inputmode="numeric"
						autocomplete={i === 0 ? 'one-time-code' : 'off'}
						maxlength={1}
						id={`code-${i}`}
						bind:value={codeDigits[i]}
						onkeyup={(e) => handlePinKeyup(e, i)}
						onpaste={i === 0 ? handlePinPaste : undefined}
						oninput={() => {
							codeDigits[i] = (codeDigits[i] || '').replace(/\D/g, '');
							resetLoginCodeFeedback();
							if (i === 5 && codeDigits[5] !== '' && loginCode.length === 6) {
								void submitLoginCode();
							}
						}}
						disabled={isBusy && activeAction === null}
						color={loginCodeError ? 'red' : undefined}
						class="block h-11 w-11 py-3 text-center text-lg font-extrabold sm:h-12 sm:w-12 sm:text-xl"
						required
					/>
				</div>
			{/each}
		</div>
		{#if loginCodeError}
			<Helper color="red" class="mt-1">{loginCodeError}</Helper>
		{:else}
			<Helper class="mt-1">Введи 6 цифр из письма.</Helper>
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
			onclick={() => (showPasswordForm = true)}
		>
			Войти с паролем
		</Button>
	</div>
</form>
