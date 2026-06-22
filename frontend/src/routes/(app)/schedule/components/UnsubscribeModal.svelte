<script lang="ts">
	import { invalidate } from '$app/navigation';
	import { createApiClient } from '$lib/api';
	const client = createApiClient();
	import { getApiErrorDetail } from '$lib/api/errors';
	import { getToastService } from '$lib/services/toasts.svelte';
	import type { ScheduleEventWithSubscription } from '$lib/types/schedule';
	import { Button, Modal, Alert } from 'flowbite-svelte';
	import { BellOutline } from 'flowbite-svelte-icons';

	interface Props {
		open: boolean;
		event: ScheduleEventWithSubscription;
	}
	let { open = $bindable(), event }: Props = $props();
	const toastService = getToastService();
	let formError = $state('');

	$effect(() => {
		if (open) {
			formError = '';
		}
	});

	async function handleUnsubscribe() {
		if (!event.user_subscription) {
			open = false;
			return;
		}

		formError = '';
		const { error, response } = await client.DELETE('/schedule/subscriptions/{subscription_id}', {
			params: { path: { subscription_id: event.user_subscription.id } }
		});

		if (error || !response.ok) {
			console.error('Error unsubscribing:', error);
			formError = getApiErrorDetail(error) ?? 'Не удалось отключить уведомления';
			return;
		}

		toastService.add('Подписка на уведомления отключена', 'success');
		await invalidate('app:schedule');
		open = false;
	}
</script>

<Modal bind:open size="sm">
	{#snippet header()}
		<div class="flex items-center gap-2">
			<BellOutline class="h-5 w-5 text-gray-500 dark:text-gray-400" />
			<h3 class="text-lg font-bold text-gray-900 dark:text-white">Отписка от уведомлений</h3>
		</div>
	{/snippet}

	{#if formError}
		<Alert color="red" class="mb-4 rounded-xl text-sm">
			{formError}
		</Alert>
	{/if}

	<p class="text-gray-600 dark:text-gray-400">
		Хочешь отписаться от уведомлений о выступлении <strong class="text-gray-900 dark:text-white"
			>{event.title}</strong
		>?
	</p>

	{#snippet footer()}
		<Button type="button" color="alternative" onclick={() => (open = false)}>Отмена</Button>
		<Button type="button" color="red" onclick={handleUnsubscribe}>Отписаться</Button>
	{/snippet}
</Modal>
