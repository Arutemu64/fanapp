<script lang="ts">
	import type { components } from '$lib/api/schema';
	import type { CurrentUserDTO } from '$lib/types/user';

	import { createApiClient } from '$lib/api';
	import { getApiErrorDetail } from '$lib/api/errors';
	import * as Alert from '$lib/components/ui/alert';
	import { Button } from '$lib/components/ui/button';
	import * as Dialog from '$lib/components/ui/dialog';
	import * as Field from '$lib/components/ui/field';
	import { Input } from '$lib/components/ui/input';
	import { Spinner } from '$lib/components/ui/spinner';
	import { getToastService } from '$lib/services/toasts.svelte';
	import { User } from '@lucide/svelte';
	import { untrack } from 'svelte';

	const client = createApiClient();

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
			return 'Введи имя пользователя';
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
		open = false;
		username = '';

		if (onUpdate) {
			onUpdate();
		}
	}
</script>

<Dialog.Root bind:open>
	<Dialog.Content class="sm:max-w-md">
		<Dialog.Header>
			<Dialog.Title class="flex items-center gap-2">
				<User class="size-5 text-muted-foreground" />
				Редактирование профиля
			</Dialog.Title>
			<Dialog.Description class="sr-only">Измени имя пользователя.</Dialog.Description>
		</Dialog.Header>

		<form onsubmit={handleSubmit} class="flex flex-col gap-4">
			{#if formError}
				<Alert.Root variant="destructive">
					<Alert.Description>{formError}</Alert.Description>
				</Alert.Root>
			{/if}

			<Field.Field data-invalid={usernameError ? true : undefined}>
				<Field.FieldLabel for="username">Имя пользователя</Field.FieldLabel>
				<div class="relative flex items-center">
					<User class="pointer-events-none absolute left-3 size-4 text-muted-foreground" />
					<Input
						id="username"
						name="username"
						type="text"
						placeholder="Например, sakura_chan"
						autocomplete="nickname"
						autocapitalize="off"
						spellcheck={false}
						bind:value={username}
						oninput={handleUsernameInput}
						aria-invalid={usernameError ? true : undefined}
						class="pl-9"
					/>
				</div>
				{#if usernameError}
					<Field.FieldError>{usernameError}</Field.FieldError>
				{/if}
				<ul class="flex flex-col gap-1 text-xs text-muted-foreground">
					<li>от 3 до 25 символов</li>
					<li>начинается с буквы (латиница или кириллица)</li>
					<li>далее буквы, цифры и подчёркивание</li>
				</ul>
			</Field.Field>

			<Button type="submit" class="w-full" disabled={!isValid() || isLoading}>
				{#if isLoading}
					<Spinner data-icon="inline-start" />
					Сохранение…
				{:else}
					Сохранить
				{/if}
			</Button>
		</form>
	</Dialog.Content>
</Dialog.Root>
