<script lang="ts">
	import { untrack } from 'svelte';
	import { Modal, Input, Label, Helper, Button, Spinner } from 'flowbite-svelte';
	import { UserCircleSolid, UserSolid, EditOutline } from 'flowbite-svelte-icons';
	import { client } from '$lib/api';
	import { getToastService } from '$lib/stores/toasts.svelte';
	import type { CurrentUserDTO } from '$lib/types/user';
	import type { components } from '$lib/api/v1';

	type UpdateCurrentUserCommand = components['schemas']['UpdateCurrentUserCommand'];

	interface Props {
		user: CurrentUserDTO;
		open: boolean;
		onUpdate?: () => void;
	}

	let { user, open = $bindable(false), onUpdate }: Props = $props();
	const toastService = getToastService();

	let username = $state('');
	let firstName = $state('');
	let isLoading = $state(false);

	// Validation state
	let usernameError = $state('');

	$effect(() => {
		if (open) {
			untrack(() => {
				username = user.username ?? '';
				firstName = user.first_name ?? '';
				usernameError = '';
			});
		}
	});

	// Validation patterns (must match backend)
	const USERNAME_MIN_LENGTH = 3;
	const USERNAME_MAX_LENGTH = 25;
	const USERNAME_PATTERN = /^[A-Za-zА-Яа-яЁё][A-Za-zА-Яа-яЁё0-9_]{2,24}$/;

	function validateUsername(value: string): string {
		if (!value) {
			return '';
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
	}

	function hasChanges(): boolean {
		return (
			(!!username && username !== user.username) || (!!firstName && firstName !== user.first_name)
		);
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
			toastService.add('Нет изменений для сохранения', 'info');
			return;
		}

		isLoading = true;

		const body: UpdateCurrentUserCommand = {};
		if (username && username !== user.username) body.username = username;
		if (firstName && firstName !== user.first_name) body.first_name = firstName;

		const { error } = await client.PATCH('/users/me', {
			body
		});

		isLoading = false;

		if (error) {
			toastService.error(error);
			return;
		}

		toastService.add('Профиль обновлён', 'success');
		open = false; // close modal

		// reset form
		username = '';
		firstName = '';

		// Update local user state via callback
		if (onUpdate) {
			onUpdate();
		}
	}
</script>

<Modal bind:open size="sm" outsideclose>
	{#snippet header()}
		<div class="flex items-center gap-2">
			<UserCircleSolid class="h-5 w-5 text-gray-500 dark:text-gray-400" />
			<h3 class="text-lg font-bold text-gray-900 dark:text-white">Редактирование профиля</h3>
		</div>
	{/snippet}

	<form onsubmit={handleSubmit} class="space-y-4">
		<div>
			<Label for="username" class="mb-2 block">Псевдоним</Label>
			<Input
				id="username"
				type="text"
				placeholder="Псевдоним"
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
			{:else}
				<Helper class="mt-1">3–25 символов, начинается с буквы; далее буквы (латиница/кириллица), цифры и подчёркивание</Helper>
			{/if}
		</div>

		<div>
			<Label for="firstName" class="mb-2 block">Настоящее имя</Label>
			<Input id="firstName" type="text" placeholder="Настоящее имя" bind:value={firstName} class="ps-9">
				{#snippet left()}
					<EditOutline class="h-5 w-5" />
				{/snippet}
			</Input>
		</div>

		<Button type="submit" color="primary" class="w-full" disabled={!isValid() || isLoading}>
			{#if isLoading}
				<span class="flex items-center gap-2">
					<Spinner size="4" />
					Сохранение...
				</span>
			{:else}
				Сохранить
			{/if}
		</Button>
	</form>
</Modal>
