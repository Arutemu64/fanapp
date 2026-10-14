<script lang="ts">
	import { CheckCircle2, Lock, XCircle } from '@lucide/svelte';
	import { createMutation, useQueryClient } from '@tanstack/svelte-query';

	import type { ChangePasswordInput } from '#lib/api/generated/index.js';

	import { getApiErrorDetail } from '#lib/api/errors.js';
	import {
		changeCurrentUserPasswordMutation,
		getCurrentUserQueryKey
	} from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import PasswordInput from '#lib/components/PasswordInput.svelte';
	import * as Alert from '#lib/components/ui/alert/index.js';
	import { Button } from '#lib/components/ui/button/index.js';
	import * as Dialog from '#lib/components/ui/dialog/index.js';
	import * as Field from '#lib/components/ui/field/index.js';
	import { Spinner } from '#lib/components/ui/spinner/index.js';
	import { getToastService } from '#lib/services/toasts.svelte.js';

	interface Props {
		open: boolean;
		hasPassword?: boolean;
		// Account email, handed to password managers as the username of the password
		// being saved. Null for an account that signs in through a social service.
		email?: string | null;
	}

	let { open = $bindable(false), hasPassword = true, email = null }: Props = $props();
	const queryClient = useQueryClient();

	// Not awaited: the refreshed user flips `hasPassword`, and with it this
	// dialog's title and toast, so the dialog closes first.
	const changePasswordMutation = createMutation(() => ({
		...changeCurrentUserPasswordMutation(),
		onSuccess: () => void queryClient.invalidateQueries({ queryKey: getCurrentUserQueryKey() })
	}));

	let oldPassword = $state('');
	const toastService = getToastService();
	let newPassword = $state('');
	let formError = $state('');
	let newPasswordError = $state('');

	// Password rules mirror the backend PASSWORD_FIELD (10-128 chars, no complexity rule).
	const MIN_PASSWORD_LENGTH = 10;
	const MAX_PASSWORD_LENGTH = 128;

	// Screen-reader description for the dialog (visually the form speaks for itself).
	let dialogDescription = $derived(
		hasPassword ? 'Смени пароль от своего аккаунта.' : 'Задай пароль для входа в аккаунт.'
	);

	let hasMinLength = $derived(newPassword.length >= MIN_PASSWORD_LENGTH);
	let withinMaxLength = $derived(newPassword.length <= MAX_PASSWORD_LENGTH);
	let isValid = $derived(hasMinLength && withinMaxLength);

	$effect(() => {
		if (open) {
			oldPassword = '';
			newPassword = '';
			formError = '';
			newPasswordError = '';
		}
	});

	function handleSubmit(e: Event) {
		e.preventDefault();

		if (!isValid) {
			newPasswordError = `Новый пароль должен быть от ${MIN_PASSWORD_LENGTH} до ${MAX_PASSWORD_LENGTH} символов`;
			return;
		}

		const body: ChangePasswordInput = {
			old_password: oldPassword || null,
			new_password: newPassword
		};

		changePasswordMutation.mutate(
			{ body },
			{
				onSuccess: () => {
					toastService.add(hasPassword ? 'Пароль изменён' : 'Пароль установлен', 'success');
					oldPassword = '';
					newPassword = '';
					open = false;
				},
				onError: (error) => {
					formError = getApiErrorDetail(error) ?? 'Не удалось сменить пароль';
				}
			}
		);
	}
</script>

<Dialog.Root bind:open>
	<Dialog.Content class="sm:max-w-md">
		<Dialog.Header>
			<Dialog.Title class="flex items-center gap-2">
				<Lock class="size-5 text-muted-foreground" />
				{hasPassword ? 'Изменение пароля' : 'Установка пароля'}
			</Dialog.Title>
			<Dialog.Description class="sr-only">{dialogDescription}</Dialog.Description>
		</Dialog.Header>

		<form onsubmit={handleSubmit} class="flex flex-col gap-4">
			<!-- Password managers pair a saved password with the username field in the
				same form. Visually hidden rather than display:none, which managers may
				skip. https://web.dev/articles/sign-in-form-best-practices -->
			{#if email}
				<input
					type="text"
					name="username"
					autocomplete="username"
					value={email}
					readonly
					tabindex={-1}
					aria-hidden="true"
					class="sr-only"
				/>
			{/if}
			{#if formError}
				<Alert.Root variant="destructive">
					<Alert.Description>{formError}</Alert.Description>
				</Alert.Root>
			{/if}

			<Field.FieldGroup class="gap-4">
				{#if hasPassword}
					<Field.Field>
						<Field.FieldLabel for="old_password">Старый пароль</Field.FieldLabel>
						<PasswordInput
							id="old_password"
							name="current_password"
							autocomplete="current-password"
							revealLabel="старый пароль"
							bind:value={oldPassword}
							oninput={() => (formError = '')}
						/>
					</Field.Field>
				{/if}
				<Field.Field data-invalid={newPasswordError ? true : undefined}>
					<Field.FieldLabel for="new_password">Новый пароль</Field.FieldLabel>
					<PasswordInput
						id="new_password"
						name="new_password"
						autocomplete="new-password"
						revealLabel="новый пароль"
						maxlength={MAX_PASSWORD_LENGTH}
						passwordrules="minlength: {MIN_PASSWORD_LENGTH}; maxlength: {MAX_PASSWORD_LENGTH};"
						color={newPasswordError ? 'red' : undefined}
						bind:value={newPassword}
						oninput={() => {
							formError = '';
							newPasswordError = '';
						}}
					/>
					{#if newPasswordError}
						<Field.FieldError>{newPasswordError}</Field.FieldError>
					{/if}

					<!-- Live password requirements; reflects the backend PASSWORD_FIELD rules. -->
					<ul class="mt-1 flex flex-col gap-1">
						<li
							class="flex items-center gap-2 text-sm {hasMinLength
								? 'text-success'
								: 'text-muted-foreground'}"
						>
							{#if hasMinLength}
								<CheckCircle2 class="size-4 shrink-0" />
							{:else}
								<XCircle class="size-4 shrink-0" />
							{/if}
							Минимум {MIN_PASSWORD_LENGTH} символов
						</li>
					</ul>
				</Field.Field>
			</Field.FieldGroup>

			<Button type="submit" class="w-full" disabled={changePasswordMutation.isPending}>
				{#if changePasswordMutation.isPending}
					<Spinner data-icon="inline-start" />
					Сохранение…
				{:else}
					{hasPassword ? 'Сменить пароль' : 'Установить пароль'}
				{/if}
			</Button>
		</form>
	</Dialog.Content>
</Dialog.Root>
