<script lang="ts">
	import { Button, Modal, Search } from 'flowbite-svelte';
	import { ShuffleOutline } from 'flowbite-svelte-icons';
	import type { ScheduleEventDTO } from '$lib/types/schedule';
	import { api } from '$lib/api';
	import { toastService } from '$lib/stores/toasts.svelte';

	interface Props {
		open: boolean;
		event: ScheduleEventDTO;
		schedule: ScheduleEventDTO[];
	}

	let { open = $bindable(), event, schedule }: Props = $props();

	let query = $state('');
	let selectedId: number | null = $state(null);

	let filtered = $derived(
		schedule.filter((ev) => {
			const q = query.toLowerCase();
			return (
				ev.public_id.toString().toLowerCase().includes(q) ||
				ev.title.toLowerCase().includes(q) ||
				ev.block_title?.toLowerCase().includes(q) ||
				ev.nomination_title?.toLowerCase().includes(q)
			);
		})
	);

	function handleSelect(ev: ScheduleEventDTO) {
		selectedId = selectedId === ev.id ? null : ev.id;
	}

	async function handleSubmit() {
		if (selectedId) {
			try {
				await api.post('/schedule/move', {
					event_id: event.id,
					place_after_event_id: selectedId
				});
				const selectedEvent = schedule.find((e) => e.id === selectedId);
				console.log('Move event after:', selectedEvent?.title);
				toastService.add('Выступление перенесено', 'success');
			} catch (error) {
				console.error('Error moving event:', error);
				toastService.error(error);
			} finally {
				open = false;
				selectedId = null;
				query = '';
			}
		}
	}
</script>

<Modal bind:open size="sm" title="Переместить событие" class="px-2">
	<div class="flex flex-col gap-4 sm:gap-5">
		<p class="text-sm text-gray-600 sm:text-base dark:text-gray-400">
			Выберите событие, <strong class="text-gray-900 dark:text-white">после</strong> которого будет
			размещено:
			<strong class="text-primary-600 dark:text-primary-400">{event.title}</strong>
		</p>

		<Search size="md" placeholder="Поиск..." clearable bind:value={query} />

		<div
			class="max-h-48 overflow-y-auto rounded-lg border border-gray-200 sm:max-h-60 dark:border-gray-700"
		>
			{#each filtered as ev (ev.id)}
				<button
					type="button"
					class="w-full cursor-pointer px-3 py-2.5 text-left text-sm transition-colors hover:bg-blue-50 sm:py-3 sm:text-base dark:hover:bg-blue-900/20 {selectedId ===
					ev.id
						? 'bg-blue-100 dark:bg-blue-900/40'
						: ''}"
					onclick={() => handleSelect(ev)}
				>
					<span class="font-medium text-gray-900 dark:text-white">№{ev.public_id}</span>
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
			<span class="flex items-center justify-center gap-2">
				<ShuffleOutline class="h-5 w-5 sm:h-6 sm:w-6" />
				Переместить
			</span>
		</Button>
	</div>
</Modal>
