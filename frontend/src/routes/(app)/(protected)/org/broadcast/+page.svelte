<script lang="ts">
	import { createApiClient } from '$lib/api';
	const client = createApiClient();
	import SectionIntro from '$lib/components/SectionIntro.svelte';
	import { getToastService } from '$lib/services/toasts.svelte';
	import { Alert, Button, Card, Checkbox, Helper, Label, Spinner, Textarea } from 'flowbite-svelte';

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
			bodyError = 'Введите текст уведомления';
			isValid = false;
		} else {
			bodyError = '';
		}

		if (selectedRoles.length === 0) {
			rolesError = 'Выберите хотя бы одну группу пользователей';
			isValid = false;
		} else {
			rolesError = '';
		}

		return isValid;
	}

	function handleBodyInput() {
		if (bodyError) {
			bodyError = bodyText.trim() ? '' : 'Введите текст уведомления';
		}
	}

	function handleRoleChange() {
		if (rolesError) {
			rolesError = selectedRoles.length > 0 ? '' : 'Выберите хотя бы одну группу пользователей';
		}
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
					submitError = 'У вас нет доступа к отправке уведомлений';
				} else if (response.status === 422) {
					submitError = 'Проверьте правильность заполнения полей';
				} else {
					submitError = 'Не удалось запустить рассылку';
				}
				return;
			}

			toastService.add('Рассылка успешно запущена!', 'success');
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

<SectionIntro
	description="Создавай массовые рассылки уведомлений для выбранных категорий участников фестиваля."
/>

<Card class="mx-auto w-full max-w-2xl rounded-2xl p-4 sm:p-6">
	<form class="space-y-6" onsubmit={handleSubmit}>
		<div class="space-y-2">
			<Label for="broadcast-body" class="text-gray-900 dark:text-white">Текст уведомления</Label>
			<Textarea
				id="broadcast-body"
				name="body"
				rows={4}
				placeholder="Напишите важное сообщение для участников фестиваля..."
				bind:value={bodyText}
				disabled={isSending}
				oninput={handleBodyInput}
				class="w-full rounded-xl"
			/>
			{#if bodyError}
				<Helper color="red" class="mt-1">{bodyError}</Helper>
			{:else}
				<Helper class="text-sm text-gray-500 dark:text-gray-400">
					Это сообщение будет моментально отправлено всем пользователям с выбранными ролями.
				</Helper>
			{/if}
		</div>

		<div class="space-y-3 rounded-lg border border-gray-200 p-4 dark:border-gray-700">
			<span class="block text-sm font-medium text-gray-900 dark:text-white">Кому отправить</span>
			<div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
				<Checkbox
					bind:group={selectedRoles}
					value="visitor"
					disabled={isSending}
					onchange={handleRoleChange}
				>
					Зрители
				</Checkbox>
				<Checkbox
					bind:group={selectedRoles}
					value="participant"
					disabled={isSending}
					onchange={handleRoleChange}
				>
					Участники
				</Checkbox>
				<Checkbox
					bind:group={selectedRoles}
					value="helper"
					disabled={isSending}
					onchange={handleRoleChange}
				>
					Волонтёры
				</Checkbox>
				<Checkbox
					bind:group={selectedRoles}
					value="org"
					disabled={isSending}
					onchange={handleRoleChange}
				>
					Организаторы
				</Checkbox>
			</div>
			{#if rolesError}
				<Helper color="red" class="mt-1">{rolesError}</Helper>
			{/if}
		</div>

		{#if submitError}
			<Alert color="red" class="rounded-xl">
				{submitError}
			</Alert>
		{/if}

		<Button
			type="submit"
			color="primary"
			class="min-h-11 w-full justify-center rounded-xl sm:w-auto"
			disabled={isSending}
		>
			{#if isSending}
				<Spinner size="4" class="mr-2" color="primary" />
				Отправка…
			{:else}
				Отправить рассылку
			{/if}
		</Button>
	</form>
</Card>
