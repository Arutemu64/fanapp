<script lang="ts">
	import { invalidateAll } from '$app/navigation';
	import { client } from '$lib/api';
	import { getToastService } from '$lib/stores/toasts.svelte';
	import type { UserFullDTO } from '$lib/types/user';
	import { Button, Card, Input, Spinner } from 'flowbite-svelte';
	import { CheckCircleOutline, TicketSolid } from 'flowbite-svelte-icons';

	interface Props {
		user: UserFullDTO;
		onTicketLinked?: () => void;
	}

	let { user, onTicketLinked }: Props = $props();
	const toastService = getToastService();

	let barcode = $state('');
	let isSubmitting = $state(false);

	async function handleLinkTicket() {
		if (!barcode.trim()) {
			toastService.add('Введите номер билета', 'warning');
			return;
		}

		isSubmitting = true;

		const { error } = await client.POST('/users/me/ticket', {
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

<Card class="w-full max-w-none p-5">
	<div class="mb-4 flex items-center gap-2">
		<TicketSolid class="h-5 w-5 text-primary-600 dark:text-primary-400" />
		<h2 class="text-lg font-bold text-gray-900 dark:text-white">Привязка билета</h2>
	</div>

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
		<ul class="mb-4 space-y-3">
			<li class="flex items-start gap-2">
				<div
					class="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-primary-100 dark:bg-primary-900"
				>
					<CheckCircleOutline class="h-3 w-3 text-primary-600 dark:text-primary-400" />
				</div>
				<div>
					<span class="text-sm font-medium text-gray-900 dark:text-white"
						>Участие в голосовании</span
					>
					<p class="text-xs text-gray-500 dark:text-gray-400">
						Голосуйте за лучших участников мероприятия
					</p>
				</div>
			</li>
			<li class="flex items-start gap-2">
				<div
					class="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-primary-100 dark:bg-primary-900"
				>
					<CheckCircleOutline class="h-3 w-3 text-primary-600 dark:text-primary-400" />
				</div>
				<div>
					<span class="text-sm font-medium text-gray-900 dark:text-white">Выполнение квестов</span>
					<p class="text-xs text-gray-500 dark:text-gray-400">
						Участвуйте в квестах и получайте награды
					</p>
				</div>
			</li>
			<li class="flex items-start gap-2">
				<div
					class="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-primary-100 dark:bg-primary-900"
				>
					<CheckCircleOutline class="h-3 w-3 text-primary-600 dark:text-primary-400" />
				</div>
				<div>
					<span class="text-sm font-medium text-gray-900 dark:text-white"
						>Эксклюзивные материалы</span
					>
					<p class="text-xs text-gray-500 dark:text-gray-400">
						Получите доступ к уникальному контенту
					</p>
				</div>
			</li>
		</ul>

		<div class="space-y-3">
			<Input
				bind:value={barcode}
				placeholder="Введите номер билета"
				disabled={isSubmitting}
				size="md"
			/>
			<Button onclick={handleLinkTicket} class="min-h-11 w-full" disabled={isSubmitting} size="md">
				{#if isSubmitting}
					<Spinner class="me-2 h-4 w-4" />
					Привязка...
				{:else}
					Привязать билет
				{/if}
			</Button>
		</div>
	{/if}
</Card>
