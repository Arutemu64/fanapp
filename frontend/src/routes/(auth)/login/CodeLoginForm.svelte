<script lang="ts">
	import { client } from '$lib/api';
	import { isValidEmail, normalizeEmail } from '$lib/utils/validation';
	import { getToastService } from '$lib/services/toasts.svelte';
	import { Button, Helper, Input, Label, Spinner } from 'flowbite-svelte';
	import { EnvelopeSolid } from 'flowbite-svelte-icons';
	import { tick } from 'svelte';
	import VerifyCodeForm from './VerifyCodeForm.svelte';

	let {
		email = $bindable(''),
		isBusy = $bindable(false),
		showPasswordForm = $bindable(false),
		isWaitingForCode = $bindable(false)
	} = $props<{
		email: string;
		isBusy?: boolean;
		showPasswordForm?: boolean;
		isWaitingForCode?: boolean;
	}>();

	type ActiveAction = 'code-request' | null;

	let codeSentTo = $state('');
	let activeAction = $state<ActiveAction>(null);
	let emailError = $state('');

	const toastService = getToastService();

	$effect(() => {
		isBusy = activeAction !== null;
	});

	$effect(() => {
		isWaitingForCode = !!codeSentTo;
	});

	let normalizedEmail = $derived(normalizeEmail(email));
	let isEmailValid = $derived(email ? isValidEmail(normalizedEmail) : null);
	let emailColor = $derived.by((): 'green' | 'red' | undefined => {
		if (emailError) return 'red';
		if (!email) return undefined;
		return isEmailValid ? 'green' : 'red';
	});

	function resetEmailFeedback() {
		emailError = '';
		codeSentTo = '';
	}

	function validateEmailCodeRequestForm(): boolean {
		emailError = '';

		if (!normalizedEmail) {
			emailError = 'Введи адрес эл. почты';
			return false;
		}

		if (!isValidEmail(normalizedEmail)) {
			emailError = 'Введи адрес в формате name@example.com';
			return false;
		}

		return true;
	}

	async function handleLoginCodeRequest() {
		if (activeAction !== null) {
			return;
		}

		if (!validateEmailCodeRequestForm()) {
			return;
		}

		const trimmedEmail = normalizedEmail;

		activeAction = 'code-request';
		codeSentTo = '';

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
			await tick();
			document.getElementById('code-0')?.focus();
		} catch (error) {
			toastService.error(error);
		} finally {
			activeAction = null;
		}
	}

	function handleSubmit(event: SubmitEvent) {
		event.preventDefault();
		if (activeAction !== null) return;
		void handleLoginCodeRequest();
	}
</script>

{#if codeSentTo}
	<VerifyCodeForm email={codeSentTo} bind:isBusy onBack={() => (codeSentTo = '')} />
{:else}
	<form onsubmit={handleSubmit} class="space-y-4">
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
			{:else}
				<Helper color="gray" class="mt-1"
					>Если у вас ещё нет аккаунта, он будет создан автоматически.</Helper
				>
			{/if}
		</div>

		<div class="flex flex-col space-y-2">
			<Button
				type="submit"
				color="primary"
				class="min-h-11 w-full rounded-xl font-medium"
				disabled={isBusy && activeAction === null}
			>
				{#if activeAction === 'code-request'}
					<Spinner size="4" class="mr-2" color="primary" />
					Отправляем…
				{:else}
					Продолжить
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
{/if}
