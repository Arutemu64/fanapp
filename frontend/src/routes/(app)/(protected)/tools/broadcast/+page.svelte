<script lang="ts">
	import { getApiErrorDetail, getApiFieldError } from '#lib/api/errors.js';
	import { sendBroadcast } from '#lib/api/generated/index.js';
	import { createApiClient } from '#lib/api/index.js';
	const client = createApiClient();
	import { invalidate } from '$app/navigation';

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

	import BroadcastHistory from './components/BroadcastHistory.svelte';

	let { data }: PageProps = $props();

	const toastService = getToastService();

	// Remount the history with the fresh server snapshot whenever route data changes
	// (a new send or a cancel triggers invalidate('app:broadcasts')).
	let broadcastsKey = $derived(
		feedSnapshotKey(
			data.hasMore,
			data.mailings.map((mailing) => mailing.id)
		)
	);

	let bodyText = $state('');
	let selectedRoles = $state<string[]>([]);
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

	function toggleRole(role: string, checked: boolean) {
		if (checked) {
			if (!selectedRoles.includes(role)) selectedRoles = [...selectedRoles, role];
		} else {
			selectedRoles = selectedRoles.filter((r) => r !== role);
		}
		handleRoleChange();
	}

	async function handleSubmit(event: Event) {
		event.preventDefault();
		submitError = '';

		if (!validateForm()) {
			return;
		}

		isSending = true;

		try {
			const { error, response } = await sendBroadcast({
				client,
				body: {
					body: bodyText.trim(),
					roles: selectedRoles as ('visitor' | 'participant' | 'helper' | 'org')[]
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

<div class="mx-auto w-full max-w-2xl">
	<SectionIntro
		description="Создавай массовые рассылки уведомлений для выбранных категорий участников фестиваля."
	/>

	<form class="flex flex-col gap-6" onsubmit={handleSubmit}>
		<Field.Field data-invalid={bodyError ? true : undefined}>
			<Field.FieldLabel for="broadcast-body">Текст уведомления</Field.FieldLabel>
			<Textarea
				id="broadcast-body"
				name="body"
				rows={4}
				placeholder="Напиши важное сообщение для участников фестиваля…"
				bind:value={bodyText}
				disabled={isSending}
				oninput={handleBodyInput}
				class="resize-none"
				aria-invalid={bodyError ? true : undefined}
			/>
			{#if bodyError}
				<Field.FieldError>{bodyError}</Field.FieldError>
			{:else}
				<Field.FieldDescription>
					Это сообщение будет моментально отправлено всем пользователям с выбранными ролями.
				</Field.FieldDescription>
			{/if}
		</Field.Field>

		<Field.FieldSet data-invalid={rolesError ? true : undefined}>
			<Field.FieldLegend variant="label">Кому отправить</Field.FieldLegend>
			<Field.FieldGroup data-slot="checkbox-group" class="grid grid-cols-1 gap-3 sm:grid-cols-2">
				<Field.Field orientation="horizontal">
					<Checkbox
						id="role-visitor"
						checked={selectedRoles.includes('visitor')}
						onCheckedChange={(v) => toggleRole('visitor', !!v)}
						disabled={isSending}
					/>
					<Field.FieldLabel for="role-visitor" class="cursor-pointer font-normal">
						Зрители
					</Field.FieldLabel>
				</Field.Field>
				<Field.Field orientation="horizontal">
					<Checkbox
						id="role-participant"
						checked={selectedRoles.includes('participant')}
						onCheckedChange={(v) => toggleRole('participant', !!v)}
						disabled={isSending}
					/>
					<Field.FieldLabel for="role-participant" class="cursor-pointer font-normal">
						Участники
					</Field.FieldLabel>
				</Field.Field>
				<Field.Field orientation="horizontal">
					<Checkbox
						id="role-helper"
						checked={selectedRoles.includes('helper')}
						onCheckedChange={(v) => toggleRole('helper', !!v)}
						disabled={isSending}
					/>
					<Field.FieldLabel for="role-helper" class="cursor-pointer font-normal">
						Волонтёры
					</Field.FieldLabel>
				</Field.Field>
				<Field.Field orientation="horizontal">
					<Checkbox
						id="role-org"
						checked={selectedRoles.includes('org')}
						onCheckedChange={(v) => toggleRole('org', !!v)}
						disabled={isSending}
					/>
					<Field.FieldLabel for="role-org" class="cursor-pointer font-normal">
						Организаторы
					</Field.FieldLabel>
				</Field.Field>
			</Field.FieldGroup>
			{#if rolesError}
				<Field.FieldError>{rolesError}</Field.FieldError>
			{/if}
		</Field.FieldSet>

		{#if submitError}
			<Alert.Root variant="destructive">
				<Alert.Description>{submitError}</Alert.Description>
			</Alert.Root>
		{/if}

		<Button type="submit" class="w-full sm:w-auto" disabled={isSending}>
			{#if isSending}
				<Spinner data-icon="inline-start" />
				Отправка…
			{:else}
				Отправить рассылку
			{/if}
		</Button>
	</form>
</div>

<div class="mt-8">
	{#key broadcastsKey}
		<BroadcastHistory initialMailings={data.mailings} initialHasMore={data.hasMore} />
	{/key}
</div>
