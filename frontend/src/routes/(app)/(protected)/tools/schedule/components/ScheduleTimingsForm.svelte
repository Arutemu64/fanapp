<script lang="ts">
	import { createMutation, useQueryClient } from '@tanstack/svelte-query';
	import { untrack } from 'svelte';

	import type { ScheduleSettingsDto } from '#lib/api/generated/index.js';

	import { getApiErrorDetail, getApiFieldError } from '#lib/api/errors.js';
	import {
		getPublicConfigQueryKey,
		getScheduleSettingsQueryKey,
		updateScheduleSettingsMutation
	} from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import FormError from '#lib/components/FormError.svelte';
	import { Button } from '#lib/components/ui/button/index.js';
	import * as Field from '#lib/components/ui/field/index.js';
	import { Input } from '#lib/components/ui/input/index.js';
	import { Spinner } from '#lib/components/ui/spinner/index.js';
	import { m } from '#lib/paraglide/messages.js';
	import { getToastService } from '#lib/services/toasts.svelte.js';
	import { offlineWriteGate } from '#lib/utils/offlineAction.js';

	import {
		CHANGEOVER_SECONDS_LIMIT,
		checkAnnouncementTimeout,
		checkChangeover
	} from '../timingsValidation';

	interface Props {
		initial: ScheduleSettingsDto;
	}

	let { initial }: Props = $props();

	const toastService = getToastService();
	const queryClient = useQueryClient();

	const saveMutation = createMutation(() => ({
		...updateScheduleSettingsMutation(),
		onSuccess: () => {
			void queryClient.invalidateQueries({ queryKey: getScheduleSettingsQueryKey() });
			void queryClient.invalidateQueries({ queryKey: getPublicConfigQueryKey() });
		}
	}));

	let saved = $state(untrack(() => ({ ...initial })));
	let announcementTimeout = $state<number | undefined>(untrack(() => initial.announcement_timeout));
	let changeover = $state<number | undefined>(untrack(() => initial.changeover_seconds));
	let announcementTimeoutError = $state('');
	let changeoverError = $state('');
	let submitError = $state('');

	let hasChanges = $derived(
		announcementTimeout !== saved.announcement_timeout || changeover !== saved.changeover_seconds
	);

	function validateAnnouncementTimeout() {
		announcementTimeoutError = checkAnnouncementTimeout(announcementTimeout);
		return !announcementTimeoutError;
	}

	function handleAnnouncementTimeoutInput() {
		submitError = '';
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

	const offlineGate = offlineWriteGate();

	function handleSubmit(event: Event) {
		event.preventDefault();
		submitError = '';

		const isAnnouncementTimeoutValid = validateAnnouncementTimeout();
		const isChangeoverValid = validateChangeover();
		if (!isAnnouncementTimeoutValid || !isChangeoverValid) {
			return;
		}
		if (announcementTimeout === undefined || changeover === undefined) {
			return;
		}

		const next = { announcement_timeout: announcementTimeout, changeover_seconds: changeover };
		saveMutation.mutate(
			{ body: next },
			{
				onSuccess: () => {
					saved = next;
					toastService.add(m.schedule_timings_saved(), 'success');
				},
				onError: (error) => {
					announcementTimeoutError = getApiFieldError(error, 'announcement_timeout') ?? '';
					changeoverError = getApiFieldError(error, 'changeover_seconds') ?? '';
					if (announcementTimeoutError || changeoverError) {
						return;
					}
					submitError = getApiErrorDetail(error) ?? m.schedule_timings_save_failed();
				}
			}
		);
	}
</script>

<form novalidate class="flex flex-col gap-4" onsubmit={offlineGate.guard(handleSubmit)}>
	<FormError message={submitError} />

	<Field.FieldGroup class="gap-4">
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
				<Field.FieldDescription>{m.settings_timeout_hint()}</Field.FieldDescription>
			{/if}
		</Field.Field>

		<Field.Field data-invalid={changeoverError ? true : undefined}>
			<Field.FieldLabel for="changeover">{m.settings_changeover_label()}</Field.FieldLabel>
			<Input
				id="changeover"
				name="changeover_seconds"
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
	</Field.FieldGroup>

	<Button
		type="submit"
		class="w-full sm:w-auto sm:self-start"
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
