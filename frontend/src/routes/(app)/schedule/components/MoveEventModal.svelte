<script lang="ts">
	import { Button, Modal, Search, Alert } from 'flowbite-svelte';
	import { ShuffleOutline } from 'flowbite-svelte-icons';
	import type { ScheduleEventFullDTO } from '$lib/types/schedule';
	import { client } from '$lib/api';
	import { getApiErrorDetail } from '$lib/api/errors';
	import { getToastService } from '$lib/services/toasts.svelte';

	interface Props {
		open: boolean;
		event: ScheduleEventFullDTO;
		schedule: ScheduleEventFullDTO[];
	}

	let { open = $bindable(), event, schedule }: Props = $props();
	const toastService = getToastService();

	let query = $state('');
	let selectedId: string | null = $state(null);
	let formError = $state('');

	$effect(() => {
		if (open) {
			formError = '';
		}
	});

	// Reset error when search changes
	$effect(() => {
		if (query) {
			formError = '';
		}
	});

	let filtered = $derived(
		schedule.filter((ev) => {
			const q = query.toLowerCase();
			return (
				ev.public_number.toString().toLowerCase().includes(q) ||
				ev.title.toLowerCase().includes(q) ||
				ev.block_title?.toLowerCase().includes(q) ||
				ev.nomination_title?.toLowerCase().includes(q)
			);
		})
	);

	function handleSelect(ev: ScheduleEventFullDTO) {
		selectedId = selectedId === ev.id ? null : ev.id;
	}

	async function handleSubmit() {
		if (selectedId) {
			formError = '';
			try {
				const { error, response } = await client.PATCH('/schedule/{event_id}/move', {
					params: { path: { event_id: event.id } },
					body: { place_after_event_id: selectedId }
				});

				if (error || !response.ok) {
					console.error('Error moving event:', error);
					formError = getApiErrorDetail(error) ?? 'Не удалось перенести выступление';
					return;
				}

				const selectedEvent = schedule.find((e) => e.id === selectedId);
				console.log('Move event after:', selectedEvent?.title);
				toastService.add('Выступление перенесено', 'success');

				// Successful flow: close modal and reset fields
				open = false;
				selectedId = null;
				query = '';
			} catch (error) {
				console.error('Error moving event:', error);
				formError = 'Произошла непредвиденная ошибка при переносе';
			}
		}
	}
</script>

<Modal bind:open size="sm" class="px-2">
	<div class="flex flex-col gap-4 sm:gap-5">
		{#if formError}
			<Alert color="red" class="rounded-xl text-sm">
				{formError}
			</Alert>
		{/if}

		<h3 class="text-xl font-semibold text-gray-900 dark:text-white">Переместить событие</h3>
		<p class="text-sm text-gray-600 sm:text-base dark:text-gray-400">
			Выбери событие, <strong class="text-gray-900 dark:text-white">после</strong> которого будет
			размещено:
			<strong class="text-primary-600 dark:text-primary-400">{event.title}</strong>
		</p>

		<Search
			name="schedule_move_search"
			size="md"
			aria-label="Поиск события для переноса"
			placeholder="Поиск события…"
			autocomplete="off"
			spellcheck={false}
			clearable
			bind:value={query}
		/>
		<div
			class="max-h-48 overflow-y-auto rounded-lg border border-gray-200 sm:max-h-60 dark:border-gray-700"
		>
			{#each filtered as ev (ev.id)}
				<button
					type="button"
					class={[
						'w-full cursor-pointer px-3 py-2.5 text-left text-sm transition-colors hover:bg-primary-50 focus:outline-none focus-visible:bg-primary-50 focus-visible:ring-2 focus-visible:ring-primary-500 sm:py-3 sm:text-base dark:hover:bg-primary-900/20 dark:focus-visible:bg-primary-900/20',
						selectedId === ev.id && 'bg-primary-100 dark:bg-primary-900/40'
					]}
					onclick={() => handleSelect(ev)}
				>
					<span class="font-medium text-gray-900 dark:text-white">№{ev.public_number}</span>
					<span class="text-gray-600 dark:text-gray-400"> — {ev.title}</span>
				</button>
			{:else}
				<div class="px-3 py-4 text-center text-sm text-gray-400 sm:py-5 sm:text-base">
					Нет совпадений
				</div>
			{/each}
		</div>

		<Button
			type="button"
			onclick={handleSubmit}
			class="w-full py-3 text-base sm:py-4 sm:text-lg"
			size="lg"
			disabled={!selectedId}
		>
			Переместить
		</Button>
	</div>
</Modal>
