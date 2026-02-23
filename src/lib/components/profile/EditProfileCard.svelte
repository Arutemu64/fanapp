<script lang="ts">
	import { Card, Input, Label, Helper, Button } from 'flowbite-svelte';
	import { UserCircleSolid } from 'flowbite-svelte-icons';
	import { client } from '$lib/api';
	import { toastService } from '$lib/stores/toasts.svelte';
	import type { UserFullDTO } from '$lib/types/user';
	import type { components } from '$lib/api/v1';

	type UpdateUserRequest = components['schemas']['UpdateUserRequest'];

	interface Props {
		user: UserFullDTO;
		onUpdate?: () => void;
	}

	let { user, onUpdate }: Props = $props();

	// Form state - initialized from props, synced via effect

	let previousUsername = $derived(user.username);

	let username = $state('');
	let isLoading = $state(false);

	// Validation state
	let usernameError = $state('');

	// Validation patterns
	const USERNAME_PATTERN = /^[a-zA-Z0-9_]+$/;

	function validateUsername(value: string): string {
		if (value && !USERNAME_PATTERN.test(value)) {
			return 'Только латинские буквы, цифры и подчёркивание';
		}
		return '';
	}

	function handleUsernameInput(e: Event) {
		const target = e.target as HTMLInputElement;
		username = target.value;
		usernameError = validateUsername(username);
	}

	function hasChanges(): boolean {
		return username !== (user.username ?? '');
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

		const body: UpdateUserRequest = {};
		if (username !== user.username) body.username = username || null;

		const { data, error } = await client.PATCH('/users/me', {
			body
		});

		isLoading = false;

		if (error) {
			toastService.error(error);
			return;
		}

		toastService.add('Профиль обновлён', 'success');

		// Update local user state via callback
		if (onUpdate) {
			onUpdate();
		}
	}
</script>

<Card class="rounded-lg bg-white shadow dark:bg-gray-800">
	<div class="p-6">
		<div class="mb-4 flex items-center gap-2">
			<UserCircleSolid class="h-5 w-5 text-gray-500 dark:text-gray-400" />
			<h3 class="text-lg font-bold text-gray-900 dark:text-white">Редактирование профиля</h3>
		</div>

		<form onsubmit={handleSubmit} class="space-y-4">
			<div>
				<Label for="username" class="mb-2 block">Имя пользователя</Label>
				<Input
					id="username"
					type="text"
					placeholder={previousUsername ?? 'username'}
					bind:value={username}
					oninput={handleUsernameInput}
					color={usernameError ? 'red' : undefined}
				/>
				{#if usernameError}
					<Helper class="mt-1" color="red">{usernameError}</Helper>
				{:else}
					<Helper class="mt-1">Латинские буквы, цифры и подчёркивание</Helper>
				{/if}
			</div>

			<Button type="submit" color="primary" class="w-full" disabled={!isValid() || isLoading}>
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
					Сохранить
				{/if}
			</Button>
		</form>
	</div>
</Card>
