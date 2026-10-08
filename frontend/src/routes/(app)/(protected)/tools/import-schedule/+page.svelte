<script lang="ts">
	import { invalidate } from '$app/navigation';
	import { AlertCircle, CheckCircle2 } from '@lucide/svelte';

	import { getApiErrorDetail } from '#lib/api/errors.js';
	import { importSchedule } from '#lib/api/generated/index.js';
	import { createApiClient } from '#lib/api/index.js';
	import SectionIntro from '#lib/components/SectionIntro.svelte';
	import * as Alert from '#lib/components/ui/alert/index.js';
	import { Button } from '#lib/components/ui/button/index.js';
	import * as Field from '#lib/components/ui/field/index.js';
	import { Input } from '#lib/components/ui/input/index.js';
	import { Spinner } from '#lib/components/ui/spinner/index.js';

	import ConfirmDialog from '../components/ConfirmDialog.svelte';
	import FileFormatGuide from './components/FileFormatGuide.svelte';

	const client = createApiClient();

	let formElement = $state<HTMLFormElement>();
	let confirmOpen = $state(false);
	let selectedFiles = $state<FileList | undefined>(undefined);
	let isUploading = $state(false);
	let inlineError = $state('');
	let successMessage = $state('');
	let selectedFileName = $derived(selectedFiles?.[0]?.name ?? '');

	const ACCEPTED_FILE_TYPES =
		'.xls,.xlsx,application/vnd.ms-excel,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';

	function handleFileChange() {
		inlineError = '';
		successMessage = '';
	}

	// The file replaces the whole programme and deletes acts missing from it, so
	// the upload waits for an explicit confirm naming that consequence.
	function handleSubmit(event: Event) {
		event.preventDefault();
		inlineError = '';
		successMessage = '';

		if (!selectedFiles?.[0]) {
			inlineError = 'Выбери Excel-файл для импорта';
			return;
		}

		confirmOpen = true;
	}

	async function upload() {
		const selectedFile = selectedFiles?.[0];
		if (!selectedFile || isUploading) return;

		isUploading = true;

		try {
			const { error, response } = await importSchedule({
				client,
				body: { file: selectedFile }
			});

			if (error || !response?.ok) {
				// Mapped by the error `code`, not the status: a rejected spreadsheet
				// comes back as INVALID_SCHEDULE_FILE carrying the column and row at
				// fault, which is the whole point of showing an error here.
				inlineError = getApiErrorDetail(error) ?? 'Не удалось импортировать программу';
				return;
			}

			successMessage = 'Файл загружен. Программа обновлена.';
			selectedFiles = undefined;
			formElement?.reset();

			await invalidate('app:schedule');
		} finally {
			isUploading = false;
		}
	}
</script>

<svelte:head>
	<title>Импорт программы · ФАН ФАН</title>
</svelte:head>

<SectionIntro description="Загрузи Excel-файл, чтобы обновить программу выступлений." />

<FileFormatGuide />

<div class="border-t border-border pt-6">
	<form bind:this={formElement} class="flex flex-col gap-4" onsubmit={handleSubmit}>
		<Field.Field>
			<Field.FieldLabel for="schedule-file">Excel-файл</Field.FieldLabel>
			<Input
				id="schedule-file"
				type="file"
				name="schedule_file"
				accept={ACCEPTED_FILE_TYPES}
				bind:files={selectedFiles}
				class="w-full cursor-pointer file:cursor-pointer"
				disabled={isUploading}
				onchange={handleFileChange}
			/>
			<Field.FieldDescription>
				{#if selectedFileName}
					Выбран файл: {selectedFileName}
				{:else}
					Поддерживаются файлы .xls и .xlsx.
				{/if}
			</Field.FieldDescription>
		</Field.Field>

		{#if inlineError}
			<Alert.Root variant="destructive">
				<AlertCircle />
				<Alert.Description>{inlineError}</Alert.Description>
			</Alert.Root>
		{/if}

		{#if successMessage}
			<Alert.Root variant="success">
				<CheckCircle2 />
				<Alert.Description>{successMessage}</Alert.Description>
			</Alert.Root>
		{/if}

		<Button type="submit" class="w-full sm:w-auto sm:self-start" disabled={isUploading}>
			{#if isUploading}
				<Spinner data-icon="inline-start" />
				Импортируем…
			{:else}
				Импортировать
			{/if}
		</Button>
	</form>
</div>

<ConfirmDialog
	bind:open={confirmOpen}
	title="Заменить программу?"
	description="Программа обновится из файла «{selectedFileName}». Выступления, которых в нём нет, будут удалены."
	confirmLabel="Заменить программу"
	destructive
	onconfirm={upload}
/>
