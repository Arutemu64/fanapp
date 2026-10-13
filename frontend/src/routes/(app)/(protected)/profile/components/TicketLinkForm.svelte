<script lang="ts">
	import { CheckCircle2 } from '@lucide/svelte';
	import { createMutation, useQueryClient } from '@tanstack/svelte-query';

	import type { CurrentUserDto } from '#lib/api/generated/index.js';

	import { getApiErrorDetail } from '#lib/api/errors.js';
	import {
		getCurrentUserQueryKey,
		getVotingStatusQueryKey,
		linkTicketMutation
	} from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import { Button } from '#lib/components/ui/button/index.js';
	import * as Field from '#lib/components/ui/field/index.js';
	import { Input } from '#lib/components/ui/input/index.js';
	import { Spinner } from '#lib/components/ui/spinner/index.js';
	import { getToastService } from '#lib/services/toasts.svelte.js';
	import { offlineWriteGate } from '#lib/utils/offlineAction.js';

	import SettingsSection from './SettingsSection.svelte';

	interface Props {
		user: CurrentUserDto;
	}

	let { user }: Props = $props();
	const queryClient = useQueryClient();
	const toastService = getToastService();

	const linkMutation = createMutation(() => ({
		...linkTicketMutation(),
		onSuccess: () => {
			// A linked ticket is what lets the user vote, so the voting status moves with it.
			void queryClient.invalidateQueries({ queryKey: getVotingStatusQueryKey() });
			return queryClient.invalidateQueries({ queryKey: getCurrentUserQueryKey() });
		}
	}));

	// Linking a ticket is a mutation — online only. A linked ticket still shows.
	const offlineGate = offlineWriteGate();

	let barcode = $state('');
	let submitError = $state('');
	let barcodeDescribedBy = $derived(
		submitError ? 'ticket-barcode-error ticket-barcode-hint' : 'ticket-barcode-hint'
	);

	function handleLinkTicket(event: SubmitEvent) {
		event.preventDefault();
		submitError = '';

		if (!barcode.trim()) {
			submitError = 'Введи номер билета';
			return;
		}

		linkMutation.mutate(
			{ body: { barcode: barcode.trim() } },
			{
				onSuccess: () => {
					toastService.add('Билет привязан', 'success');
					barcode = '';
				},
				onError: (error) => {
					submitError = getApiErrorDetail(error) ?? 'Не удалось привязать билет';
				}
			}
		);
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
					disabled={linkMutation.isPending || offlineGate.disabled}
					oninput={() => (submitError = '')}
				/>
				{#if submitError}
					<Field.FieldError id="ticket-barcode-error">{submitError}</Field.FieldError>
				{/if}
			</Field.Field>
			<Button
				type="submit"
				class="w-full"
				disabled={linkMutation.isPending || offlineGate.disabled}
				title={offlineGate.title}
			>
				{#if linkMutation.isPending}
					<Spinner data-icon="inline-start" />
					Привязка…
				{:else}
					Привязать билет
				{/if}
			</Button>
		</form>
	{/if}
</SettingsSection>
