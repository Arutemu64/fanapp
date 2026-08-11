<script lang="ts">
	import { createApiClient } from '$lib/api';
	const client = createApiClient();
	import type { CurrentUserDTO } from '$lib/types/user';

	import { getApiErrorDetail } from '$lib/api/errors';
	import { getToastService } from '$lib/services/toasts.svelte';
	import { Alert, Button, Input, Label, Spinner } from 'flowbite-svelte';
	import { CheckCircleOutline, TicketOutline, TicketSolid } from 'flowbite-svelte-icons';

	import ProfileCardShell from './ProfileCardShell.svelte';

	interface Props {
		user: CurrentUserDTO;
		onTicketLinked?: () => void;
	}

	let { user, onTicketLinked }: Props = $props();
	const toastService = getToastService();

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
		<TicketOutline class="h-5 w-5" />
	{/snippet}

	{#if user.ticket}
		<div class="rounded-lg bg-green-50 p-4 dark:bg-green-900/20">
			<div class="flex items-center gap-2">
				<CheckCircleOutline class="h-5 w-5 text-green-600 dark:text-green-400" />
				<span class="font-medium text-green-700 dark:text-green-300">Билет привязан</span>
			</div>
			<p class="mt-2 text-sm text-green-600 dark:text-green-400">
				Номер: <span class="font-mono font-medium">{user.ticket.barcode}</span>
			</p>
		</div>
	{:else}
		<div class="space-y-3 rounded-lg border border-gray-200 p-3 sm:p-4 dark:border-gray-700">
			{#if submitError}
				<Alert role="alert" color="red">
					{submitError}
				</Alert>
			{/if}

			<Label for="ticket-barcode">Номер билета</Label>
			<p class="text-sm leading-relaxed text-gray-500 dark:text-gray-400">
				Введи цифры штрихкода с бумажного или электронного билета. Если билета нет — попроси
				специальный код у оргкомитета или волонтёра.
			</p>
			<Input
				id="ticket-barcode"
				name="ticket_barcode"
				bind:value={barcode}
				placeholder="Например, 1234567890"
				autocomplete="off"
				autocapitalize="off"
				spellcheck={false}
				disabled={isSubmitting}
				size="md"
				oninput={() => (submitError = '')}
			/>
			<Button onclick={handleLinkTicket} class="min-h-11 w-full" disabled={isSubmitting} size="md">
				{#if isSubmitting}
					<Spinner class="me-2 h-4 w-4 fill-white" />
					Привязка…
				{:else}
					<TicketSolid class="me-2 h-4 w-4" />
					Привязать билет
				{/if}
			</Button>
		</div>
	{/if}
</ProfileCardShell>
