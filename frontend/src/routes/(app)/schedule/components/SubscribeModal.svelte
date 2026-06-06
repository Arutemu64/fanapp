<script lang="ts">
	import { invalidate } from '$app/navigation';
	import { createApiClient } from '$lib/api';
	const client = createApiClient();
	import { getApiErrorDetail } from '$lib/api/errors';
	import { getToastService } from '$lib/services/toasts.svelte';
	import type { ScheduleEventFullDTO } from '$lib/types/schedule';
	import { Button, Modal, Alert } from 'flowbite-svelte';
	import { BellActiveSolid, MinusOutline, PlusOutline } from 'flowbite-svelte-icons';

	interface Props {
		open: boolean;
		event: ScheduleEventFullDTO;
	}
	let { open = $bindable(), event }: Props = $props();
	const toastService = getToastService();

	let counter = $state(5);
	let formError = $state('');

	$effect(() => {
		if (open) {
			formError = '';
		}
	});

	function increment() {
		if (counter < 100) counter++;
		formError = '';
	}

	function decrement() {
		if (counter > 1) counter--;
		formError = '';
	}

	async function handleSubmit() {
		counter = Math.max(1, Math.min(100, Math.floor(counter)));
		formError = '';
		const { error, response } = await client.POST('/schedule/subscriptions/', {
			body: {
				event_id: event.id,
				counter
			}
		});

		if (error || !response.ok) {
			formError = getApiErrorDetail(error) ?? 'Не удалось оформить подписку';
			return;
		}

		toastService.add('Подписка оформлена!', 'success');
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

	<h3 class="mb-4 text-xl font-semibold text-gray-900 dark:text-white">Подписка на уведомления</h3>
	<p class="text-gray-600 dark:text-gray-400">
		За сколько выступлений до начала <strong class="text-gray-900 dark:text-white"
			>{event.title}</strong
		> начать присылать уведомления?
	</p>

	<div class="my-4 flex items-center justify-center">
		<div
			class="flex -space-x-px overflow-hidden rounded-lg border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800"
		>
			<!-- Decrement Button -->
			<button
				type="button"
				onclick={decrement}
				class="flex h-11 w-12 items-center justify-center border-r border-gray-200 bg-gray-50 text-gray-500 transition-colors hover:bg-gray-100 disabled:cursor-not-allowed disabled:opacity-50 dark:border-gray-700 dark:bg-gray-700 dark:hover:bg-gray-600"
				disabled={counter <= 1}
				aria-label="Уменьшить"
			>
				<MinusOutline class="h-5 w-5" />
			</button>

			<!-- Input Wrapper with absolute positioning for label -->
			<div class="relative flex h-11 w-44 flex-col items-center justify-center">
				<input
					name="subscription_counter"
					type="number"
					aria-label="Сколько выступлений ждать до уведомления"
					min="1"
					max="100"
					inputmode="numeric"
					autocomplete="off"
					bind:value={counter}
					class="h-full w-full border-0 bg-transparent pb-5 text-center font-bold text-gray-900 [-moz-appearance:textfield] focus:ring-0 focus:outline-none dark:text-white [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
				/>
				<div
					class="pointer-events-none absolute bottom-1 flex items-center text-xs text-gray-400 select-none dark:text-gray-500"
				>
					<span>выступлений</span>
				</div>
			</div>

			<!-- Increment Button -->
			<button
				type="button"
				onclick={increment}
				class="flex h-11 w-12 items-center justify-center border-l border-gray-200 bg-gray-50 text-gray-500 transition-colors hover:bg-gray-100 disabled:cursor-not-allowed disabled:opacity-50 dark:border-gray-700 dark:bg-gray-700 dark:hover:bg-gray-600"
				disabled={counter >= 100}
				aria-label="Увеличить"
			>
				<PlusOutline class="h-5 w-5" />
			</button>
		</div>
	</div>

	<Button type="button" onclick={handleSubmit} class="w-full">
		<BellActiveSolid class="me-2 h-4 w-4" />
		Подписаться
	</Button>
</Modal>
