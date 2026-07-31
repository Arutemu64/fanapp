<script lang="ts">
	import type { ScheduleEventFullDTO } from '$lib/types/schedule';

	import { createApiClient } from '$lib/api';
	import { getApiErrorDetail } from '$lib/api/errors';
	import NoticeCallout from '$lib/components/NoticeCallout.svelte';
	import { getToastService } from '$lib/services/toasts.svelte';
	import { createSearchIndex } from '$lib/utils/search';
	import { Alert, Button, Modal, Search } from 'flowbite-svelte';
	import { ArrowUpDownOutline, BellActiveOutline } from 'flowbite-svelte-icons';

	const client = createApiClient();

	// Sentinel for the "top of the programme" choice, which the API expresses as a
	// null `place_after_event_id`. Not a UUID, so it can never collide with an id.
	const TOP_OF_SCHEDULE = 'top';

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

	// Reset the picker each time the modal opens so a cancelled selection never lingers.
	$effect(() => {
		if (open) {
			formError = '';
			selectedId = null;
			query = '';
		}
	});

	// Shared matcher folds ё/е and matches space-separated tokens in any order.
	// Indexed once per schedule so typing through a few hundred events stays cheap.
	let searchIndex = $derived(
		createSearchIndex(schedule, (ev) => [ev.number, ev.title, ev.block_title, ev.nomination_title])
	);

	let filtered = $derived(searchIndex.filter(query));

	function handleSelect(ev: ScheduleEventFullDTO) {
		selectedId = selectedId === ev.id ? null : ev.id;
	}

	async function handleSubmit() {
		if (selectedId) {
			formError = '';
			try {
				const { error, response } = await client.PATCH('/schedule/{event_id}/move', {
					params: { path: { event_id: event.id } },
					body: {
						place_after_event_id: selectedId === TOP_OF_SCHEDULE ? null : selectedId
					}
				});

				if (error || !response.ok) {
					console.error('Error moving event:', error);
					formError = getApiErrorDetail(error) ?? 'Не удалось перенести выступление';
					return;
				}

				toastService.add('Выступление перенесено', 'success');

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

<Modal bind:open size="sm">
	{#snippet header()}
		<div class="flex items-center gap-2">
			<ArrowUpDownOutline class="h-5 w-5 text-gray-500 dark:text-gray-400" />
			<h3 class="text-lg font-bold text-gray-900 dark:text-white">Перенести выступление</h3>
		</div>
	{/snippet}

	<div class="flex flex-col gap-4 sm:gap-5">
		{#if formError}
			<Alert color="red" class="rounded-xl text-sm">
				{formError}
			</Alert>
		{/if}

		<p class="text-sm text-gray-600 sm:text-base dark:text-gray-400">
			Куда перенести:
			<strong class="text-primary-600 dark:text-primary-400">{event.title}</strong>
		</p>

		<!-- The top of the programme has no anchor event to search for, so it is its
		     own control above the picker rather than a row that search could hide. -->
		<button
			type="button"
			aria-pressed={selectedId === TOP_OF_SCHEDULE}
			class={[
				'w-full cursor-pointer rounded-lg border px-3 py-2.5 text-left text-sm font-medium transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 sm:py-3 sm:text-base',
				selectedId === TOP_OF_SCHEDULE
					? 'border-primary-500 bg-primary-100 text-primary-900 dark:bg-primary-900/40 dark:text-primary-100'
					: 'border-gray-200 text-gray-900 hover:bg-primary-50 dark:border-gray-700 dark:text-white dark:hover:bg-primary-900/20'
			]}
			onclick={() => (selectedId = selectedId === TOP_OF_SCHEDULE ? null : TOP_OF_SCHEDULE)}
		>
			В начало программы
		</button>

		<p class="text-sm text-gray-600 sm:text-base dark:text-gray-400">
			Или выбери выступление, <strong class="text-gray-900 dark:text-white">после</strong> которого его
			разместить:
		</p>

		<!-- Moving an event broadcasts a mailing to every subscriber. Push notifications cannot be recalled, so warn before sending. -->
		<NoticeCallout
			tone="warning"
			icon={BellActiveOutline}
			message="Все подписчики получат уведомление. Пуш-уведомление нельзя будет отозвать."
			role="alert"
		/>

		<Search
			name="schedule_move_search"
			size="md"
			aria-label="Поиск выступления для переноса"
			placeholder="Поиск выступления…"
			autocomplete="off"
			spellcheck={false}
			clearable
			bind:value={query}
			oninput={() => (formError = '')}
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
					<span class="font-medium text-gray-900 dark:text-white">№{ev.number}</span>
					<span class="text-gray-600 dark:text-gray-400"> — {ev.title}</span>
				</button>
			{:else}
				<div class="px-3 py-4 text-center text-sm text-gray-400 sm:py-5 sm:text-base">
					Нет совпадений
				</div>
			{/each}
		</div>
	</div>

	{#snippet footer()}
		<Button type="button" color="alternative" onclick={() => (open = false)}>Отмена</Button>
		<Button type="button" onclick={handleSubmit} disabled={!selectedId}>Перенести</Button>
	{/snippet}
</Modal>
