<script lang="ts">
	import { Button, Modal } from 'flowbite-svelte';
	import { BellOutline } from 'flowbite-svelte-icons';
	import type { ScheduleEventDTO } from '$lib/types/schedule';
	import { api } from '$lib/api';

	interface Props {
		open: boolean;
		event: ScheduleEventDTO;
	}
	let { open = $bindable(), event }: Props = $props();

	async function handleUnsubscribe() {
		if (!event.subscription) {
			open = false;
			return;
		}

		try {
			await api.delete('/schedule/subscriptions', {
				body: JSON.stringify({ subscription_id: event.subscription.id })
			});
			open = false;
		} catch (error) {
			console.error('Error unsubscribing:', error);
		}
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
