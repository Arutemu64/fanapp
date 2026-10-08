<script lang="ts">
	import { linkTicket } from '#lib/api/generated/index.js';
	import { createApiClient } from '#lib/api/index.js';
	const client = createApiClient();
	import { CheckCircle2 } from '@lucide/svelte';

	import type { CurrentUserDto } from '#lib/api/generated/index.js';

	import { getApiErrorDetail } from '#lib/api/errors.js';
	import { Button } from '#lib/components/ui/button/index.js';
	import * as Field from '#lib/components/ui/field/index.js';
	import { Input } from '#lib/components/ui/input/index.js';
	import { Spinner } from '#lib/components/ui/spinner/index.js';
	import { getToastService } from '#lib/services/toasts.svelte.js';
	import { offlineWriteGate } from '#lib/utils/offlineAction.js';

	import SettingsSection from './SettingsSection.svelte';

	interface Props {
		user: CurrentUserDto;
		onTicketLinked?: () => void;
	}

	let { user, onTicketLinked }: Props = $props();
	const toastService = getToastService();

	// Linking a ticket is a mutation — online only. A linked ticket still shows.
	const offlineGate = offlineWriteGate();

	let barcode = $state('');
	let isSubmitting = $state(false);
	let submitError = $state('');
	let barcodeDescribedBy = $derived(
		submitError ? 'ticket-barcode-error ticket-barcode-hint' : 'ticket-barcode-hint'
	);

	async function handleLinkTicket(event: SubmitEvent) {
		event.preventDefault();
		submitError = '';

		if (!barcode.trim()) {
			submitError = 'Введи номер билета';
			return;
		}

		isSubmitting = true;

		try {
			const { error, response } = await linkTicket({
				client,
				body: { barcode: barcode.trim() }
			});

			if (error || !response?.ok) {
				submitError = getApiErrorDetail(error) ?? 'Не удалось привязать билет';
				return;
			}

			toastService.add('Билет привязан', 'success');
			barcode = '';
			onTicketLinked?.();
		} finally {
			isSubmitting = false;
		}
	}
</script>

<SettingsSection description="Привяжи билет, чтобы получить доступ к голосованию.">
	{#if user.ticket}
		<div class="rounded-lg bg-success/10 p-4">
			<div class="flex items-center gap-2">
				<CheckCircle2 class="size-5 text-success" />
				<span class="font-medium text-success">Билет привязан</span>
			</div>
			<p class="mt-2 text-sm text-success">
				Номер: <span class="font-mono font-medium">{user.ticket.barcode}</span>
			</p>
		</div>
	{:else}
		<form class="flex flex-col gap-3" onsubmit={handleLinkTicket}>
			<Field.Field data-invalid={submitError ? true : undefined}>
				<Field.FieldLabel for="ticket-barcode">Номер билета</Field.FieldLabel>
				<Field.FieldDescription id="ticket-barcode-hint">
					Введи номер под штрихкодом бумажного или электронного билета. Если билета нет — попроси
					специальный код у оргкомитета или волонтёра.
				</Field.FieldDescription>
				<Input
					id="ticket-barcode"
					name="ticket_barcode"
					bind:value={barcode}
					placeholder="Например, 1234567890"
					autocomplete="off"
					autocapitalize="off"
					enterkeyhint="go"
					spellcheck={false}
					aria-invalid={submitError ? true : undefined}
					aria-describedby={barcodeDescribedBy}
					disabled={isSubmitting || offlineGate.disabled}
					oninput={() => (submitError = '')}
				/>
				{#if submitError}
					<Field.FieldError id="ticket-barcode-error">{submitError}</Field.FieldError>
				{/if}
			</Field.Field>
			<Button
				type="submit"
				class="w-full"
				disabled={isSubmitting || offlineGate.disabled}
				title={offlineGate.title}
			>
				{#if isSubmitting}
					<Spinner data-icon="inline-start" />
					Привязка…
				{:else}
					Привязать билет
				{/if}
			</Button>
		</form>
	{/if}
</SettingsSection>
