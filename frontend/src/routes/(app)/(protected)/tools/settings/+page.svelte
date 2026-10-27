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
			void queryClient.invalidateQueries({ queryKey: getSettingsQueryKey() });
			void queryClient.invalidateQueries({ queryKey: getPublicConfigQueryKey() });
		}
	}));
	let savedFestivalStart = $state(
		untrack(() => toEventDateTimeLocal(data.settings.festival_start))
	);
	let savedFestivalEnd = $state(untrack(() => toEventDateTimeLocal(data.settings.festival_end)));
	let festivalStart = $state(untrack(() => toEventDateTimeLocal(data.settings.festival_start)));
	let festivalEnd = $state(untrack(() => toEventDateTimeLocal(data.settings.festival_end)));
	let festivalStartError = $state('');
	let festivalEndError = $state('');
	let savedQuest = $state(
		untrack(() => ({
			enabled: data.settings.quest_enabled,
			max_award: data.settings.quest_max_award,
			cancel_window_minutes: data.settings.quest_cancel_window_minutes
		}))
	);
	let questEnabled = $state(untrack(() => data.settings.quest_enabled));
	let questMaxAward = $state<number | undefined>(untrack(() => data.settings.quest_max_award));
	let questCancelWindow = $state<number | undefined>(
		untrack(() => data.settings.quest_cancel_window_minutes)
	);
	let questMaxAwardError = $state('');
	let questCancelWindowError = $state('');
	let submitError = $state('');

	let hasChanges = $derived(
		festivalStart !== savedFestivalStart ||
			festivalEnd !== savedFestivalEnd ||
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
		if (festivalEndError) {
			validateFestivalEnd();
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

	const offlineGate = offlineWriteGate();

	function handleSubmit(event: Event) {
		event.preventDefault();
		submitError = '';

		const isFestivalStartValid = validateFestivalStart();
		const isFestivalEndValid = validateFestivalEnd();
		const isQuestMaxAwardValid = validateQuestMaxAward();
		const isQuestCancelWindowValid = validateQuestCancelWindow();

		if (
			!isFestivalStartValid ||
			!isFestivalEndValid ||
			!isQuestMaxAwardValid ||
			!isQuestCancelWindowValid
		) {
			return;
		}

		const nextQuestMaxAward = questMaxAward;
		const nextQuestCancelWindow = questCancelWindow;

		if (nextQuestMaxAward === undefined || nextQuestCancelWindow === undefined) {
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
					quest_enabled: nextQuest.enabled,
					quest_max_award: nextQuest.max_award,
					quest_cancel_window_minutes: nextQuest.cancel_window_minutes
				}
			},
			{
				onSuccess: () => {
					savedFestivalStart = festivalStart;
					savedFestivalEnd = festivalEnd;
					savedQuest = nextQuest;
					festivalStartError = '';
					festivalEndError = '';
					toastService.add(m.settings_saved(), 'success');
				},
				onError: (error) => {
					festivalStartError = getApiFieldError(error, 'festival_start') ?? '';
					festivalEndError = getApiFieldError(error, 'festival_end') ?? '';
					questMaxAwardError = getApiFieldError(error, 'quest_max_award') ?? '';
					questCancelWindowError = getApiFieldError(error, 'quest_cancel_window_minutes') ?? '';
					const hasFieldError =
						festivalStartError || festivalEndError || questMaxAwardError || questCancelWindowError;
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
