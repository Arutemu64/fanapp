<script lang="ts">
	import { createApiClient } from '$lib/api';
	const client = createApiClient();
	import BackLink from '$lib/components/BackLink.svelte';
	import SectionIntro from '$lib/components/SectionIntro.svelte';
	import * as Alert from '$lib/components/ui/alert';
	import { Button } from '$lib/components/ui/button';
	import * as Card from '$lib/components/ui/card';
	import * as Field from '$lib/components/ui/field';
	import { Input } from '$lib/components/ui/input';
	import * as Select from '$lib/components/ui/select';
	import { Spinner } from '$lib/components/ui/spinner';
	import { Textarea } from '$lib/components/ui/textarea';
	import { getToastService } from '$lib/services/toasts.svelte';
	import { ClipboardCopy } from '@lucide/svelte';

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
	let selectedRoleLabel = $derived(
		ROLE_OPTIONS.find((option) => option.value === selectedRole)?.name ?? 'Выбери роль'
	);
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

<BackLink href="/tools" label="Назад к инструментам" />

<SectionIntro
	description="Создавай новые билеты для выбранной роли. Получатель привязывает билет по номеру и получает роль."
/>

<Card.Root class="mx-auto w-full max-w-2xl rounded-2xl p-4 sm:p-6">
	<form class="flex flex-col gap-6" onsubmit={handleSubmit}>
		<Field.FieldGroup class="gap-6">
			<Field.Field>
				<Field.FieldLabel for="ticket-role">Роль</Field.FieldLabel>
				<Select.Root type="single" name="role" bind:value={selectedRole} disabled={isGenerating}>
					<Select.Trigger id="ticket-role" class="w-full">
						{selectedRoleLabel}
					</Select.Trigger>
					<Select.Content>
						<Select.Group>
							{#each ROLE_OPTIONS as option (option.value)}
								<Select.Item value={option.value} label={option.name}>
									{option.name}
								</Select.Item>
							{/each}
						</Select.Group>
					</Select.Content>
				</Select.Root>
				<Field.FieldDescription>Эту роль получит тот, кто привяжет билет.</Field.FieldDescription>
			</Field.Field>

			<Field.Field data-invalid={amountError ? true : undefined}>
				<Field.FieldLabel for="ticket-amount">Количество</Field.FieldLabel>
				<Input
					id="ticket-amount"
					type="number"
					min={MIN_AMOUNT}
					max={MAX_AMOUNT}
					step="1"
					bind:value={amountInput}
					disabled={isGenerating}
					oninput={handleAmountInput}
					aria-invalid={amountError ? true : undefined}
					class="w-full rounded-xl"
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
				<Alert.Description>{submitError}</Alert.Description>
			</Alert.Root>
		{/if}

		<Button type="submit" class="min-h-11 w-full justify-center sm:w-auto" disabled={isGenerating}>
			{#if isGenerating}
				<Spinner data-icon="inline-start" />
				Генерируем…
			{:else}
				Сгенерировать
			{/if}
		</Button>
	</form>

	{#if generatedBarcodes.length > 0}
		<div class="mt-6 flex flex-col gap-3 border-t border-border pt-6">
			<div class="flex items-center justify-between gap-3">
				<span class="text-sm font-medium text-foreground">
					Готовые билеты: {generatedBarcodes.length}
				</span>
				<Button type="button" variant="outline" size="sm" onclick={copyBarcodes}>
					<ClipboardCopy data-icon="inline-start" />
					Копировать
				</Button>
			</div>
			<Textarea
				readonly
				rows={Math.min(generatedBarcodes.length, 10)}
				value={barcodesText}
				class="w-full resize-none rounded-xl font-mono text-sm"
			/>
			<p class="text-xs text-muted-foreground">
				Каждый билет — на отдельной строке. Скопируй и вставь в таблицу Excel: номера встанут в один
				столбец.
			</p>
		</div>
	{/if}
</Card.Root>
