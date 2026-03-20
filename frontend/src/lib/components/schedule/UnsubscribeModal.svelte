<script lang="ts">
	import { invalidate } from '$app/navigation';
	import { client } from '$lib/api';
	import { getToastService } from '$lib/services/toasts.svelte';
	import type { ScheduleEventFullDTO } from '$lib/types/schedule';
	import { Button, Modal } from 'flowbite-svelte';
	import { BellOutline } from 'flowbite-svelte-icons';

	interface Props {
		open: boolean;
		event: ScheduleEventFullDTO;
	}
	let { open = $bindable(), event }: Props = $props();
	const toastService = getToastService();

	async function handleUnsubscribe() {
		if (!event.user_subscription) {
			open = false;
			return;
		}

		const { data, error, response } = await client.DELETE(
			'/schedule/subscriptions/{subscription_id}',
			{
				params: { path: { subscription_id: event.user_subscription.id } }
			}
		);

		if (error) {
			console.error('Error unsubscribing:', error);
			toastService.error(error);
			return;
		}

		toastService.add('Вы отписались от уведомлений', 'success');
		await invalidate('app:schedule');
		open = false;
	}
</script>

<Modal bind:open size="sm" title="Отписка от уведомлений">
	<p class="text-gray-600 dark:text-gray-400">
		Вы уверены, что хотите отписаться от уведомлений о выступлении <strong
			class="text-gray-900 dark:text-white">{event.title}</strong
		>?
	</p>

	<div class="flex gap-3">
		<Button type="button" color="light" onclick={() => (open = false)} class="flex-1">
			Отмена
		</Button>
		<Button type="button" color="red" onclick={handleUnsubscribe} class="flex-1">
			<span class="flex items-center gap-2">
				<BellOutline class="h-4 w-4" />
				Отписаться
			</span>
		</Button>
	</div>
</Modal>
