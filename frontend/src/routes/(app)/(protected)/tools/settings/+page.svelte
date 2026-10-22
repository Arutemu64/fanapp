<script lang="ts">
	import { createMutation, useQueryClient } from '@tanstack/svelte-query';
	import { untrack } from 'svelte';

	import { getApiErrorDetail, getApiFieldError } from '#lib/api/errors.js';
	import {
		getPublicConfigQueryKey,
		getSettingsQueryKey,
		updateSettingsMutation
	} from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import FormError from '#lib/components/FormError.svelte';
	import SectionIntro from '#lib/components/SectionIntro.svelte';
	import { Button } from '#lib/components/ui/button/index.js';
	import * as Field from '#lib/components/ui/field/index.js';
	import { Input } from '#lib/components/ui/input/index.js';
	import { Spinner } from '#lib/components/ui/spinner/index.js';
	import { Switch } from '#lib/components/ui/switch/index.js';
	import { m } from '#lib/paraglide/messages.js';
	import { getToastService } from '#lib/services/toasts.svelte.js';
	import { fromEventDateTimeLocal, toEventDateTimeLocal } from '#lib/utils/formatters.js';
	import { offlineWriteGate } from '#lib/utils/offlineAction.js';

	import type { PageProps } from './$types';

	import ToolSection from '../components/ToolSection.svelte';
	import {
		CHANGEOVER_SECONDS_LIMIT,
		checkAnnouncementTimeout,
		checkChangeover,
		checkFestivalEnd,
		checkFestivalStart,
		checkQuestCancelWindow,
		checkQuestMaxAward,
		QUEST_CANCEL_WINDOW_LIMIT,
		QUEST_MAX_AWARD_LIMIT
	} from './settingsValidation';

	let { data }: PageProps = $props();
	const toastService = getToastService();
	const queryClient = useQueryClient();

	const saveMutation = createMutation(() => ({
		...updateSettingsMutation(),
		onSuccess: () => {
			// The festival dates are public config too; config_updated would refresh it,
			// but not before this organizer looks at the home hero.
			void queryClient.invalidateQueries({ queryKey: getSettingsQueryKey() });
			void queryClient.invalidateQueries({ queryKey: getPublicConfigQueryKey() });
		}
	}));
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
	let savedChangeover = $state(untrack(() => data.settings.schedule.changeover_seconds));
	let changeover = $state<number | undefined>(
		untrack(() => data.settings.schedule.changeover_seconds)
	);
	let changeoverError = $state('');
	let savedQuest = $state(untrack(() => ({ ...data.settings.quest })));
	let questEnabled = $state(untrack(() => data.settings.quest.enabled));
	let questMaxAward = $state<number | undefined>(untrack(() => data.settings.quest.max_award));
	let questCancelWindow = $state<number | undefined>(
		untrack(() => data.settings.quest.cancel_window_minutes)
	);
	let questMaxAwardError = $state('');
	let questCancelWindowError = $state('');
	let submitError = $state('');

	let hasChanges = $derived(
		festivalStart !== savedFestivalStart ||
			festivalEnd !== savedFestivalEnd ||
			announcementTimeout !== savedAnnouncementTimeout ||
			changeover !== savedChangeover ||
			questEnabled !== savedQuest.enabled ||
			questMaxAward !== savedQuest.max_award ||
			questCancelWindow !== savedQuest.cancel_window_minutes
	);

	function validateFestivalStart() {
		festivalStartError = checkFestivalStart(festivalStart);
		return !festivalStartError;
	}

	function handleFestivalStartInput() {
		submitError = '';
		// Re-validate live only after the field has already shown an error once.
		if (festivalStartError) {
			validateFestivalStart();
		}
	}

	function validateFestivalEnd() {
		festivalEndError = checkFestivalEnd(festivalStart, festivalEnd);
		return !festivalEndError;
	}

	function handleFestivalEndInput() {
		submitError = '';
		// Re-validate live only after the field has already shown an error once.
		if (festivalEndError) {
			validateFestivalEnd();
		}
	}

	function validateAnnouncementTimeout() {
		announcementTimeoutError = checkAnnouncementTimeout(announcementTimeout);
		return !announcementTimeoutError;
	}

	function handleAnnouncementTimeoutInput() {
		submitError = '';
		// Re-validate live only after the field has already shown an error once.
		if (announcementTimeoutError) {
			validateAnnouncementTimeout();
		}
	}

	function validateChangeover() {
		changeoverError = checkChangeover(changeover);
		return !changeoverError;
	}

	function handleChangeoverInput() {
		submitError = '';
		if (changeoverError) {
			validateChangeover();
		}
	}

	function validateQuestMaxAward() {
		questMaxAwardError = checkQuestMaxAward(questMaxAward);
		return !questMaxAwardError;
	}

	function validateQuestCancelWindow() {
		questCancelWindowError = checkQuestCancelWindow(questCancelWindow);
		return !questCancelWindowError;
	}

	function handleQuestMaxAwardInput() {
		submitError = '';
		if (questMaxAwardError) {
			validateQuestMaxAward();
		}
	}

	function handleQuestCancelWindowInput() {
		submitError = '';
		if (questCancelWindowError) {
			validateQuestCancelWindow();
		}
	}

	// A connection that drops mid-form keeps what was typed; the submit explains
	// itself instead of sending.
	const offlineGate = offlineWriteGate();

	function handleSubmit(event: Event) {
		event.preventDefault();
		submitError = '';

		// Validate every field so all errors surface at once, not one at a time.
		const isFestivalStartValid = validateFestivalStart();
		const isFestivalEndValid = validateFestivalEnd();
		const isAnnouncementTimeoutValid = validateAnnouncementTimeout();
		const isChangeoverValid = validateChangeover();
		const isQuestMaxAwardValid = validateQuestMaxAward();
		const isQuestCancelWindowValid = validateQuestCancelWindow();

		if (
			!isFestivalStartValid ||
			!isFestivalEndValid ||
			!isAnnouncementTimeoutValid ||
			!isChangeoverValid ||
			!isQuestMaxAwardValid ||
			!isQuestCancelWindowValid
		) {
			return;
		}

		const nextAnnouncementTimeout = announcementTimeout;
		const nextChangeover = changeover;
		const nextQuestMaxAward = questMaxAward;
		const nextQuestCancelWindow = questCancelWindow;

		if (
			nextAnnouncementTimeout === undefined ||
			nextChangeover === undefined ||
			nextQuestMaxAward === undefined ||
			nextQuestCancelWindow === undefined
		) {
			return;
		}
		const nextQuest = {
			enabled: questEnabled,
			max_award: nextQuestMaxAward,
			cancel_window_minutes: nextQuestCancelWindow
		};

		saveMutation.mutate(
			{
				body: {
					festival_start: fromEventDateTimeLocal(festivalStart),
					festival_end: fromEventDateTimeLocal(festivalEnd),
					announcement_timeout: nextAnnouncementTimeout,
					schedule_changeover_seconds: nextChangeover,
					quest_enabled: nextQuest.enabled,
					quest_max_award: nextQuest.max_award,
					quest_cancel_window_minutes: nextQuest.cancel_window_minutes
				}
			},
			{
				onSuccess: () => {
					savedFestivalStart = festivalStart;
					savedFestivalEnd = festivalEnd;
					savedAnnouncementTimeout = nextAnnouncementTimeout;
					savedChangeover = nextChangeover;
					savedQuest = nextQuest;
					festivalStartError = '';
					festivalEndError = '';
					announcementTimeoutError = '';
					changeoverError = '';
					toastService.add(m.settings_saved(), 'success');
				},
				onError: (error) => {
					festivalStartError = getApiFieldError(error, 'festival_start') ?? '';
					festivalEndError = getApiFieldError(error, 'festival_end') ?? '';
					announcementTimeoutError = getApiFieldError(error, 'announcement_timeout') ?? '';
					changeoverError = getApiFieldError(error, 'schedule_changeover_seconds') ?? '';
					questMaxAwardError = getApiFieldError(error, 'quest_max_award') ?? '';
					questCancelWindowError = getApiFieldError(error, 'quest_cancel_window_minutes') ?? '';
					const hasFieldError =
						festivalStartError ||
						festivalEndError ||
						announcementTimeoutError ||
						changeoverError ||
						questMaxAwardError ||
						questCancelWindowError;
					if (hasFieldError) {
						return;
					}
					submitError = getApiErrorDetail(error) ?? m.settings_save_failed();
				}
			}
		);
	}
</script>

<svelte:head>
	<title>{m.document_title({ title: m.tool_settings() })}</title>
</svelte:head>

<SectionIntro description={m.settings_description()} />

<!-- novalidate: the browser's own bubble for min/max would pre-empt the Russian
     field errors with English text; the validate* functions cover the same bounds. -->
<form
	novalidate
	class="mx-auto flex w-full max-w-2xl flex-col gap-5"
	onsubmit={offlineGate.guard(handleSubmit)}
>
	<FormError message={submitError} />

	<ToolSection title={m.settings_festival_section()}>
		<Field.FieldGroup class="gap-4">
			<Field.Field data-invalid={festivalStartError ? true : undefined}>
				<Field.FieldLabel for="festival-start">{m.settings_start_label()}</Field.FieldLabel>
				<Input
					id="festival-start"
					name="festival_start"
					type="datetime-local"
					autocomplete="off"
					bind:value={festivalStart}
					disabled={saveMutation.isPending}
					oninput={handleFestivalStartInput}
					onblur={validateFestivalStart}
					aria-invalid={festivalStartError ? true : undefined}
				/>
				{#if festivalStartError}
					<Field.FieldError>{festivalStartError}</Field.FieldError>
				{:else}
					<Field.FieldDescription>
						{m.settings_start_hint()}
					</Field.FieldDescription>
				{/if}
			</Field.Field>

			<Field.Field data-invalid={festivalEndError ? true : undefined}>
				<Field.FieldLabel for="festival-end">{m.settings_end_label()}</Field.FieldLabel>
				<Input
					id="festival-end"
					name="festival_end"
					type="datetime-local"
					autocomplete="off"
					bind:value={festivalEnd}
					disabled={saveMutation.isPending}
					oninput={handleFestivalEndInput}
					onblur={validateFestivalEnd}
					aria-invalid={festivalEndError ? true : undefined}
				/>
				{#if festivalEndError}
					<Field.FieldError>{festivalEndError}</Field.FieldError>
				{:else}
					<Field.FieldDescription>
						{m.settings_end_hint()}
					</Field.FieldDescription>
				{/if}
			</Field.Field>
		</Field.FieldGroup>
	</ToolSection>

	<ToolSection title={m.nav_schedule()}>
		<Field.Field data-invalid={announcementTimeoutError ? true : undefined}>
			<Field.FieldLabel for="announcement-timeout">{m.settings_timeout_label()}</Field.FieldLabel>
			<Input
				id="announcement-timeout"
				name="announcement_timeout"
				type="number"
				min="1"
				step="1"
				inputmode="numeric"
				autocomplete="off"
				bind:value={announcementTimeout}
				disabled={saveMutation.isPending}
				oninput={handleAnnouncementTimeoutInput}
				onblur={validateAnnouncementTimeout}
				aria-invalid={announcementTimeoutError ? true : undefined}
			/>
			{#if announcementTimeoutError}
				<Field.FieldError>{announcementTimeoutError}</Field.FieldError>
			{:else}
				<Field.FieldDescription>
					{m.settings_timeout_hint()}
				</Field.FieldDescription>
			{/if}
		</Field.Field>

		<Field.Field data-invalid={changeoverError ? true : undefined}>
			<Field.FieldLabel for="changeover">{m.settings_changeover_label()}</Field.FieldLabel>
			<Input
				id="changeover"
				name="schedule_changeover_seconds"
				type="number"
				min="0"
				max={CHANGEOVER_SECONDS_LIMIT}
				step="1"
				inputmode="numeric"
				autocomplete="off"
				bind:value={changeover}
				disabled={saveMutation.isPending}
				oninput={handleChangeoverInput}
				onblur={validateChangeover}
				aria-invalid={changeoverError ? true : undefined}
			/>
			{#if changeoverError}
				<Field.FieldError>{changeoverError}</Field.FieldError>
			{:else}
				<Field.FieldDescription>{m.settings_changeover_hint()}</Field.FieldDescription>
			{/if}
		</Field.Field>
	</ToolSection>

	<ToolSection title={m.quest_title()}>
		<Field.FieldGroup class="gap-4">
			<Field.Field orientation="horizontal">
				<Field.FieldContent>
					<Field.FieldLabel for="quest-enabled">{m.settings_quest_enabled_label()}</Field.FieldLabel
					>
					<Field.FieldDescription>{m.settings_quest_enabled_hint()}</Field.FieldDescription>
				</Field.FieldContent>
				<Switch
					id="quest-enabled"
					bind:checked={questEnabled}
					disabled={saveMutation.isPending}
					onCheckedChange={() => (submitError = '')}
				/>
			</Field.Field>

			<Field.Field data-invalid={questMaxAwardError ? true : undefined}>
				<Field.FieldLabel for="quest-max-award">{m.settings_quest_max_label()}</Field.FieldLabel>
				<Input
					id="quest-max-award"
					name="quest_max_award"
					type="number"
					min="1"
					max={QUEST_MAX_AWARD_LIMIT}
					step="1"
					inputmode="numeric"
					autocomplete="off"
					bind:value={questMaxAward}
					disabled={saveMutation.isPending}
					oninput={handleQuestMaxAwardInput}
					onblur={validateQuestMaxAward}
					aria-invalid={questMaxAwardError ? true : undefined}
				/>
				{#if questMaxAwardError}
					<Field.FieldError>{questMaxAwardError}</Field.FieldError>
				{:else}
					<Field.FieldDescription>{m.settings_quest_max_hint()}</Field.FieldDescription>
				{/if}
			</Field.Field>

			<Field.Field data-invalid={questCancelWindowError ? true : undefined}>
				<Field.FieldLabel for="quest-cancel-window">
					{m.settings_quest_window_label()}
				</Field.FieldLabel>
				<Input
					id="quest-cancel-window"
					name="quest_cancel_window_minutes"
					type="number"
					min="0"
					max={QUEST_CANCEL_WINDOW_LIMIT}
					step="1"
					inputmode="numeric"
					autocomplete="off"
					bind:value={questCancelWindow}
					disabled={saveMutation.isPending}
					oninput={handleQuestCancelWindowInput}
					onblur={validateQuestCancelWindow}
					aria-invalid={questCancelWindowError ? true : undefined}
				/>
				{#if questCancelWindowError}
					<Field.FieldError>{questCancelWindowError}</Field.FieldError>
				{:else}
					<Field.FieldDescription>{m.settings_quest_window_hint()}</Field.FieldDescription>
				{/if}
			</Field.Field>
		</Field.FieldGroup>
	</ToolSection>

	<Button
		type="submit"
		class="w-full sm:w-auto"
		disabled={saveMutation.isPending || !hasChanges}
		aria-disabled={offlineGate.blocked}
	>
		{#if saveMutation.isPending}
			<Spinner data-icon="inline-start" />
			{m.common_saving()}
		{:else}
			{m.common_save()}
		{/if}
	</Button>
</form>
