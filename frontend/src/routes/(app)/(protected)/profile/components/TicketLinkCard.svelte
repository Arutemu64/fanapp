<script lang="ts">
	import { createApiClient } from '$lib/api';
	const client = createApiClient();
	import type { CurrentUserDTO } from '$lib/types/user';

	import { getApiErrorDetail } from '$lib/api/errors';
	import * as Alert from '$lib/components/ui/alert';
	import { Button } from '$lib/components/ui/button';
	import * as Field from '$lib/components/ui/field';
	import { Input } from '$lib/components/ui/input';
	import { Spinner } from '$lib/components/ui/spinner';
	import { getToastService } from '$lib/services/toasts.svelte';
	import { offlineWriteGate } from '$lib/utils/offlineAction';
	import { CheckCircle2, Ticket } from '@lucide/svelte';

	import ProfileCardShell from './ProfileCardShell.svelte';

	interface Props {
		user: CurrentUserDTO;
		onTicketLinked?: () => void;
	}

	let { user, onTicketLinked }: Props = $props();
	const toastService = getToastService();

	// Linking a ticket is a mutation — online only. A linked ticket still shows.
	const offlineGate = offlineWriteGate();

	let barcode = $state('');
	let isSubmitting = $state(false);
	let submitError = $state('');

	async function handleLinkTicket() {
		submitError = '';

		if (!barcode.trim()) {
			submitError = 'Введи номер билета';
			return;
		}

		isSubmitting = true;

		try {
			const { error, response } = await client.POST('/me/ticket', {
				body: { barcode: barcode.trim() }
			});

			isSubmitting = false;

			if (error || !response.ok) {
				submitError = getApiErrorDetail(error) ?? 'Не удалось привязать билет';
				return;
			}

			toastService.add('Билет привязан', 'success');
			barcode = '';
			onTicketLinked?.();
		} catch (err) {
			console.error('Ticket link exception:', err);
			submitError = 'Произошла непредвиденная ошибка';
			isSubmitting = false;
		}
	}
</script>

<ProfileCardShell title="Билет" description="Привяжи билет, чтобы получить доступ к голосованию.">
	{#snippet icon()}
		<Ticket class="size-5" />
	{/snippet}

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
		<div class="flex flex-col gap-3 rounded-lg border border-border p-3 sm:p-4">
			{#if submitError}
				<Alert.Root variant="destructive">
					<Alert.Description>{submitError}</Alert.Description>
				</Alert.Root>
			{/if}

			<Field.Field>
				<Field.FieldLabel for="ticket-barcode">Номер билета</Field.FieldLabel>
				<Field.FieldDescription>
					Введи цифры штрихкода с бумажного или электронного билета. Если билета нет — попроси
					специальный код у оргкомитета или волонтёра.
				</Field.FieldDescription>
				<Input
					id="ticket-barcode"
					name="ticket_barcode"
					bind:value={barcode}
					placeholder="Например, 1234567890"
					autocomplete="off"
					autocapitalize="off"
					spellcheck={false}
					disabled={isSubmitting || offlineGate.disabled}
					oninput={() => (submitError = '')}
				/>
			</Field.Field>
			<Button
				onclick={handleLinkTicket}
				class="min-h-11 w-full"
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
		</div>
	{/if}
</ProfileCardShell>
