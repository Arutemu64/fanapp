<script lang="ts">
	import { invalidate } from '$app/navigation';
	import { AlertCircle } from '@lucide/svelte';

	import type { UserRole } from '#lib/api/generated/index.js';

	import { getApiErrorDetail, getApiFieldError } from '#lib/api/errors.js';
	import { sendBroadcast } from '#lib/api/generated/index.js';
	import { createApiClient } from '#lib/api/index.js';
	import SectionIntro from '#lib/components/SectionIntro.svelte';
	import * as Alert from '#lib/components/ui/alert/index.js';
	import { Button } from '#lib/components/ui/button/index.js';
	import { Checkbox } from '#lib/components/ui/checkbox/index.js';
	import * as Field from '#lib/components/ui/field/index.js';
	import { Spinner } from '#lib/components/ui/spinner/index.js';
	import { Textarea } from '#lib/components/ui/textarea/index.js';
	import { getToastService } from '#lib/services/toasts.svelte.js';
	import { feedSnapshotKey } from '#lib/utils/feed.js';

	import type { PageProps } from './$types';

	import ConfirmDialog from '../components/ConfirmDialog.svelte';
	import BroadcastHistory from './components/BroadcastHistory.svelte';

	let { data }: PageProps = $props();

	const client = createApiClient();
	const toastService = getToastService();

	const ROLE_OPTIONS: { value: UserRole; label: string }[] = [
		{ value: 'visitor', label: 'Зрители' },
		{ value: 'participant', label: 'Участники' },
		{ value: 'helper', label: 'Волонтёры' },
		{ value: 'org', label: 'Организаторы' }
	];

	// Remount the history with the fresh server snapshot whenever route data changes
	// (a new send or a cancel triggers invalidate('app:broadcasts')).
	let broadcastsKey = $derived(
		feedSnapshotKey(
			data.hasMore,
			data.mailings.map((mailing) => mailing.id)
		)
	);

	let bodyText = $state('');
	let selectedRoles = $state<UserRole[]>([]);
	let confirmOpen = $state(false);
	let isSending = $state(false);

	let bodyError = $state('');
	let rolesError = $state('');
	let submitError = $state('');

	function validateForm() {
		let isValid = true;

		if (!bodyText.trim()) {
			bodyError = 'Введи текст уведомления';
			isValid = false;
		} else {
			bodyError = '';
		}

		if (selectedRoles.length === 0) {
			rolesError = 'Выбери хотя бы одну группу пользователей';
			isValid = false;
		} else {
			rolesError = '';
		}

		return isValid;
	}

	function handleBodyInput() {
		if (bodyError) {
			bodyError = bodyText.trim() ? '' : 'Введи текст уведомления';
		}
	}

	function handleRoleChange() {
		if (rolesError) {
			rolesError = selectedRoles.length > 0 ? '' : 'Выбери хотя бы одну группу пользователей';
		}
	}

	function toggleRole(role: UserRole, checked: boolean) {
		if (checked) {
			if (!selectedRoles.includes(role)) selectedRoles = [...selectedRoles, role];
		} else {
			selectedRoles = selectedRoles.filter((r) => r !== role);
		}
		handleRoleChange();
	}

	// In ROLE_OPTIONS order, whatever order the boxes were ticked in.
	let recipientsLabel = $derived(
		ROLE_OPTIONS.filter((option) => selectedRoles.includes(option.value))
			.map((option) => option.label)
			.join(', ')
	);

	// A mailing reaches every account in the chosen roles and a delivered push can't
	// be recalled, so the form only validates here and the send waits for the
	// confirm dialog (https://www.nngroup.com/articles/confirmation-dialog/).
	function handleSubmit(event: Event) {
		event.preventDefault();
		submitError = '';

		if (!validateForm()) {
			return;
		}

		confirmOpen = true;
	}

	async function send() {
		if (isSending) return;
		isSending = true;

		try {
			const { error, response } = await sendBroadcast({
				client,
				body: {
					body: bodyText.trim(),
					roles: selectedRoles
				}
			});

			if (error || !response?.ok) {
				bodyError = getApiFieldError(error, 'body') ?? '';
				rolesError = getApiFieldError(error, 'roles') ?? '';
				if (bodyError || rolesError) {
					return;
				}
				submitError = getApiErrorDetail(error) ?? 'Не удалось запустить рассылку';
				return;
			}

			toastService.add('Рассылка запущена', 'success');
			bodyText = '';
			selectedRoles = [];
			bodyError = '';
			rolesError = '';
			await invalidate('app:broadcasts');
		} finally {
			isSending = false;
		}
	}
</script>

<svelte:head>
	<title>Рассылка уведомлений · ФАН ФАН</title>
</svelte:head>

<SectionIntro
	description="Создавай массовые рассылки уведомлений для выбранных категорий участников фестиваля."
/>

<!-- novalidate keeps the browser's own bubbles out, so every error is ours and in
     Russian; the textarea goes read-only, not disabled, while sending so focus and
     the keyboard stay put. -->
<form novalidate class="flex flex-col gap-6" onsubmit={handleSubmit}>
	<Field.Field data-invalid={bodyError ? true : undefined}>
		<Field.FieldLabel for="broadcast-body">Текст уведомления</Field.FieldLabel>
		<Textarea
			id="broadcast-body"
			name="body"
			rows={4}
			placeholder="Напиши важное сообщение для участников фестиваля…"
			bind:value={bodyText}
			readonly={isSending}
			oninput={handleBodyInput}
			class="resize-none"
			aria-invalid={bodyError ? true : undefined}
		/>
		{#if bodyError}
			<Field.FieldError>{bodyError}</Field.FieldError>
		{:else}
			<Field.FieldDescription>
				Уведомление сразу уйдёт всем пользователям с выбранными ролями.
			</Field.FieldDescription>
		{/if}
	</Field.Field>

	<Field.FieldSet data-invalid={rolesError ? true : undefined}>
		<Field.FieldLegend variant="label">Кому отправить</Field.FieldLegend>
		<Field.FieldGroup data-slot="checkbox-group" class="grid grid-cols-1 gap-3 sm:grid-cols-2">
			{#each ROLE_OPTIONS as option (option.value)}
				<Field.Field orientation="horizontal">
					<Checkbox
						id="role-{option.value}"
						checked={selectedRoles.includes(option.value)}
						onCheckedChange={(checked) => toggleRole(option.value, checked === true)}
						disabled={isSending}
					/>
					<Field.FieldLabel for="role-{option.value}" class="cursor-pointer font-normal">
						{option.label}
					</Field.FieldLabel>
				</Field.Field>
			{/each}
		</Field.FieldGroup>
		{#if rolesError}
			<Field.FieldError>{rolesError}</Field.FieldError>
		{/if}
	</Field.FieldSet>

	{#if submitError}
		<Alert.Root variant="destructive">
			<AlertCircle />
			<Alert.Description>{submitError}</Alert.Description>
		</Alert.Root>
	{/if}

	<Button type="submit" class="w-full sm:w-auto sm:self-start" disabled={isSending}>
		{#if isSending}
			<Spinner data-icon="inline-start" />
			Отправляем…
		{:else}
			Отправить рассылку
		{/if}
	</Button>
</form>

<div class="mt-10">
	{#key broadcastsKey}
		<BroadcastHistory initialMailings={data.mailings} initialHasMore={data.hasMore} />
	{/key}
</div>

<ConfirmDialog
	bind:open={confirmOpen}
	title="Отправить рассылку?"
	description="Получатели: {recipientsLabel}. Пуш-уведомление нельзя будет отозвать, а отменить рассылку можно, только пока она не разослана до конца."
	confirmLabel="Отправить рассылку"
	onconfirm={send}
/>
