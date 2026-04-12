<script lang="ts">
	import { Modal, Input, Label, Button, Spinner } from 'flowbite-svelte';
	import { LockSolid, EyeOutline, EyeSlashOutline } from 'flowbite-svelte-icons';
	import { client } from '$lib/api';
	import { getToastService } from '$lib/services/toasts.svelte';
	import type { components } from '$lib/api/v1';

	type ChangePasswordInput = components['schemas']['ChangePasswordInput'];

	interface Props {
		open: boolean;
		hasPassword?: boolean;
		onSuccess?: () => void;
	}

	let { open = $bindable(false), hasPassword = true, onSuccess }: Props = $props();

	let oldPassword = $state('');
	const toastService = getToastService();
	let newPassword = $state('');
	let isLoading = $state(false);
	let showOldPassword = $state(false);
	let showNewPassword = $state(false);

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

		const body: ChangePasswordInput = {
			old_password: oldPassword || null,
			new_password: newPassword
		};

		const { error } = await client.POST('/me/password', {
			body
		});

		isLoading = false;

		if (error) {
			toastService.error(error);
			return;
		}

		toastService.add(
			hasPassword ? 'Пароль успешно изменён' : 'Пароль успешно установлен',
			'success'
		);
		oldPassword = '';
		newPassword = '';
		open = false; // close modal
		if (onSuccess) onSuccess();
	}
</script>

<Modal bind:open size="sm">
	{#snippet header()}
		<div class="flex items-center gap-2">
			<LockSolid class="h-5 w-5 text-gray-500 dark:text-gray-400" />
			<h3 class="text-lg font-bold text-gray-900 dark:text-white">
				{hasPassword ? 'Изменение пароля' : 'Установка пароля'}
			</h3>
		</div>
	{/snippet}

	<form onsubmit={handleSubmit} class="space-y-4">
		{#if hasPassword}
			<div>
				<Label for="old_password" class="mb-2 block">Старый пароль</Label>
				<Input
					id="old_password"
					name="current_password"
					type={showOldPassword ? 'text' : 'password'}
					placeholder="••••••••"
					autocomplete="current-password"
					bind:value={oldPassword}
					class="ps-9"
				>
					{#snippet left()}
						<LockSolid class="h-5 w-5" />
					{/snippet}
					{#snippet right()}
						<button
							type="button"
							class="pointer-events-auto"
							onclick={() => (showOldPassword = !showOldPassword)}
							aria-label={showOldPassword ? 'Скрыть старый пароль' : 'Показать старый пароль'}
							aria-pressed={showOldPassword}
						>
							{#if showOldPassword}
								<EyeOutline class="h-5 w-5 text-gray-500 dark:text-gray-400" />
							{:else}
								<EyeSlashOutline class="h-5 w-5 text-gray-500 dark:text-gray-400" />
							{/if}
						</button>
					{/snippet}
				</Input>
			</div>
		{/if}
		<div>
			<Label for="new_password" class="mb-2 block">Новый пароль</Label>
			<Input
				id="new_password"
				name="new_password"
				type={showNewPassword ? 'text' : 'password'}
				placeholder="••••••••"
				autocomplete="new-password"
				bind:value={newPassword}
				class="ps-9"
			>
				{#snippet left()}
					<LockSolid class="h-5 w-5" />
				{/snippet}
				{#snippet right()}
					<button
						type="button"
						class="pointer-events-auto"
						onclick={() => (showNewPassword = !showNewPassword)}
						aria-label={showNewPassword ? 'Скрыть новый пароль' : 'Показать новый пароль'}
						aria-pressed={showNewPassword}
					>
						{#if showNewPassword}
							<EyeOutline class="h-5 w-5 text-gray-500 dark:text-gray-400" />
						{:else}
							<EyeSlashOutline class="h-5 w-5 text-gray-500 dark:text-gray-400" />
						{/if}
					</button>
				{/snippet}
			</Input>
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
					Сохранение…
				</span>
			{:else}
				{hasPassword ? 'Сменить пароль' : 'Установить пароль'}
			{/if}
		</Button>
	</form>
</Modal>
