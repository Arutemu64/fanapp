<script lang="ts">
	import { Card, Input, Label, Button } from 'flowbite-svelte';
	import { LockSolid } from 'flowbite-svelte-icons';
	import { client } from '$lib/api';
	import { toastService } from '$lib/stores/toasts.svelte';
	import type { components } from '$lib/api/v1';

	type ChangePasswordCommand = components['schemas']['ChangePasswordCommand'];

	let oldPassword = $state('');
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
	}
</script>

<Card class="rounded-lg bg-white shadow dark:bg-gray-800">
	<div class="p-6">
		<div class="mb-4 flex items-center gap-2">
			<LockSolid class="h-5 w-5 text-gray-500 dark:text-gray-400" />
			<h3 class="text-lg font-bold text-gray-900 dark:text-white">Изменение пароля</h3>
		</div>

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
						<svg class="h-4 w-4 animate-spin" viewBox="0 0 24 24">
							<circle
								class="opacity-25"
								cx="12"
								cy="12"
								r="10"
								stroke="currentColor"
								stroke-width="4"
								fill="none"
							/>
							<path
								class="opacity-75"
								fill="currentColor"
								d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
							/>
						</svg>
						Сохранение...
					</span>
				{:else}
					Сменить пароль
				{/if}
			</Button>
		</form>
	</div>
</Card>
