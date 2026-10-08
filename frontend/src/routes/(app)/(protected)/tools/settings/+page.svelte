<script lang="ts">
	import { invalidate } from '$app/navigation';
	import { AlertCircle } from '@lucide/svelte';
	import { untrack } from 'svelte';

	import { getApiErrorDetail, getApiFieldError } from '#lib/api/errors.js';
	import { updateSettings } from '#lib/api/generated/index.js';
	import { createApiClient } from '#lib/api/index.js';
	import SectionIntro from '#lib/components/SectionIntro.svelte';
	import SettingsSection from '#lib/components/SettingsSection.svelte';
	import * as Alert from '#lib/components/ui/alert/index.js';
	import { Button } from '#lib/components/ui/button/index.js';
	import * as Field from '#lib/components/ui/field/index.js';
	import { Input } from '#lib/components/ui/input/index.js';
	import { Spinner } from '#lib/components/ui/spinner/index.js';
	import { getToastService } from '#lib/services/toasts.svelte.js';
	import { fromEventDateTimeLocal, toEventDateTimeLocal } from '#lib/utils/formatters.js';

	import type { PageProps } from './$types';

	let { data }: PageProps = $props();
	const client = createApiClient();
	const toastService = getToastService();

	let isSaving = $state(false);
	// festival_start and festival_end are instants; edit them on the venue clock
	// via zone-naive datetime-locals, converting back to ISO instants on save.
	let festivalStart = $state(untrack(() => toEventDateTimeLocal(data.settings.festival_start)));
	let festivalEnd = $state(untrack(() => toEventDateTimeLocal(data.settings.festival_end)));
	let festivalStartError = $state('');
	let festivalEndError = $state('');
	let announcementTimeout = $state<number | undefined>(
		untrack(() => data.settings.limits.announcement_timeout)
	);
	let announcementTimeoutError = $state('');
	let submitError = $state('');

	function validateFestivalStart() {
		if (!festivalStart) {
			festivalStartError = 'Укажи дату и время начала фестиваля';
			return false;
		}

		festivalStartError = '';
		return true;
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

	// Errors appear on submit, not on blur, and clear once the field is corrected
	// (GOV.UK validation pattern: https://design-system.service.gov.uk/patterns/validation/).
	function handleFestivalStartInput() {
		submitError = '';
		if (festivalStartError) {
			validateFestivalStart();
		}
	}

	function handleFestivalEndInput() {
		submitError = '';
		if (festivalEndError) {
			validateFestivalEnd();
		}
	}

	function handleAnnouncementTimeoutInput() {
		submitError = '';
		if (announcementTimeoutError) {
			validateAnnouncementTimeout();
		}
	}

	async function handleSubmit(event: Event) {
		event.preventDefault();
		if (isSaving) return;
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
			const { error, response } = await updateSettings({
				client,
				body: {
					festival_start: fromEventDateTimeLocal(festivalStart),
					festival_end: fromEventDateTimeLocal(festivalEnd),
					announcement_timeout: nextAnnouncementTimeout
				}
			});

			if (error || !response?.ok) {
				festivalStartError = getApiFieldError(error, 'festival_start') ?? '';
				festivalEndError = getApiFieldError(error, 'festival_end') ?? '';
				announcementTimeoutError = getApiFieldError(error, 'announcement_timeout') ?? '';
				if (festivalStartError || festivalEndError || announcementTimeoutError) {
					return;
				}
				submitError = getApiErrorDetail(error) ?? 'Не удалось сохранить настройки фестиваля';
				return;
			}

			toastService.add('Настройки фестиваля сохранены', 'success');
			await invalidate('app:festival-settings');
		} finally {
			isSaving = false;
		}
	}
</script>

<svelte:head>
	<title>Настройки фестиваля · ФАН ФАН</title>
</svelte:head>

<SectionIntro description="Управляй датами фестиваля и таймингами программы." />

<!-- novalidate: the browser's own bubble for the number field's min would block
     submit in the browser's language and pre-empt the Russian message below. The
     fields go read-only, not disabled, while saving, so focus and the phone
     keyboard stay put. -->
<form novalidate class="flex flex-col gap-6" onsubmit={handleSubmit}>
	{#if submitError}
		<Alert.Root variant="destructive">
			<AlertCircle />
			<Alert.Description>{submitError}</Alert.Description>
		</Alert.Root>
	{/if}

	<SettingsSection title="Фестиваль">
		<Field.FieldGroup class="gap-4">
			<Field.Field data-invalid={festivalStartError ? true : undefined}>
				<Field.FieldLabel for="festival-start">Начало фестиваля (МСК)</Field.FieldLabel>
				<Input
					id="festival-start"
					name="festival_start"
					type="datetime-local"
					autocomplete="off"
					bind:value={festivalStart}
					readonly={isSaving}
					oninput={handleFestivalStartInput}
					aria-invalid={festivalStartError ? true : undefined}
				/>
				{#if festivalStartError}
					<Field.FieldError>{festivalStartError}</Field.FieldError>
				{:else}
					<Field.FieldDescription>
						От этой даты считается обратный отсчёт на главной.
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
					readonly={isSaving}
					oninput={handleFestivalEndInput}
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
	</SettingsSection>

	<SettingsSection title="Программа">
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
				readonly={isSaving}
				oninput={handleAnnouncementTimeoutInput}
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
	</SettingsSection>

	<Button type="submit" class="w-full sm:w-auto sm:self-start" disabled={isSaving}>
		{#if isSaving}
			<Spinner data-icon="inline-start" />
			Сохраняем…
		{:else}
			Сохранить
		{/if}
	</Button>
</form>
