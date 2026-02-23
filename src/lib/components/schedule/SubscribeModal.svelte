<script lang="ts">
	import { invalidateAll } from '$app/navigation';
	import { client } from '$lib/api';
	import { toastService } from '$lib/stores/toasts.svelte';
	import type { ScheduleEventFullDTO } from '$lib/types/schedule';
	import { Button, Input, Modal } from 'flowbite-svelte';
	import { BellActiveOutline, MinusOutline, PlusOutline } from 'flowbite-svelte-icons';

	interface Props {
		open: boolean;
		event: ScheduleEventFullDTO;
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
		const { data, error, response } = await client.POST('/schedule/subscriptions', {
			body: {
				event_id: event.id,
				counter
			}
		});

		if (error || !response.ok) {
			toastService.error(error ?? new Error('Ошибка подписки'));
			open = false;
			return;
		}

		toastService.add('Подписка оформлена!', 'success');
		invalidateAll();
		open = false;
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
