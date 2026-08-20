<script lang="ts">
	import { invalidate } from '$app/navigation';
	import { createApiClient } from '$lib/api';
	const client = createApiClient();
	import BackLink from '$lib/components/BackLink.svelte';
	import SectionIntro from '$lib/components/SectionIntro.svelte';
	import { getToastService } from '$lib/services/toasts.svelte';
	import { fromEventDateTimeLocal, toEventDateTimeLocal } from '$lib/utils/formatters';
	import { Alert, Button, Card, Helper, Input, Label, Spinner, Toggle } from 'flowbite-svelte';
	import { untrack } from 'svelte';

	import type { PageProps } from './$types';

	let { data }: PageProps = $props();
	const toastService = getToastService();

	let isSaving = $state(false);
	// festival_start is an instant; edit it on the venue clock via a zone-naive
	// datetime-local, converting back to an ISO instant only when saving.
	let savedFestivalStart = $state(
		untrack(() => toEventDateTimeLocal(data.settings.festival_start))
	);
	let savedFestivalEnded = $state(untrack(() => data.settings.festival_ended));
	let festivalStart = $state(untrack(() => toEventDateTimeLocal(data.settings.festival_start)));
	let festivalEnded = $state(untrack(() => data.settings.festival_ended));
	let festivalStartError = $state('');
	let savedVotingEnabled = $state(untrack(() => data.settings.voting_enabled));
	let savedAnnouncementTimeout = $state(untrack(() => data.settings.limits.announcement_timeout));
	let savedTransitionBuffer = $state(untrack(() => data.settings.limits.transition_buffer));
	let votingEnabled = $state(untrack(() => data.settings.voting_enabled));
	let announcementTimeout = $state<number | undefined>(
		untrack(() => data.settings.limits.announcement_timeout)
	);
	let transitionBuffer = $state<number | undefined>(
		untrack(() => data.settings.limits.transition_buffer)
	);
	let announcementTimeoutError = $state('');
	let transitionBufferError = $state('');
	let submitError = $state('');

	let hasChanges = $derived(
		festivalStart !== savedFestivalStart ||
			festivalEnded !== savedFestivalEnded ||
			votingEnabled !== savedVotingEnabled ||
			announcementTimeout !== savedAnnouncementTimeout ||
			transitionBuffer !== savedTransitionBuffer
	);

	function validateFestivalStart() {
		if (!festivalStart) {
			festivalStartError = 'Укажи дату и время начала фестиваля';
			return false;
		}

		festivalStartError = '';
		return true;
	}

	function handleFestivalStartInput() {
		submitError = '';
		// Re-validate live only after the field has already shown an error once.
		if (festivalStartError) {
			validateFestivalStart();
		}
	}

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

	function validateTransitionBuffer() {
		if (transitionBuffer === undefined || Number.isNaN(transitionBuffer)) {
			transitionBufferError = 'Укажи буфер перехода';
			return false;
		}

		if (!Number.isInteger(transitionBuffer) || transitionBuffer < 0) {
			transitionBufferError = 'Введи целое число не меньше 0';
			return false;
		}

		transitionBufferError = '';
		return true;
	}

	function handleAnnouncementTimeoutInput() {
		submitError = '';
		// Re-validate live only after the field has already shown an error once.
		if (announcementTimeoutError) {
			validateAnnouncementTimeout();
		}
	}

	function handleTransitionBufferInput() {
		submitError = '';
		// Re-validate live only after the field has already shown an error once.
		if (transitionBufferError) {
			validateTransitionBuffer();
		}
	}

	async function handleSubmit(event: Event) {
		event.preventDefault();
		submitError = '';

		// Validate every field so all errors surface at once, not one at a time.
		const isFestivalStartValid = validateFestivalStart();
		const isAnnouncementTimeoutValid = validateAnnouncementTimeout();
		const isTransitionBufferValid = validateTransitionBuffer();

		if (!isFestivalStartValid || !isAnnouncementTimeoutValid || !isTransitionBufferValid) {
			return;
		}

		const nextAnnouncementTimeout = announcementTimeout;
		const nextTransitionBuffer = transitionBuffer;

		if (nextAnnouncementTimeout === undefined || nextTransitionBuffer === undefined) {
			return;
		}

		isSaving = true;

		try {
			const { error, response } = await client.PATCH('/settings', {
				body: {
					voting_enabled: votingEnabled,
					festival_start: fromEventDateTimeLocal(festivalStart),
					festival_ended: festivalEnded,
					announcement_timeout: nextAnnouncementTimeout,
					transition_buffer: nextTransitionBuffer
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

			savedFestivalStart = festivalStart;
			savedFestivalEnded = festivalEnded;
			savedVotingEnabled = votingEnabled;
			savedAnnouncementTimeout = nextAnnouncementTimeout;
			savedTransitionBuffer = nextTransitionBuffer;
			festivalStartError = '';
			announcementTimeoutError = '';
			transitionBufferError = '';
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
	<title>Настройки фестиваля · ФАН ФАН</title>
</svelte:head>

<BackLink href="/tools" label="Назад к инструментам" />

<SectionIntro description="Управляй фестивалем, голосованием и таймингами расписания." />

<form class="mx-auto w-full max-w-2xl space-y-5" onsubmit={handleSubmit}>
	{#if submitError}
		<Alert color="red">
			{submitError}
		</Alert>
	{/if}

	<Card class="w-full max-w-none space-y-4 rounded-2xl p-4 sm:p-6">
		<h2 class="text-lg font-semibold text-gray-900 dark:text-white">Фестиваль</h2>

		<div class="space-y-2">
			<Label for="festival-start">Начало фестиваля (МСК)</Label>
			<Input
				id="festival-start"
				name="festival_start"
				type="datetime-local"
				autocomplete="off"
				bind:value={festivalStart}
				disabled={isSaving}
				oninput={handleFestivalStartInput}
				onblur={validateFestivalStart}
			/>
			{#if festivalStartError}
				<Helper color="red">{festivalStartError}</Helper>
			{:else}
				<Helper>
					Дата и время по московскому времени. От неё считается обратный отсчёт на главной.
				</Helper>
			{/if}
		</div>

		<div class="flex items-start justify-between gap-3">
			<div class="min-w-0">
				<h3 class="text-base font-medium text-gray-900 dark:text-white">Фестиваль завершён</h3>
				<p class="mt-1 text-xs leading-5 text-gray-500 dark:text-gray-300">
					Включи, когда фестиваль закончится — на главной вместо отсчёта появится прощание.
				</p>
			</div>
			<Toggle
				bind:checked={festivalEnded}
				color="primary"
				disabled={isSaving}
				onchange={() => (submitError = '')}
			/>
		</div>
	</Card>

	<Card class="w-full max-w-none space-y-3 rounded-2xl p-4 sm:p-6">
		<h2 class="text-lg font-semibold text-gray-900 dark:text-white">Голосование</h2>

		<div class="flex items-start justify-between gap-3">
			<div class="min-w-0">
				<h3 class="text-base font-medium text-gray-900 dark:text-white">Голосование активно</h3>
				<p class="mt-1 text-xs leading-5 text-gray-500 dark:text-gray-300">
					Если отключить эту настройку, посетители временно не смогут голосовать.
				</p>
			</div>
			<Toggle
				bind:checked={votingEnabled}
				color="primary"
				disabled={isSaving}
				onchange={() => (submitError = '')}
			/>
		</div>
	</Card>

	<Card class="w-full max-w-none space-y-4 rounded-2xl p-4 sm:p-6">
		<h2 class="text-lg font-semibold text-gray-900 dark:text-white">Программа</h2>

		<div class="space-y-2">
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

		<div class="space-y-2">
			<Label for="transition-buffer">Буфер перехода, сек</Label>
			<Input
				id="transition-buffer"
				name="transition_buffer"
				type="number"
				min="0"
				step="1"
				inputmode="numeric"
				autocomplete="off"
				bind:value={transitionBuffer}
				disabled={isSaving}
				oninput={handleTransitionBufferInput}
				onblur={validateTransitionBuffer}
			/>
			{#if transitionBufferError}
				<Helper color="red">{transitionBufferError}</Helper>
			{:else}
				<Helper>
					Запас времени между выступлениями. Учитывается при расчёте ожидаемого времени начала.
				</Helper>
			{/if}
		</div>
	</Card>

	<Button
		type="submit"
		color="primary"
		class="min-h-11 w-full justify-center sm:w-auto"
		disabled={isSaving || !hasChanges}
	>
		{#if isSaving}
			<Spinner size="4" class="mr-2 fill-white" />
			Сохраняем…
		{:else}
			Сохранить
		{/if}
	</Button>
</form>
