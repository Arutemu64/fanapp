<script lang="ts">
	import type { components } from '$lib/api/schema';

	import { createApiClient } from '$lib/api';
	import { getApiErrorDetail } from '$lib/api/errors';
	import PasswordInput from '$lib/components/PasswordInput.svelte';
	import { getToastService } from '$lib/services/toasts.svelte';
	import { Alert, Button, Label, Modal, Spinner } from 'flowbite-svelte';
	import { CheckCircleSolid, CloseCircleOutline, LockSolid } from 'flowbite-svelte-icons';

	const client = createApiClient();

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
	let formError = $state('');

	// Password rules mirror the backend PASSWORD_FIELD (10-128 chars, no complexity rule).
	const MIN_PASSWORD_LENGTH = 10;
	const MAX_PASSWORD_LENGTH = 128;

	let hasMinLength = $derived(newPassword.length >= MIN_PASSWORD_LENGTH);
	let withinMaxLength = $derived(newPassword.length <= MAX_PASSWORD_LENGTH);
	let isValid = $derived(hasMinLength && withinMaxLength);

	$effect(() => {
		if (open) {
			oldPassword = '';
			newPassword = '';
			formError = '';
		}
	});

	async function handleSubmit(e: Event) {
		e.preventDefault();

		if (!isValid) {
			formError = `Новый пароль должен быть от ${MIN_PASSWORD_LENGTH} до ${MAX_PASSWORD_LENGTH} символов`;
			return;
		}

		isLoading = true;

		const body: ChangePasswordInput = {
			old_password: oldPassword || null,
			new_password: newPassword
		};

		const { error, response } = await client.POST('/me/password', {
			body
		});

		isLoading = false;

		if (error || !response.ok) {
			formError = getApiErrorDetail(error) ?? 'Не удалось сменить пароль';
			return;
		}

		toastService.add(
			hasPassword ? 'Пароль успешно изменён' : 'Пароль успешно установлен',
			'success'
		);
		oldPassword = '';
		newPassword = '';
		open = false;
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
		{#if formError}
			<Alert role="alert" color="red">
				{formError}
			</Alert>
		{/if}

		{#if hasPassword}
			<div>
				<Label for="old_password" class="mb-2 block">Старый пароль</Label>
				<PasswordInput
					id="old_password"
					name="current_password"
					autocomplete="current-password"
					revealLabel="старый пароль"
					bind:value={oldPassword}
					oninput={() => (formError = '')}
				/>
			</div>
		{/if}
		<div>
			<Label for="new_password" class="mb-2 block">Новый пароль</Label>
			<PasswordInput
				id="new_password"
				name="new_password"
				autocomplete="new-password"
				revealLabel="новый пароль"
				maxlength={MAX_PASSWORD_LENGTH}
				bind:value={newPassword}
				oninput={() => (formError = '')}
			/>

			<!-- Live password requirements; reflects the backend PASSWORD_FIELD rules. -->
			<ul class="mt-2 space-y-1">
				<li
					class="flex items-center gap-2 text-sm {hasMinLength
						? 'text-green-600 dark:text-green-400'
						: 'text-gray-500 dark:text-gray-400'}"
				>
					{#if hasMinLength}
						<CheckCircleSolid class="h-4 w-4 shrink-0" />
					{:else}
						<CloseCircleOutline class="h-4 w-4 shrink-0" />
					{/if}
					Минимум {MIN_PASSWORD_LENGTH} символов
				</li>
			</ul>
		</div>

		<Button type="submit" color="primary" class="w-full" disabled={isLoading || !isValid}>
			{#if isLoading}
				<span class="flex items-center gap-2">
					<Spinner size="4" class="fill-white" />
					Сохранение…
				</span>
			{:else}
				{hasPassword ? 'Сменить пароль' : 'Установить пароль'}
			{/if}
		</Button>
	</form>
</Modal>
