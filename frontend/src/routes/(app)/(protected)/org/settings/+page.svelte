<script lang="ts">
	import { invalidate } from '$app/navigation';
	import { client } from '$lib/api';
	import SectionHeader from '$lib/components/SectionHeader.svelte';
	import { getToastService } from '$lib/services/toasts.svelte';
	import type { PageProps } from './$types';
	import { Alert, Button, Card, Helper, Input, Label, Spinner, Toggle } from 'flowbite-svelte';
	import { untrack } from 'svelte';

	let { data }: PageProps = $props();
	const toastService = getToastService();

	let isSaving = $state(false);
	let savedVotingEnabled = $state(untrack(() => data.settings.voting_enabled));
	let savedAnnouncementTimeout = $state(untrack(() => data.settings.limits.announcement_timeout));
	let votingEnabled = $state(untrack(() => data.settings.voting_enabled));
	let announcementTimeout = $state<number | undefined>(
		untrack(() => data.settings.limits.announcement_timeout)
	);
	let announcementTimeoutError = $state('');
	let submitError = $state('');

	let hasChanges = $derived(
		votingEnabled !== savedVotingEnabled || announcementTimeout !== savedAnnouncementTimeout
	);

	function validateAnnouncementTimeout() {
		if (announcementTimeout === undefined || Number.isNaN(announcementTimeout)) {
			announcementTimeoutError = 'Укажи таймаут анонсов';
			return false;
		}

		if (!Number.isInteger(announcementTimeout) || announcementTimeout < 1) {
			announcementTimeoutError = 'Введи целое число не меньше 1';
			return false;
		}

		announcementTimeoutError = '';
		return true;
	}

	function handleAnnouncementTimeoutInput() {
		submitError = '';
		// Re-validate live only after the field has already shown an error once.
		if (announcementTimeoutError) {
			validateAnnouncementTimeout();
		}
	}

	async function handleSubmit(event: Event) {
		event.preventDefault();
		submitError = '';

		if (!validateAnnouncementTimeout()) {
			return;
		}

		const nextAnnouncementTimeout = announcementTimeout;

		if (nextAnnouncementTimeout === undefined) {
			return;
		}

		isSaving = true;

		try {
			const { error, response } = await client.PATCH('/settings', {
				body: {
					voting_enabled: votingEnabled,
					announcement_timeout: nextAnnouncementTimeout
				}
			});

			if (error || !response.ok) {
				if (response.status === 401) {
					submitError = 'Нужно войти в аккаунт заново';
				} else if (response.status === 403) {
					submitError = 'У тебя нет доступа к настройкам фестиваля';
				} else if (response.status === 404) {
					submitError = 'Настройки фестиваля не найдены';
				} else if (response.status === 422) {
					submitError = 'Проверь введённые значения и попробуй снова';
				} else {
					submitError = 'Не удалось сохранить настройки фестиваля';
				}

				return;
			}

			savedVotingEnabled = votingEnabled;
			savedAnnouncementTimeout = nextAnnouncementTimeout;
			announcementTimeoutError = '';
			toastService.add('Настройки фестиваля сохранены', 'success');
			await invalidate('app:festival-settings');
		} catch (err) {
			console.error('Festival settings update failed:', err);
			submitError = 'Не удалось сохранить настройки фестиваля';
		} finally {
			isSaving = false;
		}
	}
</script>

<svelte:head>
	<title>Настройки фестиваля</title>
</svelte:head>

<SectionHeader
	title="Настройки фестиваля"
	description="Управляй голосованием и таймаутом между анонсами расписания."
/>

<Card class="mx-auto w-full max-w-2xl rounded-2xl p-4 sm:p-6">
	<form class="space-y-5" onsubmit={handleSubmit}>
		{#if submitError}
			<Alert color="red" class="rounded-xl text-sm">
				{submitError}
			</Alert>
		{/if}

		<div class="rounded-lg border border-gray-200 p-3 sm:p-4 dark:border-gray-700">
			<div class="flex items-start justify-between gap-3">
				<div class="min-w-0">
					<h2 class="text-base font-medium text-gray-900 dark:text-white">Голосование активно</h2>
					<p class="mt-1 text-sm leading-6 text-gray-500 dark:text-gray-400">
						Если отключить эту настройку, посетители временно не смогут голосовать.
					</p>
				</div>
				<Toggle
					bind:checked={votingEnabled}
					color="green"
					disabled={isSaving}
					onchange={() => (submitError = '')}
				/>
			</div>
		</div>

		<div class="space-y-2 rounded-lg border border-gray-200 p-3 sm:p-4 dark:border-gray-700">
			<Label for="announcement-timeout">Таймаут анонсов, сек</Label>
			<Input
				id="announcement-timeout"
				name="announcement_timeout"
				type="number"
				min="1"
				step="1"
				inputmode="numeric"
				autocomplete="off"
				bind:value={announcementTimeout}
				disabled={isSaving}
				oninput={handleAnnouncementTimeoutInput}
				onblur={validateAnnouncementTimeout}
			/>
			{#if announcementTimeoutError}
				<Helper color="red">{announcementTimeoutError}</Helper>
			{:else}
				<Helper>Минимум 1 секунда. Ограничение помогает не отправлять анонсы слишком часто.</Helper>
			{/if}
		</div>

		<Button
			type="submit"
			color="primary"
			class="min-h-11 w-full justify-center rounded-xl sm:w-auto"
			disabled={isSaving || !hasChanges}
		>
			{#if isSaving}
				<Spinner size="4" class="mr-2" color="primary" />
				Сохраняем…
			{:else}
				Сохранить
			{/if}
		</Button>
	</form>
</Card>
