<script lang="ts">
	import { AlertCircle } from '@lucide/svelte';
	import { createMutation, useQueryClient } from '@tanstack/svelte-query';
	import { untrack } from 'svelte';

	import { getApiErrorDetail, getApiFieldError } from '#lib/api/errors.js';
	import {
		getPublicConfigQueryKey,
		getSettingsQueryKey,
		updateSettingsMutation
	} from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import SectionIntro from '#lib/components/SectionIntro.svelte';
	import * as Alert from '#lib/components/ui/alert/index.js';
	import { Button } from '#lib/components/ui/button/index.js';
	import * as Card from '#lib/components/ui/card/index.js';
	import * as Field from '#lib/components/ui/field/index.js';
	import { Input } from '#lib/components/ui/input/index.js';
	import { Spinner } from '#lib/components/ui/spinner/index.js';
	import { m } from '#lib/paraglide/messages.js';
	import { getToastService } from '#lib/services/toasts.svelte.js';
	import { fromEventDateTimeLocal, toEventDateTimeLocal } from '#lib/utils/formatters.js';
	import { offlineWriteGate } from '#lib/utils/offlineAction.js';

	import type { PageProps } from './$types';

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
	let submitError = $state('');

	let hasChanges = $derived(
		festivalStart !== savedFestivalStart ||
			festivalEnd !== savedFestivalEnd ||
			announcementTimeout !== savedAnnouncementTimeout
	);

	function validateFestivalStart() {
		if (!festivalStart) {
			festivalStartError = m.settings_validation_start();
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
			festivalEndError = m.settings_validation_end();
			return false;
		}

		// Guard the range: the backend stores the two instants independently with no
		// ordering check, and an end at or before the start collapses the home page's
		// "during" phase entirely — the countdown would jump straight to the farewell.
		if (festivalStart && festivalEnd <= festivalStart) {
			festivalEndError = m.error_invalid_festival_time_range();
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
			announcementTimeoutError = m.settings_validation_timeout_required();
			return false;
		}

		if (!Number.isInteger(announcementTimeout) || announcementTimeout < 1) {
			announcementTimeoutError = m.settings_validation_timeout_integer();
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

		if (!isFestivalStartValid || !isFestivalEndValid || !isAnnouncementTimeoutValid) {
			return;
		}

		const nextAnnouncementTimeout = announcementTimeout;

		if (nextAnnouncementTimeout === undefined) {
			return;
		}

		saveMutation.mutate(
			{
				body: {
					festival_start: fromEventDateTimeLocal(festivalStart),
					festival_end: fromEventDateTimeLocal(festivalEnd),
					announcement_timeout: nextAnnouncementTimeout
				}
			},
			{
				onSuccess: () => {
					savedFestivalStart = festivalStart;
					savedFestivalEnd = festivalEnd;
					savedAnnouncementTimeout = nextAnnouncementTimeout;
					festivalStartError = '';
					festivalEndError = '';
					announcementTimeoutError = '';
					toastService.add(m.settings_saved(), 'success');
				},
				onError: (error) => {
					festivalStartError = getApiFieldError(error, 'festival_start') ?? '';
					festivalEndError = getApiFieldError(error, 'festival_end') ?? '';
					announcementTimeoutError = getApiFieldError(error, 'announcement_timeout') ?? '';
					if (festivalStartError || festivalEndError || announcementTimeoutError) {
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
	class="mx-auto flex w-full max-w-2xl flex-col gap-5"
	onsubmit={offlineGate.guard(handleSubmit)}
>
	{#if submitError}
		<Alert.Root variant="destructive">
			<AlertCircle class="size-4" />
			<Alert.Description>{submitError}</Alert.Description>
		</Alert.Root>
	{/if}

	<Card.Root class="w-full max-w-none gap-4 rounded-2xl p-4 sm:p-6">
		<h2 class="text-lg font-semibold text-foreground">
			{m.settings_festival_section()}
		</h2>

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
	</Card.Root>

	<Card.Root class="w-full max-w-none gap-4 rounded-2xl p-4 sm:p-6">
		<h2 class="text-lg font-semibold text-foreground">{m.nav_schedule()}</h2>

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
	</Card.Root>

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
