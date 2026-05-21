<script lang="ts">
	import { invalidate } from '$app/navigation';
	import { client } from '$lib/api';
	import { getToastService } from '$lib/services/toasts.svelte';
	import type { ScheduleEventFullDTO } from '$lib/types/schedule';
	import { Button, ButtonGroup, Input, Modal } from 'flowbite-svelte';
	import { BellActiveOutline, MinusOutline, PlusOutline } from 'flowbite-svelte-icons';

	interface Props {
		open: boolean;
		event: ScheduleEventFullDTO;
	}
	let { open = $bindable(), event }: Props = $props();
	const toastService = getToastService();

	let counter = $state(5);

	function increment() {
		if (counter < 100) counter++;
	}

	function decrement() {
		if (counter > 1) counter--;
	}

	async function handleSubmit() {
		counter = Math.max(1, Math.min(100, Math.floor(counter)));
		const { error, response } = await client.POST('/schedule/subscriptions/', {
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
		await invalidate('app:schedule');
		open = false;
	}
</script>

<Modal bind:open size="sm">
	<h3 class="text-xl font-semibold text-gray-900 dark:text-white mb-4">Подписка на уведомления</h3>
	<p class="text-gray-600 dark:text-gray-400">
		За сколько выступлений до начала <strong class="text-gray-900 dark:text-white"
			>{event.title}</strong
		> начать присылать уведомления?
	</p>

	<div class="flex items-center justify-center my-4">
		<div class="flex -space-x-px rounded-lg overflow-hidden border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
			<!-- Decrement Button -->
			<button
				type="button"
				onclick={decrement}
				class="h-11 w-12 flex items-center justify-center bg-gray-50 dark:bg-gray-700 text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors border-r border-gray-200 dark:border-gray-700"
				disabled={counter <= 1}
				aria-label="Уменьшить"
			>
				<MinusOutline class="h-5 w-5" />
			</button>

			<!-- Input Wrapper with absolute positioning for label -->
			<div class="relative w-44 h-11 flex flex-col justify-center items-center">
				<input
					name="subscription_counter"
					type="number"
					aria-label="Сколько выступлений ждать до уведомления"
					min="1"
					max="100"
					inputmode="numeric"
					autocomplete="off"
					bind:value={counter}
					class="w-full h-full pb-5 text-center font-bold text-gray-900 dark:text-white bg-transparent border-0 focus:ring-0 focus:outline-none [-moz-appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
				/>
				<div class="absolute bottom-1 flex items-center text-[10px] text-gray-400 dark:text-gray-500 pointer-events-none select-none">
					<span>выступлений</span>
				</div>
			</div>

			<!-- Increment Button -->
			<button
				type="button"
				onclick={increment}
				class="h-11 w-12 flex items-center justify-center bg-gray-50 dark:bg-gray-700 text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors border-l border-gray-200 dark:border-gray-700"
				disabled={counter >= 100}
				aria-label="Увеличить"
			>
				<PlusOutline class="h-5 w-5" />
			</button>
		</div>
	</div>

	<Button type="button" onclick={handleSubmit} class="w-full">
		Подписаться
	</Button>
</Modal>
