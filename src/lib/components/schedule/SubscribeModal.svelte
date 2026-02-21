<script lang="ts">
	import { Button, Modal, Input } from 'flowbite-svelte';
	import { PlusOutline, MinusOutline, BellActiveOutline } from 'flowbite-svelte-icons';
	import type { ScheduleEventDTO } from '$lib/types/schedule';
	import { api } from '$lib/api';
	import { getContext } from 'svelte';
	import type { ScheduleStore } from '$lib/stores/schedule.svelte';

	const useScheduleStore = getContext<ScheduleStore>('useScheduleStore');

	interface Props {
		open: boolean;
		event: ScheduleEventDTO;
	}
	let { open = $bindable(), event }: Props = $props();

	let counter = $state(5);

	function increment() {
		if (counter < 100) counter++;
	}

	function decrement() {
		if (counter > 1) counter--;
	}

	async function handleSubmit() {
		try {
			await api.post('/subscriptions', {
				event_id: event.id,
				counter
			});
			useScheduleStore.refresh();
			console.log('Subscribed with counter:', counter);
		} catch (error) {
			console.error('Subscription error:', error);
		} finally {
			open = false;
		}
	}
</script>

<Modal bind:open size="sm" title="Подписка на уведомления">
	<p class="text-gray-600 dark:text-gray-400">
		За сколько выступлений до начала <strong class="text-gray-900 dark:text-white"
			>{event.title}</strong
		> начать присылать уведомления?
	</p>

	<div class="flex items-center justify-center gap-3">
		<Button
			type="button"
			color="light"
			onclick={decrement}
			class="h-10 w-10 p-0"
			disabled={counter <= 1}
			aria-label="Уменьшить"
		>
			<MinusOutline class="h-5 w-5" />
		</Button>

		<Input
			type="number"
			min="1"
			max="100"
			bind:value={counter}
			class="w-10 text-center font-bold [-moz-appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
		/>

		<Button
			type="button"
			color="light"
			onclick={increment}
			class="h-10 w-10 p-0"
			disabled={counter >= 100}
			aria-label="Увеличить"
		>
			<PlusOutline class="h-5 w-5" />
		</Button>
	</div>

	<Button type="button" onclick={handleSubmit} class="w-full">
		<span class="flex items-center gap-2">
			<BellActiveOutline class="h-4 w-4" />
			Подписаться
		</span>
	</Button>
</Modal>
