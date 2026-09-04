<script lang="ts">
	import { createApiClient } from '$lib/api';
	const client = createApiClient();
	import BackLink from '$lib/components/BackLink.svelte';
	import SectionIntro from '$lib/components/SectionIntro.svelte';
	import * as Alert from '$lib/components/ui/alert';
	import { Button } from '$lib/components/ui/button';
	import * as Card from '$lib/components/ui/card';
	import { Checkbox } from '$lib/components/ui/checkbox';
	import * as Field from '$lib/components/ui/field';
	import { Spinner } from '$lib/components/ui/spinner';
	import { Textarea } from '$lib/components/ui/textarea';
	import { getToastService } from '$lib/services/toasts.svelte';

	const toastService = getToastService();

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
			const { error, response } = await client.POST('/notifications/broadcast', {
				body: {
					body: bodyText.trim(),
					roles: selectedRoles as ('visitor' | 'participant' | 'helper' | 'org')[]
				}
			});

			if (error || !response.ok) {
				if (response.status === 401) {
					submitError = 'Нужно войти в аккаунт заново';
				} else if (response.status === 403) {
					submitError = 'У тебя нет доступа к отправке уведомлений';
				} else if (response.status === 422) {
					submitError = 'Проверь правильность заполнения полей';
				} else {
					submitError = 'Не удалось запустить рассылку';
				}
				return;
			}

			toastService.add('Рассылка запущена', 'success');
			bodyText = '';
			selectedRoles = [];
			bodyError = '';
			rolesError = '';
		} catch (err) {
			console.error('Failed to send broadcast:', err);
			submitError = 'Произошла непредвиденная ошибка';
		} finally {
			isSending = false;
		}
	}
</script>

<svelte:head>
	<title>Рассылка уведомлений · ФАН ФАН</title>
</svelte:head>

<BackLink href="/tools" label="Назад к инструментам" />

<SectionIntro
	description="Создавай массовые рассылки уведомлений для выбранных категорий участников фестиваля."
/>

<Card.Root class="mx-auto w-full max-w-2xl rounded-2xl p-4 sm:p-6">
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
				class="w-full resize-none rounded-xl"
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

		<Field.FieldSet
			class="rounded-lg border border-border p-4"
			data-invalid={rolesError ? true : undefined}
		>
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

		<Button type="submit" class="min-h-11 w-full justify-center sm:w-auto" disabled={isSending}>
			{#if isSending}
				<Spinner data-icon="inline-start" />
				Отправка…
			{:else}
				Отправить рассылку
			{/if}
		</Button>
	</form>
</Card.Root>
