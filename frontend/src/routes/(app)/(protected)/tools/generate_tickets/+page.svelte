<script lang="ts">
	import { createApiClient } from '$lib/api';
	const client = createApiClient();
	import SectionIntro from '$lib/components/SectionIntro.svelte';
	import { getToastService } from '$lib/services/toasts.svelte';
	import {
		Alert,
		Button,
		Card,
		Helper,
		Input,
		Label,
		Select,
		Spinner,
		Textarea
	} from 'flowbite-svelte';
	import { ClipboardCheckOutline } from 'flowbite-svelte-icons';

	const toastService = getToastService();

	type Role = 'visitor' | 'participant' | 'helper' | 'org';

	const ROLE_OPTIONS: { value: Role; name: string }[] = [
		{ value: 'visitor', name: 'Зритель' },
		{ value: 'participant', name: 'Участник' },
		{ value: 'helper', name: 'Волонтёр' },
		{ value: 'org', name: 'Организатор' }
	];

	const MIN_AMOUNT = 1;
	const MAX_AMOUNT = 100;

	let selectedRole = $state<Role>('visitor');
	// Kept as the raw input string: a cleared number field yields '' (not null),
	// which keeps the Flowbite Input binding well-typed. Parsed on validate.
	let amountInput = $state('10');
	let isGenerating = $state(false);

	let amountError = $state('');
	let submitError = $state('');

	let generatedBarcodes = $state<string[]>([]);
	// One barcode per line: pasting this into a spreadsheet fills a single column,
	// one ticket per row.
	let barcodesText = $derived(generatedBarcodes.join('\n'));

	function parseAmount(): number | null {
		const trimmed = amountInput.trim();
		if (trimmed === '') {
			return null;
		}
		const parsed = Number(trimmed);
		return Number.isInteger(parsed) ? parsed : null;
	}

	function validateAmount(): boolean {
		const parsed = parseAmount();
		if (parsed === null || parsed < MIN_AMOUNT || parsed > MAX_AMOUNT) {
			amountError = `Введи число от ${MIN_AMOUNT} до ${MAX_AMOUNT}`;
			return false;
		}
		amountError = '';
		return true;
	}

	function handleAmountInput() {
		if (amountError) {
			validateAmount();
		}
	}

	async function handleSubmit(event: Event) {
		event.preventDefault();
		submitError = '';

		const amount = parseAmount();
		if (!validateAmount() || amount === null) {
			return;
		}

		isGenerating = true;

		try {
			const { data, error, response } = await client.POST('/tickets/generate', {
				body: { role: selectedRole, amount }
			});

			if (error || !response.ok || !data) {
				if (response.status === 401) {
					submitError = 'Нужно войти в аккаунт заново';
				} else if (response.status === 403) {
					submitError = 'У тебя нет доступа к генерации билетов';
				} else if (response.status === 422) {
					submitError = 'Проверь правильность заполнения полей';
				} else {
					submitError = 'Не удалось сгенерировать билеты';
				}
				return;
			}

			generatedBarcodes = data.barcodes;
			toastService.add(`Готово! Создано билетов: ${data.barcodes.length}`, 'success');
		} catch (err) {
			console.error('Failed to generate tickets:', err);
			submitError = 'Произошла непредвиденная ошибка';
		} finally {
			isGenerating = false;
		}
	}

	async function copyBarcodes() {
		try {
			await navigator.clipboard.writeText(barcodesText);
			toastService.add('Скопировано. Вставь в таблицу', 'success');
		} catch (err) {
			console.error('Failed to copy barcodes:', err);
			toastService.add('Не удалось скопировать. Выдели текст и скопируй вручную.', 'error');
		}
	}
</script>

<svelte:head>
	<title>Генерация билетов · ФАН ФАН</title>
</svelte:head>

<SectionIntro
	description="Создавай новые билеты для выбранной роли. Получатель привязывает билет по номеру и получает роль."
/>

<Card class="mx-auto w-full max-w-2xl rounded-2xl p-4 sm:p-6">
	<form class="space-y-6" onsubmit={handleSubmit}>
		<div class="space-y-2">
			<Label for="ticket-role" class="text-gray-900 dark:text-white">Роль</Label>
			<Select
				id="ticket-role"
				items={ROLE_OPTIONS}
				bind:value={selectedRole}
				disabled={isGenerating}
				classes={{ select: 'rounded-xl' }}
			/>
			<Helper class="text-sm text-gray-500 dark:text-gray-400">
				Эту роль получит тот, кто привяжет билет.
			</Helper>
		</div>

		<div class="space-y-2">
			<Label for="ticket-amount" class="text-gray-900 dark:text-white">Количество</Label>
			<Input
				id="ticket-amount"
				type="number"
				min={MIN_AMOUNT}
				max={MAX_AMOUNT}
				step="1"
				bind:value={amountInput}
				disabled={isGenerating}
				oninput={handleAmountInput}
				class="w-full rounded-xl"
			/>
			{#if amountError}
				<Helper color="red" class="mt-1">{amountError}</Helper>
			{:else}
				<Helper class="text-sm text-gray-500 dark:text-gray-400">
					От {MIN_AMOUNT} до {MAX_AMOUNT} билетов за один раз.
				</Helper>
			{/if}
		</div>

		{#if submitError}
			<Alert color="red">
				{submitError}
			</Alert>
		{/if}

		<Button
			type="submit"
			color="primary"
			class="min-h-11 w-full justify-center sm:w-auto"
			disabled={isGenerating}
		>
			{#if isGenerating}
				<Spinner size="4" class="mr-2 fill-white" />
				Генерируем…
			{:else}
				Сгенерировать
			{/if}
		</Button>
	</form>

	{#if generatedBarcodes.length > 0}
		<div class="mt-6 space-y-3 border-t border-gray-200 pt-6 dark:border-gray-700">
			<div class="flex items-center justify-between gap-3">
				<span class="text-sm font-medium text-gray-900 dark:text-white">
					Готовые билеты: {generatedBarcodes.length}
				</span>
				<Button type="button" color="alternative" size="sm" onclick={copyBarcodes}>
					<ClipboardCheckOutline class="mr-2 h-4 w-4" />
					Копировать
				</Button>
			</div>
			<Textarea
				readonly
				rows={Math.min(generatedBarcodes.length, 10)}
				value={barcodesText}
				class="w-full rounded-xl font-mono text-sm"
			/>
			<Helper class="text-sm text-gray-500 dark:text-gray-400">
				Каждый билет — на отдельной строке. Скопируй и вставь в таблицу Excel: номера встанут в один
				столбец.
			</Helper>
		</div>
	{/if}
</Card>
