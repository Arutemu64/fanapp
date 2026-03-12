<script lang="ts">
	import { Modal, Input, Label, Button, Spinner } from 'flowbite-svelte';
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
	const toastService = getToastService();
	let isLoading = $state(false);

	function isValid(): boolean {
		// Basic email validation
		return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(newEmail);
	}

	async function handleSubmit(e: Event) {
		e.preventDefault();

		if (!isValid()) {
			toastService.add('Пожалуйста, введите корректный email адрес', 'error');
			return;
		}

		isLoading = true;

		const body: ChangeEmailCommand = {
			new_email: newEmail
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
				? 'Email успешно изменён. Проверьте почту для подтверждения!'
				: 'Email успешно добавлен. Проверьте почту для подтверждения!',
			'success'
		);
		newEmail = '';
		open = false; // close modal
		if (onSuccess) onSuccess();
	}
</script>

<Modal bind:open size="sm" outsideclose>
	{#snippet header()}
		<div class="flex items-center gap-2">
			<EnvelopeSolid class="h-5 w-5 text-gray-500 dark:text-gray-400" />
			<h3 class="text-lg font-bold text-gray-900 dark:text-white">
				{currentEmail ? 'Изменение email' : 'Добавление email'}
			</h3>
		</div>
	{/snippet}

	<form onsubmit={handleSubmit} class="space-y-4">
		{#if currentEmail}
			<div>
				<Label class="mb-2 block">Текущий email</Label>
				<Input type="text" value={currentEmail} disabled class="ps-9">
					{#snippet left()}
						<EnvelopeSolid class="h-5 w-5" />
					{/snippet}
				</Input>
			</div>
		{/if}
		<div>
			<Label for="new_email" class="mb-2 block">Новый email</Label>
			<Input
				id="new_email"
				type="email"
				placeholder="example@example.com"
				bind:value={newEmail}
				class="ps-9"
			>
				{#snippet left()}
					<EnvelopeSolid class="h-5 w-5" />
				{/snippet}
			</Input>
		</div>

		<Button type="submit" color="primary" class="w-full" disabled={isLoading || !isValid()}>
			{#if isLoading}
				<span class="flex items-center gap-2">
					<Spinner size="4" />
					Сохранение...
				</span>
			{:else}
				{currentEmail ? 'Изменить email' : 'Добавить email'}
			{/if}
		</Button>
	</form>
</Modal>
