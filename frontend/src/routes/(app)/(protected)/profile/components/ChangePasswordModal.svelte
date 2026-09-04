<script lang="ts">
	import type { components } from '$lib/api/schema';

	import { createApiClient } from '$lib/api';
	import { getApiErrorDetail } from '$lib/api/errors';
	import PasswordInput from '$lib/components/PasswordInput.svelte';
	import * as Alert from '$lib/components/ui/alert';
	import { Button } from '$lib/components/ui/button';
	import * as Dialog from '$lib/components/ui/dialog';
	import * as Field from '$lib/components/ui/field';
	import { Spinner } from '$lib/components/ui/spinner';
	import { getToastService } from '$lib/services/toasts.svelte';
	import { CheckCircle2, Lock, XCircle } from '@lucide/svelte';

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

		toastService.add(hasPassword ? 'Пароль изменён' : 'Пароль установлен', 'success');
		oldPassword = '';
		newPassword = '';
		open = false;
		if (onSuccess) onSuccess();
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
				<Field.Field>
					<Field.FieldLabel for="new_password">Новый пароль</Field.FieldLabel>
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

			<Button type="submit" class="w-full" disabled={isLoading || !isValid}>
				{#if isLoading}
					<Spinner data-icon="inline-start" />
					Сохранение…
				{:else}
					{hasPassword ? 'Сменить пароль' : 'Установить пароль'}
				{/if}
			</Button>
		</form>
	</Dialog.Content>
</Dialog.Root>
