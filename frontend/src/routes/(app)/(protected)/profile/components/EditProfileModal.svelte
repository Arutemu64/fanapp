<script lang="ts">
	import { User } from '@lucide/svelte';
	import { createMutation, useQueryClient } from '@tanstack/svelte-query';
	import { untrack } from 'svelte';

	import type { CurrentUserDto, UpdateCurrentUserInput } from '#lib/api/generated/index.js';

	import { getApiErrorDetail, getApiFieldError } from '#lib/api/errors.js';
	import {
		getCurrentUserQueryKey,
		updateCurrentUserMutation
	} from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import * as Alert from '#lib/components/ui/alert/index.js';
	import { Button } from '#lib/components/ui/button/index.js';
	import * as Dialog from '#lib/components/ui/dialog/index.js';
	import * as Field from '#lib/components/ui/field/index.js';
	import { Input } from '#lib/components/ui/input/index.js';
	import { Spinner } from '#lib/components/ui/spinner/index.js';
	import { getToastService } from '#lib/services/toasts.svelte.js';

	interface Props {
		user: CurrentUserDto;
		open: boolean;
	}

	let { user, open = $bindable(false) }: Props = $props();
	const queryClient = useQueryClient();
	const toastService = getToastService();

	const updateProfileMutation = createMutation(() => ({
		...updateCurrentUserMutation(),
		onSuccess: () => queryClient.invalidateQueries({ queryKey: getCurrentUserQueryKey() })
	}));

	let username = $state('');

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

	// Validate when the field is left, not on every keystroke: "Минимум 3 символа"
	// after the first letter scolds someone who is still typing
	// (https://www.nngroup.com/articles/errors-forms-design-guidelines/). Once an
	// error is showing, re-check as they type so it clears the moment it's fixed.
	function handleUsernameInput(event: Event & { currentTarget: HTMLInputElement }) {
		formError = '';
		if (usernameError) {
			usernameError = validateUsername(event.currentTarget.value);
		}
	}

	function handleUsernameBlur() {
		usernameError = validateUsername(username);
	}

	function hasChanges(): boolean {
		return !!username && username !== user.username;
	}

	function isValid(): boolean {
		return !usernameError;
	}

	function handleSubmit(e: Event) {
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

		const body: UpdateCurrentUserInput = {};
		if (username && username !== user.username) body.username = username;

		updateProfileMutation.mutate(
			{ body },
			{
				onSuccess: () => {
					toastService.add('Профиль обновлён', 'success');
					open = false;
					username = '';
				},
				onError: (error) => {
					const usernameFieldError = getApiFieldError(error, 'username');
					if (usernameFieldError) {
						usernameError = usernameFieldError;
						return;
					}
					formError = getApiErrorDetail(error) ?? 'Не удалось обновить профиль';
				}
			}
		);
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
						onblur={handleUsernameBlur}
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

			<Button type="submit" class="w-full" disabled={updateProfileMutation.isPending}>
				{#if updateProfileMutation.isPending}
					<Spinner data-icon="inline-start" />
					Сохранение…
				{:else}
					Сохранить
				{/if}
			</Button>
		</form>
	</Dialog.Content>
</Dialog.Root>
