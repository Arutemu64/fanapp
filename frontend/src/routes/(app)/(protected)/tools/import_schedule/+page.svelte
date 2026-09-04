<script lang="ts">
	import { invalidate } from '$app/navigation';
	import { createApiClient } from '$lib/api';
	const client = createApiClient();
	import { getApiErrorDetail } from '$lib/api/errors';
	import BackLink from '$lib/components/BackLink.svelte';
	import SectionIntro from '$lib/components/SectionIntro.svelte';
	import * as Alert from '$lib/components/ui/alert';
	import { Button } from '$lib/components/ui/button';
	import * as Card from '$lib/components/ui/card';
	import * as Field from '$lib/components/ui/field';
	import { Input } from '$lib/components/ui/input';
	import { Spinner } from '$lib/components/ui/spinner';
	import { AlertCircle, CheckCircle2 } from '@lucide/svelte';

	import FileFormatGuide from './components/FileFormatGuide.svelte';

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
			selectedFiles = undefined;
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

<Card.Root class="mx-auto w-full max-w-2xl rounded-2xl p-4 sm:p-6">
	<form class="flex flex-col gap-4" onsubmit={handleSubmit}>
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
				<AlertCircle class="size-4" />
				<Alert.Description>{inlineError}</Alert.Description>
			</Alert.Root>
		{/if}

		{#if successMessage}
			<Alert.Root variant="success">
				<CheckCircle2 />
				<Alert.Description>{successMessage}</Alert.Description>
			</Alert.Root>
		{/if}

		<Button type="submit" class="min-h-11 w-full justify-center sm:w-auto" disabled={isUploading}>
			{#if isUploading}
				<Spinner data-icon="inline-start" />
				Импортируем…
			{:else}
				Импортировать
			{/if}
		</Button>
	</form>
</Card.Root>
