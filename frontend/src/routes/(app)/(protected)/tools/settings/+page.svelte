<script lang="ts">
	import { invalidate } from '$app/navigation';
	import { createApiClient } from '$lib/api';
	const client = createApiClient();
	import BackLink from '$lib/components/BackLink.svelte';
	import SectionIntro from '$lib/components/SectionIntro.svelte';
	import * as Alert from '$lib/components/ui/alert';
	import { Button } from '$lib/components/ui/button';
	import * as Card from '$lib/components/ui/card';
	import * as Field from '$lib/components/ui/field';
	import { Input } from '$lib/components/ui/input';
	import { Spinner } from '$lib/components/ui/spinner';
	import { getToastService } from '$lib/services/toasts.svelte';
	import { fromEventDateTimeLocal, toEventDateTimeLocal } from '$lib/utils/formatters';
	import { AlertCircle } from '@lucide/svelte';
	import { untrack } from 'svelte';

	import type { PageProps } from './$types';

	let { data }: PageProps = $props();
	const toastService = getToastService();

	let isSaving = $state(false);
	// festival_start and festival_end are instants; edit them on the venue clock
	// via zone-naive datetime-locals, converting back to ISO instants on save.
	let savedFestivalStart = $state(
		untrack(() => toEventDateTimeLocal(data.settings.festival_start))
	);
	let savedFestivalEnd = $state(untrack(() => toEventDateTimeLocal(data.settings.festival_end)));
	let festivalStart = $state(untrack(() => toEventDateTimeLocal(data.settings.festival_start)));
	let festivalEnd = $state(untrack(() => toEventDateTimeLocal(data.settings.festival_end)));
	let festivalStartError = $state('');
	let festivalEndError = $state('');
	let savedAnnouncementTimeout = $state(untrack(() => data.settings.limits.announcement_timeout));
	let announcementTimeout = $state<number | undefined>(
		untrack(() => data.settings.limits.announcement_timeout)
	);
	let announcementTimeoutError = $state('');
	let submitError = $state('');

	let hasChanges = $derived(
		festivalStart !== savedFestivalStart ||
			festivalEnd !== savedFestivalEnd ||
			announcementTimeout !== savedAnnouncementTimeout
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

	function validateFestivalEnd() {
		if (!festivalEnd) {
			festivalEndError = 'Укажи дату и время конца фестиваля';
			return false;
		}

		// Guard the range: the backend stores the two instants independently with no
		// ordering check, and an end at or before the start collapses the home page's
		// "during" phase entirely — the countdown would jump straight to the farewell.
		if (festivalStart && festivalEnd <= festivalStart) {
			festivalEndError = 'Конец фестиваля должен быть позже начала';
			return false;
		}

		festivalEndError = '';
		return true;
	}

	function handleFestivalEndInput() {
		submitError = '';
		// Re-validate live only after the field has already shown an error once.
		if (festivalEndError) {
			validateFestivalEnd();
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

		// Validate every field so all errors surface at once, not one at a time.
		const isFestivalStartValid = validateFestivalStart();
		const isFestivalEndValid = validateFestivalEnd();
		const isAnnouncementTimeoutValid = validateAnnouncementTimeout();

		if (!isFestivalStartValid || !isFestivalEndValid || !isAnnouncementTimeoutValid) {
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
					festival_start: fromEventDateTimeLocal(festivalStart),
					festival_end: fromEventDateTimeLocal(festivalEnd),
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

			savedFestivalStart = festivalStart;
			savedFestivalEnd = festivalEnd;
			savedAnnouncementTimeout = nextAnnouncementTimeout;
			festivalStartError = '';
			festivalEndError = '';
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
	<title>Настройки фестиваля · ФАН ФАН</title>
</svelte:head>

<BackLink href="/tools" label="Назад к инструментам" />

<SectionIntro description="Управляй датами фестиваля и таймингами расписания." />

<form class="mx-auto flex w-full max-w-2xl flex-col gap-5" onsubmit={handleSubmit}>
	{#if submitError}
		<Alert.Root variant="destructive">
			<AlertCircle class="size-4" />
			<Alert.Description>{submitError}</Alert.Description>
		</Alert.Root>
	{/if}

	<Card.Root class="flex w-full max-w-none flex-col gap-4 rounded-2xl p-4 sm:p-6">
		<h2 class="text-lg font-semibold text-foreground">Фестиваль</h2>

		<Field.FieldGroup class="gap-4">
			<Field.Field data-invalid={festivalStartError ? true : undefined}>
				<Field.FieldLabel for="festival-start">Начало фестиваля (МСК)</Field.FieldLabel>
				<Input
					id="festival-start"
					name="festival_start"
					type="datetime-local"
					autocomplete="off"
					bind:value={festivalStart}
					disabled={isSaving}
					oninput={handleFestivalStartInput}
					onblur={validateFestivalStart}
					aria-invalid={festivalStartError ? true : undefined}
				/>
				{#if festivalStartError}
					<Field.FieldError>{festivalStartError}</Field.FieldError>
				{:else}
					<Field.FieldDescription>
						Дата и время по московскому времени. От неё считается обратный отсчёт на главной.
					</Field.FieldDescription>
				{/if}
			</Field.Field>

			<Field.Field data-invalid={festivalEndError ? true : undefined}>
				<Field.FieldLabel for="festival-end">Конец фестиваля (МСК)</Field.FieldLabel>
				<Input
					id="festival-end"
					name="festival_end"
					type="datetime-local"
					autocomplete="off"
					bind:value={festivalEnd}
					disabled={isSaving}
					oninput={handleFestivalEndInput}
					onblur={validateFestivalEnd}
					aria-invalid={festivalEndError ? true : undefined}
				/>
				{#if festivalEndError}
					<Field.FieldError>{festivalEndError}</Field.FieldError>
				{:else}
					<Field.FieldDescription>
						После него на главной вместо отсчёта появится прощание. Сдвинь позже, если фестиваль
						затянулся.
					</Field.FieldDescription>
				{/if}
			</Field.Field>
		</Field.FieldGroup>
	</Card.Root>

	<Card.Root class="flex w-full max-w-none flex-col gap-4 rounded-2xl p-4 sm:p-6">
		<h2 class="text-lg font-semibold text-foreground">Программа</h2>

		<Field.Field data-invalid={announcementTimeoutError ? true : undefined}>
			<Field.FieldLabel for="announcement-timeout">Таймаут анонсов, сек</Field.FieldLabel>
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
				aria-invalid={announcementTimeoutError ? true : undefined}
			/>
			{#if announcementTimeoutError}
				<Field.FieldError>{announcementTimeoutError}</Field.FieldError>
			{:else}
				<Field.FieldDescription>
					Минимум 1 секунда. Ограничение помогает не отправлять анонсы слишком часто.
				</Field.FieldDescription>
			{/if}
		</Field.Field>
	</Card.Root>

	<Button
		type="submit"
		class="min-h-11 w-full justify-center sm:w-auto"
		disabled={isSaving || !hasChanges}
	>
		{#if isSaving}
			<Spinner data-icon="inline-start" />
			Сохраняем…
		{:else}
			Сохранить
		{/if}
	</Button>
</form>
