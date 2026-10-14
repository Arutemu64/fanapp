<script lang="ts">
	import { RefreshCw, User } from '@lucide/svelte';
	import { createMutation, useQueryClient } from '@tanstack/svelte-query';

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
	import UserAvatar from '#lib/components/UserAvatar.svelte';
	import { getToastService } from '#lib/services/toasts.svelte.js';
	import { createAvatarSeed } from '#lib/utils/avatar.js';

	interface Props {
		user: CurrentUserDto;
		onclose: () => void;
	}

	let { user, onclose }: Props = $props();
	const queryClient = useQueryClient();
	const toastService = getToastService();

	// The toast lives here, not in `mutate()`'s callbacks: those are dropped if the
	// dialog is dismissed while the request is in flight, which would lose the
	// confirmation of a profile that was in fact saved.
	const updateProfileMutation = createMutation(() => ({
		...updateCurrentUserMutation(),
		onSuccess: () => {
			toastService.add('Профиль обновлён', 'success');
			return queryClient.invalidateQueries({ queryKey: getCurrentUserQueryKey() });
		}
	}));

	// Snapshots of the saved profile taken when the dialog opens: the form edits a
	// draft, so a background refetch of `user` must not overwrite what is being typed.
	// svelte-ignore state_referenced_locally
	let username = $state(user.username ?? '');
	// svelte-ignore state_referenced_locally
	let avatarSeed = $state(user.avatar_seed);

	let usernameError = $state('');
	let formError = $state('');

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
		return (!!username && username !== user.username) || avatarSeed !== user.avatar_seed;
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
			onclose();
			return;
		}

		const body: UpdateCurrentUserInput = {};
		if (username && username !== user.username) body.username = username;
		if (avatarSeed !== user.avatar_seed) body.avatar_seed = avatarSeed;

		updateProfileMutation.mutate(
			{ body },
			{
				onSuccess: onclose,
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

<Dialog.Header>
	<Dialog.Title class="flex items-center gap-2">
		<User class="size-5 text-muted-foreground" />
		Редактирование профиля
	</Dialog.Title>
	<Dialog.Description class="sr-only">Измени аватар и имя пользователя.</Dialog.Description>
</Dialog.Header>

<form onsubmit={handleSubmit} class="flex flex-col gap-4">
	{#if formError}
		<Alert.Root variant="destructive">
			<Alert.Description>{formError}</Alert.Description>
		</Alert.Root>
	{/if}

	<!-- A new face is only previewed here; it is saved with the form, so closing keeps the old one. -->
	<div class="relative mx-auto">
		<UserAvatar seed={avatarSeed} class="size-32 sm:size-36" />
		<Button
			type="button"
			variant="secondary"
			size="icon"
			class="absolute right-0 bottom-0 size-11 rounded-full border border-border shadow-sm"
			aria-label="Другой аватар"
			onclick={() => (avatarSeed = createAvatarSeed())}
		>
			<RefreshCw aria-hidden="true" />
		</Button>
	</div>

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
