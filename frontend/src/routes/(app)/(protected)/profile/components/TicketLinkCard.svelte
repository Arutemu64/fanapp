<script lang="ts">
	import { client } from '$lib/api';
	import { getToastService } from '$lib/services/toasts.svelte';
	import type { CurrentUserDTO } from '$lib/types/user';
	import { Button, Input, Label, Spinner } from 'flowbite-svelte';
	import { CheckCircleOutline, TicketSolid } from 'flowbite-svelte-icons';
	import ProfileCardShell from './ProfileCardShell.svelte';

	interface Props {
		user: CurrentUserDTO;
		onTicketLinked?: () => void;
	}

	let { user, onTicketLinked }: Props = $props();
	const toastService = getToastService();

	let barcode = $state('');
	let isSubmitting = $state(false);

	async function handleLinkTicket() {
		if (!barcode.trim()) {
			toastService.add('Введи номер билета', 'warning');
			return;
		}

		isSubmitting = true;

		const { error } = await client.POST('/me/ticket', {
			body: { barcode: barcode.trim() }
		});

		isSubmitting = false;

		if (error) {
			toastService.error(error);
			return;
		}

		toastService.add('Билет успешно привязан!', 'success');
		barcode = '';
		onTicketLinked?.();
	}
</script>

<ProfileCardShell title="Билет" description="Привяжи билет, чтобы получить доступ к голосованию.">
	{#snippet icon()}
		<TicketSolid class="h-5 w-5" />
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
			<Label for="ticket-barcode">Номер билета</Label>
			<Input
				id="ticket-barcode"
				name="ticket_barcode"
				bind:value={barcode}
				placeholder="Введи номер билета"
				autocomplete="off"
				autocapitalize="off"
				spellcheck={false}
				disabled={isSubmitting}
				size="md"
				class="ps-9"
			>
				{#snippet left()}
					<TicketSolid class="h-5 w-5" />
				{/snippet}
			</Input>
			<Button onclick={handleLinkTicket} class="min-h-11 w-full" disabled={isSubmitting} size="md">
				{#if isSubmitting}
					<Spinner class="me-2 h-4 w-4" />
					Привязка…
				{:else}
					Привязать билет
				{/if}
			</Button>
		</div>
	{/if}
</ProfileCardShell>
