<script lang="ts">
	import { Modal, Input, Label, Button, Spinner } from 'flowbite-svelte';
	import { LockSolid } from 'flowbite-svelte-icons';
	import { client } from '$lib/api';
	import { getToastService } from '$lib/stores/toasts.svelte';
	import type { components } from '$lib/api/v1';

	type ChangePasswordCommand = components['schemas']['ChangePasswordCommand'];

	interface Props {
		open: boolean;
	}

	let { open = $bindable(false) }: Props = $props();

	let oldPassword = $state('');
	const toastService = getToastService();
	let newPassword = $state('');
	let isLoading = $state(false);

	function isValid(): boolean {
		return newPassword.length >= 6;
	}

	async function handleSubmit(e: Event) {
		e.preventDefault();

		if (!isValid()) {
			toastService.add('Новый пароль должен быть не короче 6 символов', 'error');
			return;
		}

		isLoading = true;

		const body: ChangePasswordCommand = {
			old_password: oldPassword || null,
			new_password: newPassword
		};

		const { error } = await client.POST('/auth/change_password', {
			body
		});

		isLoading = false;

		if (error) {
			toastService.error(error);
			return;
		}

		toastService.add('Пароль успешно изменён', 'success');
		oldPassword = '';
		newPassword = '';
		open = false; // close modal
	}
</script>

<Modal bind:open size="sm" outsideclose>
	{#snippet header()}
		<div class="flex items-center gap-2">
			<LockSolid class="h-5 w-5 text-gray-500 dark:text-gray-400" />
			<h3 class="text-lg font-bold text-gray-900 dark:text-white">Изменение пароля</h3>
		</div>
	{/snippet}

	<form onsubmit={handleSubmit} class="space-y-4">
		<div>
			<Label for="old_password" class="mb-2 block">Старый пароль</Label>
			<Input id="old_password" type="password" placeholder="••••••••" bind:value={oldPassword} />
		</div>
		<div>
			<Label for="new_password" class="mb-2 block">Новый пароль</Label>
			<Input id="new_password" type="password" placeholder="••••••••" bind:value={newPassword} />
		</div>

		<Button
			type="submit"
			color="primary"
			class="w-full"
			disabled={isLoading || newPassword.length < 6}
		>
			{#if isLoading}
				<span class="flex items-center gap-2">
					<Spinner size="4" />
					Сохранение...
				</span>
			{:else}
				Сменить пароль
			{/if}
		</Button>
	</form>
</Modal>
