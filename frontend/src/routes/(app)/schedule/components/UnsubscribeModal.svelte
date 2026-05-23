<script lang="ts">
	import { invalidate } from '$app/navigation';
	import { client } from '$lib/api';
	import { getApiErrorDetail } from '$lib/api/errors';
	import { getToastService } from '$lib/services/toasts.svelte';
	import type { ScheduleEventFullDTO } from '$lib/types/schedule';
	import { Button, Modal, Alert } from 'flowbite-svelte';
	import { BellOutline } from 'flowbite-svelte-icons';

	interface Props {
		open: boolean;
		event: ScheduleEventFullDTO;
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
	{#if formError}
		<Alert color="red" class="mb-4 rounded-xl text-sm">
			{formError}
		</Alert>
	{/if}

	<h3 class="mb-4 text-xl font-semibold text-gray-900 dark:text-white">Отписка от уведомлений</h3>
	<p class="text-gray-600 dark:text-gray-400">
		Хочешь отписаться от уведомлений о выступлении <strong class="text-gray-900 dark:text-white"
			>{event.title}</strong
		>?
	</p>

	<div class="flex gap-3">
		<Button type="button" color="light" onclick={() => (open = false)} class="flex-1">
			Отмена
		</Button>
		<Button type="button" color="red" onclick={handleUnsubscribe} class="flex-1">Отписаться</Button>
	</div>
</Modal>
