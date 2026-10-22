<script lang="ts">
	import CircleCheck from '@lucide/svelte/icons/circle-check';
	import { createMutation, useQueryClient } from '@tanstack/svelte-query';

	import { getApiErrorDetail } from '#lib/api/errors.js';
	import {
		getScheduleQueryKey,
		importScheduleMutation
	} from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import FormError from '#lib/components/FormError.svelte';
	import * as Alert from '#lib/components/ui/alert/index.js';
	import { Button } from '#lib/components/ui/button/index.js';
	import * as Field from '#lib/components/ui/field/index.js';
	import { Input } from '#lib/components/ui/input/index.js';
	import { Spinner } from '#lib/components/ui/spinner/index.js';
	import { m } from '#lib/paraglide/messages.js';
	import { offlineWriteGate } from '#lib/utils/offlineAction.js';

	import FileFormatGuide from './FileFormatGuide.svelte';

	const queryClient = useQueryClient();

	const importMutation = createMutation(() => ({
		...importScheduleMutation(),
		onSuccess: () => queryClient.invalidateQueries({ queryKey: getScheduleQueryKey() })
	}));

	let selectedFiles = $state<FileList | undefined>(undefined);
	let inlineError = $state('');
	let successMessage = $state('');
	let selectedFileName = $derived(selectedFiles?.[0]?.name ?? '');

	const ACCEPTED_FILE_TYPES =
		'.xls,.xlsx,application/vnd.ms-excel,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';

	function handleFileChange() {
		inlineError = '';
		successMessage = '';
	}

	// A connection that drops mid-form keeps what was typed; the submit explains
	// itself instead of sending.
	const offlineGate = offlineWriteGate();

	function handleSubmit(event: Event) {
		event.preventDefault();
		const form = event.currentTarget as HTMLFormElement;
		const selectedFile = selectedFiles?.[0] ?? null;

		inlineError = '';
		successMessage = '';

		if (!selectedFile) {
			inlineError = m.import_validation_file();
			return;
		}

		importMutation.mutate(
			{ body: { file: selectedFile } },
			{
				onSuccess: () => {
					successMessage = m.import_done();
					selectedFiles = undefined;
					form.reset();
				},
				onError: (error) => {
					// Mapped by the error `code`, not the status: a rejected spreadsheet
					// comes back as INVALID_SCHEDULE_FILE carrying the column and row at
					// fault, which is the whole point of showing an error here.
					inlineError = getApiErrorDetail(error) ?? m.import_failed();
				}
			}
		);
	}
</script>

<div>
	<FileFormatGuide />

	<div class="border-t border-border pt-6">
		<form class="flex flex-col gap-4" onsubmit={offlineGate.guard(handleSubmit)}>
			<Field.Field>
				<Field.FieldLabel for="schedule-file">{m.import_file_label()}</Field.FieldLabel>
				<Input
					id="schedule-file"
					type="file"
					name="schedule_file"
					accept={ACCEPTED_FILE_TYPES}
					bind:files={selectedFiles}
					class="w-full cursor-pointer file:cursor-pointer"
					disabled={importMutation.isPending}
					onchange={handleFileChange}
				/>
				<Field.FieldDescription>
					{#if selectedFileName}
						{m.import_selected_file({ name: selectedFileName })}
					{:else}
						{m.import_formats_hint()}
					{/if}
				</Field.FieldDescription>
			</Field.Field>

			<FormError message={inlineError} />

			{#if successMessage}
				<Alert.Root variant="success">
					<CircleCheck />
					<Alert.Description>{successMessage}</Alert.Description>
				</Alert.Root>
			{/if}

			<Button
				type="submit"
				class="w-full sm:w-auto"
				disabled={importMutation.isPending}
				aria-disabled={offlineGate.blocked}
			>
				{#if importMutation.isPending}
					<Spinner data-icon="inline-start" />
					{m.import_importing()}
				{:else}
					{m.import_action()}
				{/if}
			</Button>
		</form>
	</div>
</div>
