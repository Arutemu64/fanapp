<script lang="ts">
	import { untrack } from 'svelte';
	import { Modal, Input, Label, Helper, Button, Spinner, Alert } from 'flowbite-svelte';
	import { UserCircleSolid, UserSolid } from 'flowbite-svelte-icons';
	import { createApiClient } from '$lib/api';
	const client = createApiClient();
	import { getApiErrorDetail } from '$lib/api/errors';
	import { getToastService } from '$lib/services/toasts.svelte';
	import type { CurrentUserDTO } from '$lib/types/user';
	import type { components } from '$lib/api/v1';

	type UpdateCurrentUserInput = components['schemas']['UpdateCurrentUserInput'];

	interface Props {
		user: CurrentUserDTO;
		open: boolean;
		onUpdate?: () => void;
	}

	let { user, open = $bindable(false), onUpdate }: Props = $props();
	const toastService = getToastService();

	let username = $state('');
	let isLoading = $state(false);

	// Validation & form state
	let usernameError = $state('');
	let formError = $state('');

	$effect(() => {
		if (open) {
			untrack(() => {
				username = user.username ?? '';
				usernameError = '';
				formError = '';
			});
		}
	});

	// Validation patterns (must match backend)
	const USERNAME_MIN_LENGTH = 3;
	const USERNAME_MAX_LENGTH = 25;
	const USERNAME_PATTERN = /^[A-Za-zА-Яа-яЁё][A-Za-zА-Яа-яЁё0-9_]{2,24}$/;

	function validateUsername(value: string): string {
		if (!value) {
			return 'Псевдоним обязателен';
		}

		if (value.length < USERNAME_MIN_LENGTH) {
			return `Минимум ${USERNAME_MIN_LENGTH} символа`;
		}

		if (value.length > USERNAME_MAX_LENGTH) {
			return `Максимум ${USERNAME_MAX_LENGTH} символов`;
		}

		if (!USERNAME_PATTERN.test(value)) {
			return 'Начинается с буквы; далее буквы, цифры и подчёркивание';
		}

		return '';
	}

	function handleUsernameInput(e: Event) {
		const target = e.target as HTMLInputElement;
		username = target.value;
		usernameError = validateUsername(username);
		formError = '';
	}

	function hasChanges(): boolean {
		return !!username && username !== user.username;
	}

	function isValid(): boolean {
		return !usernameError;
	}

	async function handleSubmit(e: Event) {
		e.preventDefault();

		// Validate all fields
		usernameError = validateUsername(username);

		if (!isValid()) {
			return;
		}

		if (!hasChanges()) {
			// Nothing to save — close silently instead of nagging with a toast.
			open = false;
			return;
		}

		isLoading = true;

		const body: UpdateCurrentUserInput = {};
		if (username && username !== user.username) body.username = username;

		const { error, response } = await client.PATCH('/me/', {
			body
		});

		isLoading = false;

		if (error || !response.ok) {
			formError = getApiErrorDetail(error) ?? 'Не удалось обновить профиль';
			return;
		}

		toastService.add('Профиль обновлён', 'success');
		open = false; // close modal

		// reset form
		username = '';

		// Update local user state via callback
		if (onUpdate) {
			onUpdate();
		}
	}
</script>

<Modal bind:open size="sm">
	{#snippet header()}
		<div class="flex items-center gap-2">
			<UserCircleSolid class="h-5 w-5 text-gray-500 dark:text-gray-400" />
			<h3 class="text-lg font-bold text-gray-900 dark:text-white">Редактирование профиля</h3>
		</div>
	{/snippet}

	<form onsubmit={handleSubmit} class="space-y-4">
		{#if formError}
			<Alert color="red" class="rounded-xl text-sm">
				{formError}
			</Alert>
		{/if}

		<div>
			<Label for="username" class="mb-2 block">Псевдоним</Label>
			<Input
				id="username"
				name="username"
				type="text"
				placeholder="Псевдоним"
				autocomplete="nickname"
				autocapitalize="off"
				spellcheck={false}
				bind:value={username}
				oninput={handleUsernameInput}
				color={usernameError ? 'red' : undefined}
				class="ps-9"
			>
				{#snippet left()}
					<UserSolid class="h-5 w-5" />
				{/snippet}
			</Input>
			{#if usernameError}
				<Helper class="mt-1" color="red">{usernameError}</Helper>
			{/if}
			<ul class="mt-2 space-y-1 text-xs text-gray-500 dark:text-gray-400">
				<li>от 3 до 25 символов</li>
				<li>начинается с буквы (латиница или кириллица)</li>
				<li>далее буквы, цифры и подчёркивание</li>
			</ul>
		</div>

		<Button type="submit" color="primary" class="w-full" disabled={!isValid() || isLoading}>
			{#if isLoading}
				<span class="flex items-center gap-2">
					<Spinner size="4" />
					Сохранение…
				</span>
			{:else}
				Сохранить
			{/if}
		</Button>
	</form>
</Modal>
