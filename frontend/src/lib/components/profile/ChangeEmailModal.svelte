<script lang="ts">
	import { Modal, Input, Label, Button, Spinner, Helper } from 'flowbite-svelte';
	import { EnvelopeSolid } from 'flowbite-svelte-icons';
	import { client } from '$lib/api';
	import { getToastService } from '$lib/stores/toasts.svelte';
	import type { components } from '$lib/api/v1';

	type ChangeEmailCommand = components['schemas']['ChangeEmailCommand'];

	interface Props {
		open: boolean;
		currentEmail?: string | null;
		onSuccess?: () => void;
	}

	let { open = $bindable(false), currentEmail, onSuccess }: Props = $props();

	let newEmail = $state('');
	let emailError = $state('');
	const toastService = getToastService();
	let isLoading = $state(false);

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
	}

	async function handleSubmit(e: Event) {
		e.preventDefault();
		emailError = '';

		const trimmedEmail = newEmail.trim().toLowerCase();

		if (!isValidEmail(trimmedEmail)) {
			emailError = 'Введите адрес в формате name@example.com';
			return;
		}

		isLoading = true;

		const body: ChangeEmailCommand = {
			new_email: trimmedEmail
		};

		const { error } = await client.POST('/me/email', {
			body
		});

		isLoading = false;

		if (error) {
			toastService.error(error);
			return;
		}

		toastService.add(
			currentEmail
				? 'Адрес обновлён. Подтвердите его по письму.'
				: 'Адрес добавлен. Подтвердите его по письму.',
			'success'
		);
		newEmail = '';
		emailError = '';
		open = false; // close modal
		if (onSuccess) onSuccess();
	}
</script>

<Modal bind:open size="sm" outsideclose>
	{#snippet header()}
		<div class="flex items-center gap-2">
			<EnvelopeSolid class="h-5 w-5 text-gray-500 dark:text-gray-400" />
			<h3 class="text-lg font-bold text-gray-900 dark:text-white">
				{currentEmail ? 'Изменить эл. почту' : 'Добавить эл. почту'}
			</h3>
		</div>
	{/snippet}

	<form onsubmit={handleSubmit} class="space-y-4">
		{#if currentEmail}
			<div>
				<Label class="mb-2 block">Текущая эл. почта</Label>
				<Input type="text" value={currentEmail} disabled class="ps-9">
					{#snippet left()}
						<EnvelopeSolid class="h-5 w-5" />
					{/snippet}
				</Input>
			</div>
		{/if}
		<div>
			<Label for="new_email" color={emailColor} class="mb-2 block">Новая эл. почта</Label>
			<Input
				id="new_email"
				type="email"
				placeholder="name@example.com"
				autocomplete="email"
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
				<Helper class="mt-1">На этот адрес придёт письмо для подтверждения.</Helper>
			{/if}
		</div>

		<Button type="submit" color="primary" class="w-full" disabled={isLoading || !isValid()}>
			{#if isLoading}
				<span class="flex items-center gap-2">
					<Spinner size="4" />
					Сохранение...
				</span>
			{:else}
				{currentEmail ? 'Сохранить адрес' : 'Добавить адрес'}
			{/if}
		</Button>
	</form>
</Modal>
