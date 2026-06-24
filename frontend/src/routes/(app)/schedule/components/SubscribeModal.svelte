<script lang="ts">
	import { invalidate } from '$app/navigation';
	import { createApiClient } from '$lib/api';
	const client = createApiClient();
	import { getApiErrorDetail } from '$lib/api/errors';
	import { getToastService } from '$lib/services/toasts.svelte';
	import type { ScheduleItemFullDTO } from '$lib/types/schedule';
	import { Button, Modal, Alert } from 'flowbite-svelte';
	import { BellActiveSolid, MinusOutline, PlusOutline } from 'flowbite-svelte-icons';

	interface Props {
		open: boolean;
		event: ScheduleItemFullDTO;
	}
	let { open = $bindable(), event }: Props = $props();
	const toastService = getToastService();

	let counter = $state(5);
	let formError = $state('');

	$effect(() => {
		if (open) {
			counter = 5;
			formError = '';
		}
	});

	// Clamp to the valid 1–100 range, snapping a cleared/NaN input back to the min
	// so +/- never dead-locks and submit never POSTs null.
	function clampCounter() {
		counter = Number.isFinite(counter) ? Math.max(1, Math.min(100, Math.floor(counter))) : 1;
	}

	function increment() {
		counter = Number.isFinite(counter) ? Math.min(100, Math.floor(counter) + 1) : 1;
		formError = '';
	}

	function decrement() {
		counter = Number.isFinite(counter) ? Math.max(1, Math.floor(counter) - 1) : 1;
		formError = '';
	}

	async function handleSubmit() {
		clampCounter();
		formError = '';
		const { error, response } = await client.POST('/schedule/subscriptions/', {
			body: {
				schedule_item_id: event.id,
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
	{#snippet header()}
		<div class="flex items-center gap-2">
			<BellActiveSolid class="h-5 w-5 text-gray-500 dark:text-gray-400" />
			<h3 class="text-lg font-bold text-gray-900 dark:text-white">Подписка на уведомления</h3>
		</div>
	{/snippet}

	{#if formError}
		<Alert color="red" class="mb-4 rounded-xl text-sm">
			{formError}
		</Alert>
	{/if}

	<p class="text-gray-600 dark:text-gray-400">
		За сколько выступлений до <strong class="text-gray-900 dark:text-white">{event.title}</strong>
		начать присылать тебе уведомления?
	</p>

	<div class="my-4 flex items-center justify-center">
		<div
			class="flex -space-x-px overflow-hidden rounded-lg border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800"
		>
			<button
				type="button"
				onclick={decrement}
				class="flex h-11 w-12 items-center justify-center border-r border-gray-200 bg-gray-50 text-gray-500 transition-colors hover:bg-gray-100 disabled:cursor-not-allowed disabled:opacity-50 dark:border-gray-700 dark:bg-gray-700 dark:hover:bg-gray-600"
				disabled={counter <= 1}
				aria-label="Уменьшить"
			>
				<MinusOutline class="h-5 w-5" />
			</button>

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
					onblur={clampCounter}
					class="h-full w-full border-0 bg-transparent pb-5 text-center font-bold text-gray-900 [-moz-appearance:textfield] focus:ring-0 focus:outline-none dark:text-white [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
				/>
				<div
					class="pointer-events-none absolute bottom-1 flex items-center text-xs text-gray-400 select-none dark:text-gray-500"
				>
					<span>выступлений</span>
				</div>
			</div>

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

	{#snippet footer()}
		<Button type="button" color="alternative" onclick={() => (open = false)}>Отмена</Button>
		<Button type="button" onclick={handleSubmit}>Подписаться</Button>
	{/snippet}
</Modal>
