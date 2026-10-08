<script lang="ts">
	import { AlertCircle, ClipboardCopy } from '@lucide/svelte';

	import type { UserRole } from '#lib/api/generated/index.js';

	import { getApiErrorDetail, getApiFieldError } from '#lib/api/errors.js';
	import { generateTickets } from '#lib/api/generated/index.js';
	import { createApiClient } from '#lib/api/index.js';
	import SectionIntro from '#lib/components/SectionIntro.svelte';
	import * as Alert from '#lib/components/ui/alert/index.js';
	import { Button } from '#lib/components/ui/button/index.js';
	import * as Field from '#lib/components/ui/field/index.js';
	import { Input } from '#lib/components/ui/input/index.js';
	import * as RadioGroup from '#lib/components/ui/radio-group/index.js';
	import { Spinner } from '#lib/components/ui/spinner/index.js';
	import { Textarea } from '#lib/components/ui/textarea/index.js';
	import { getToastService } from '#lib/services/toasts.svelte.js';

	const client = createApiClient();
	const toastService = getToastService();

	const ROLE_OPTIONS: { value: UserRole; name: string }[] = [
		{ value: 'visitor', name: 'Зритель' },
		{ value: 'participant', name: 'Участник' },
		{ value: 'helper', name: 'Волонтёр' },
		{ value: 'org', name: 'Организатор' }
	];

	const MIN_AMOUNT = 1;
	const MAX_AMOUNT = 100;

	let selectedRole = $state<UserRole>('visitor');
	// A `type="number"` binding yields a number, or an empty value when the field is
	// cleared — never a string. Validated as an integer in range on submit.
	let amountInput = $state<number | undefined>(10);
	let isGenerating = $state(false);

	let amountError = $state('');
	let submitError = $state('');

	let generatedBarcodes = $state<string[]>([]);
	// One barcode per line: pasting this into a spreadsheet fills a single column,
	// one ticket per row.
	let barcodesText = $derived(generatedBarcodes.join('\n'));

	function parseAmount(): number | null {
		// Guards both the cleared field (null/undefined) and non-integer input.
		if (!Number.isInteger(amountInput)) {
			return null;
		}
		return amountInput as number;
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
		if (isGenerating) return;
		submitError = '';

		const amount = parseAmount();
		if (!validateAmount() || amount === null) {
			return;
		}

		isGenerating = true;

		try {
			const { data, error, response } = await generateTickets({
				client,
				body: { role: selectedRole, amount }
			});

			if (error || !response?.ok || !data) {
				const amountFieldError = getApiFieldError(error, 'amount');
				if (amountFieldError) {
					amountError = amountFieldError;
					return;
				}
				submitError = getApiErrorDetail(error) ?? 'Не удалось сгенерировать билеты';
				return;
			}

			generatedBarcodes = data.barcodes;
			toastService.add(`Готово! Создано билетов: ${data.barcodes.length}`, 'success');
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

<!-- novalidate: the amount's min/max would otherwise raise the browser's own bubble
     in the browser's language before our message. -->
<form novalidate class="flex flex-col gap-6" onsubmit={handleSubmit}>
	<Field.FieldGroup class="gap-6">
		<!-- Radios, not a select: four options read at a glance and take one tap, and
		     a select is the harder control for many people
		     (https://design-system.service.gov.uk/components/select/). -->
		<Field.FieldSet>
			<Field.FieldLegend variant="label">Роль</Field.FieldLegend>
			<Field.FieldDescription>Эту роль получит тот, кто привяжет билет.</Field.FieldDescription>
			<RadioGroup.Root
				bind:value={() => selectedRole, (value) => (selectedRole = value as UserRole)}
				name="role"
				disabled={isGenerating}
				class="grid grid-cols-1 gap-3 sm:grid-cols-2"
			>
				{#each ROLE_OPTIONS as option (option.value)}
					<Field.Field orientation="horizontal">
						<RadioGroup.Item value={option.value} id="ticket-role-{option.value}" />
						<Field.FieldLabel for="ticket-role-{option.value}" class="cursor-pointer font-normal">
							{option.name}
						</Field.FieldLabel>
					</Field.Field>
				{/each}
			</RadioGroup.Root>
		</Field.FieldSet>

		<Field.Field data-invalid={amountError ? true : undefined}>
			<Field.FieldLabel for="ticket-amount">Количество</Field.FieldLabel>
			<Input
				id="ticket-amount"
				type="number"
				min={MIN_AMOUNT}
				max={MAX_AMOUNT}
				step="1"
				inputmode="numeric"
				bind:value={amountInput}
				readonly={isGenerating}
				oninput={handleAmountInput}
				aria-invalid={amountError ? true : undefined}
			/>
			{#if amountError}
				<Field.FieldError>{amountError}</Field.FieldError>
			{:else}
				<Field.FieldDescription>
					От {MIN_AMOUNT} до {MAX_AMOUNT} билетов за один раз.
				</Field.FieldDescription>
			{/if}
		</Field.Field>
	</Field.FieldGroup>

	{#if submitError}
		<Alert.Root variant="destructive">
			<AlertCircle />
			<Alert.Description>{submitError}</Alert.Description>
		</Alert.Root>
	{/if}

	<Button type="submit" class="w-full sm:w-auto sm:self-start" disabled={isGenerating}>
		{#if isGenerating}
			<Spinner data-icon="inline-start" />
			Генерируем…
		{:else}
			Сгенерировать
		{/if}
	</Button>
</form>

{#if generatedBarcodes.length > 0}
	<section class="mt-8 flex flex-col gap-3" aria-labelledby="generated-tickets-heading">
		<div class="flex items-center justify-between gap-3">
			<h2 id="generated-tickets-heading" class="text-base font-semibold sm:text-lg">
				Готовые билеты: {generatedBarcodes.length}
			</h2>
			<Button type="button" variant="outline" size="sm" onclick={copyBarcodes}>
				<ClipboardCopy data-icon="inline-start" />
				Копировать
			</Button>
		</div>
		<Textarea
			readonly
			aria-labelledby="generated-tickets-heading"
			rows={Math.min(generatedBarcodes.length, 10)}
			value={barcodesText}
			class="resize-none font-mono text-sm"
		/>
		<p class="text-xs text-muted-foreground">
			Каждый билет — на отдельной строке. Скопируй и вставь в таблицу Excel: номера встанут в один
			столбец.
		</p>
	</section>
{/if}
