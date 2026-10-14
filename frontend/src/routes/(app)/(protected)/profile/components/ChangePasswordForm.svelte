<script lang="ts">
	import { CheckCircle2, XCircle } from '@lucide/svelte';

	import type { ChangePasswordInput } from '#lib/api/generated/index.js';

	import { getApiErrorDetail } from '#lib/api/errors.js';
	import PasswordInput from '#lib/components/PasswordInput.svelte';
	import * as Alert from '#lib/components/ui/alert/index.js';
	import { Button } from '#lib/components/ui/button/index.js';
	import * as Field from '#lib/components/ui/field/index.js';
	import { Spinner } from '#lib/components/ui/spinner/index.js';
	import { m } from '#lib/paraglide/messages.js';

	interface Props {
		hasPassword: boolean;
		pending: boolean;
		/** Changes the password; rejects with the API error body. */
		onSave: (body: ChangePasswordInput) => Promise<void>;
	}

	let { hasPassword, pending, onSave }: Props = $props();

	// Mounted fresh on every open (inside Dialog.Content), so no typed password
	// survives a close.
	let oldPassword = $state('');
	let newPassword = $state('');
	let formError = $state('');
	let newPasswordError = $state('');

	// Password rules mirror the backend PASSWORD_FIELD (10-128 chars, no complexity rule).
	const MIN_PASSWORD_LENGTH = 10;
	const MAX_PASSWORD_LENGTH = 128;

	let hasMinLength = $derived(newPassword.length >= MIN_PASSWORD_LENGTH);
	let withinMaxLength = $derived(newPassword.length <= MAX_PASSWORD_LENGTH);
	let isValid = $derived(hasMinLength && withinMaxLength);

	async function handleSubmit(e: Event) {
		e.preventDefault();

		if (!isValid) {
			newPasswordError = m.password_length_error({
				min: MIN_PASSWORD_LENGTH,
				max: MAX_PASSWORD_LENGTH
			});
			return;
		}

		const body: ChangePasswordInput = {
			old_password: oldPassword || null,
			new_password: newPassword
		};

		try {
			await onSave(body);
		} catch (error) {
			formError = getApiErrorDetail(error) ?? m.password_change_failed();
		}
	}
</script>

<form onsubmit={handleSubmit} class="flex flex-col gap-4">
	{#if formError}
		<Alert.Root variant="destructive">
			<Alert.Description>{formError}</Alert.Description>
		</Alert.Root>
	{/if}

	<Field.FieldGroup class="gap-4">
		{#if hasPassword}
			<Field.Field>
				<Field.FieldLabel for="old_password">{m.password_old_label()}</Field.FieldLabel>
				<PasswordInput
					id="old_password"
					name="current_password"
					autocomplete="current-password"
					showLabel={m.password_show_old()}
					hideLabel={m.password_hide_old()}
					bind:value={oldPassword}
					oninput={() => (formError = '')}
				/>
			</Field.Field>
		{/if}
		<Field.Field data-invalid={newPasswordError ? true : undefined}>
			<Field.FieldLabel for="new_password">{m.password_new_label()}</Field.FieldLabel>
			<PasswordInput
				id="new_password"
				name="new_password"
				autocomplete="new-password"
				showLabel={m.password_show_new()}
				hideLabel={m.password_hide_new()}
				maxlength={MAX_PASSWORD_LENGTH}
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
					{m.password_min_length({ count: MIN_PASSWORD_LENGTH })}
				</li>
			</ul>
		</Field.Field>
	</Field.FieldGroup>

	<Button type="submit" class="w-full" disabled={pending}>
		{#if pending}
			<Spinner data-icon="inline-start" />
			{m.common_saving()}
		{:else}
			{hasPassword ? m.password_change() : m.password_set()}
		{/if}
	</Button>
</form>
