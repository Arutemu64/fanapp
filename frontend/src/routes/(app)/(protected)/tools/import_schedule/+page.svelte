<script lang="ts">
	import { invalidate } from '$app/navigation';
	import { createApiClient } from '$lib/api';
	const client = createApiClient();
	import { getApiErrorDetail } from '$lib/api/errors';
	import BackLink from '$lib/components/BackLink.svelte';
	import SectionIntro from '$lib/components/SectionIntro.svelte';
	import { Alert, Button, Card, Fileupload, Helper, Label, Spinner } from 'flowbite-svelte';

	import FileFormatGuide from './components/FileFormatGuide.svelte';

	let selectedFiles = $state<FileList | null>(null);
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

	async function handleSubmit(event: Event) {
		event.preventDefault();
		const form = event.currentTarget as HTMLFormElement;
		const selectedFile = selectedFiles?.[0] ?? null;

		inlineError = '';
		successMessage = '';

		if (!selectedFile) {
			inlineError = 'Выбери Excel-файл для импорта';
			return;
		}

		isUploading = true;

		try {
			const { error, response } = await client.POST('/schedule/import', {
				body: { file: selectedFile },
				bodySerializer(body) {
					const formData = new FormData();
					formData.set('file', body.file);
					return formData;
				}
			});

			if (error || !response.ok) {
				// Mapped by the error `code`, not the status: a rejected spreadsheet
				// comes back as INVALID_SCHEDULE_FILE carrying the column and row at
				// fault, which is the whole point of showing an error here.
				inlineError = getApiErrorDetail(error) ?? 'Не удалось импортировать программу';
				return;
			}

			successMessage = 'Файл загружен. Программа обновлена.';
			selectedFiles = null;
			form.reset();

			await invalidate('app:schedule');
		} catch (submitError) {
			console.error('Schedule import failed:', submitError);
			inlineError = 'Не удалось импортировать программу';
		} finally {
			isUploading = false;
		}
	}
</script>

<svelte:head>
	<title>Импорт программы · ФАН ФАН</title>
</svelte:head>

<BackLink href="/tools" label="Назад к инструментам" />

<SectionIntro description="Загрузи Excel-файл, чтобы обновить программу мероприятия." />

<FileFormatGuide />

<Card class="mx-auto w-full max-w-2xl rounded-2xl p-4 sm:p-6">
	<form class="space-y-4" onsubmit={handleSubmit}>
		<div class="space-y-2">
			<Label for="schedule-file">Excel-файл</Label>
			<Fileupload
				id="schedule-file"
				name="schedule_file"
				accept={ACCEPTED_FILE_TYPES}
				bind:files={selectedFiles}
				clearable
				size="lg"
				class="w-full"
				disabled={isUploading}
				onchange={handleFileChange}
			/>
			<Helper class="mt-2 text-sm text-gray-500 dark:text-gray-400">
				{#if selectedFileName}
					Выбран файл: {selectedFileName}
				{:else}
					Поддерживаются файлы .xls и .xlsx.
				{/if}
			</Helper>
		</div>

		{#if inlineError}
			<Alert color="red">
				{inlineError}
			</Alert>
		{/if}

		{#if successMessage}
			<Alert color="green">
				{successMessage}
			</Alert>
		{/if}

		<Button
			type="submit"
			color="primary"
			class="min-h-11 w-full justify-center sm:w-auto"
			disabled={isUploading}
		>
			{#if isUploading}
				<Spinner size="4" class="mr-2 fill-white" />
				Импортируем…
			{:else}
				Импортировать
			{/if}
		</Button>
	</form>
</Card>
