<script lang="ts">
	import type { ScheduleEventFullDTO } from '$lib/types/schedule';

	import { invalidate } from '$app/navigation';
	import { page } from '$app/state';
	import { createApiClient } from '$lib/api';
	import { getApiErrorDetail } from '$lib/api/errors';
	import { getToastService } from '$lib/services/toasts.svelte';
	import { createSearchIndex } from '$lib/utils/search';
	import { Alert, Button, Modal, Search, Spinner } from 'flowbite-svelte';
	import { ArrowUpDownOutline, BellActiveOutline } from 'flowbite-svelte-icons';

	const client = createApiClient();

	interface Props {
		open: boolean;
		event: ScheduleEventFullDTO;
	}

	let { open = $bindable(), event }: Props = $props();
	const toastService = getToastService();

	// The move picker searches the whole programme. It reads that off the route's
	// loaded schedule rather than a prop, so the full array isn't drilled through
	// every EventCard row just to reach this rarely-opened dialog. The cast is
	// needed because merged page.data is untyped; this dialog only ever mounts
	// under the schedule route, where the load supplies `schedule`.
	let schedule = $derived(page.data.schedule as ScheduleEventFullDTO[]);

	let query = $state('');
	let selectedId: string | null = $state(null);
	let formError = $state('');
	// Blocks re-entry while the move request is in flight. A move fans out an
	// irreversible push to every subscriber, so a double-tap on a slow venue cell
	// must not fire the request — and the mailing — twice.
	let isSubmitting = $state(false);

	// Reset the picker each time the modal opens so a cancelled selection never lingers.
	$effect(() => {
		if (open) {
			formError = '';
			selectedId = null;
			query = '';
			isSubmitting = false;
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
		if (!selectedId || isSubmitting) return;

		formError = '';
		isSubmitting = true;
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

			// Read-your-writes: refetch our own schedule off the successful response
			// rather than waiting for the schedule_updated SSE echo, which can arrive
			// late or be dropped on a flaky operator connection. See EventCard's
			// reloadSchedule for the full rationale.
			void invalidate('app:schedule');
			toastService.add('Выступление перенесено', 'success');

			open = false;
			selectedId = null;
			query = '';
		} catch (error) {
			console.error('Error moving event:', error);
			formError = 'Произошла непредвиденная ошибка при переносе';
		} finally {
			isSubmitting = false;
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
			<Alert color="red">
				{formError}
			</Alert>
		{/if}

		<p class="text-sm text-gray-600 sm:text-base dark:text-gray-400">
			Выбери выступление, <strong class="text-gray-900 dark:text-white">после</strong> которого
			разместить:
			<strong class="text-primary-600 dark:text-primary-400">{event.title}</strong>
		</p>

		<!-- Moving an event broadcasts a mailing to every subscriber. Push notifications cannot be recalled, so warn before sending. -->
		<Alert color="yellow">
			{#snippet icon()}
				<BellActiveOutline class="h-5 w-5 shrink-0" />
			{/snippet}
			Все подписчики получат уведомление. Пуш-уведомление нельзя будет отозвать.
		</Alert>

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
					{#if ev.number !== null}
						<span class="font-medium text-gray-900 dark:text-white">№{ev.number}</span>
						<span class="text-gray-600 dark:text-gray-400"> — {ev.title}</span>
					{:else}
						<!-- No number to lead with (a break), so the title carries the row. -->
						<span class="font-medium text-gray-900 dark:text-white">{ev.title}</span>
					{/if}
				</button>
			{:else}
				<div class="px-3 py-4 text-center text-sm text-gray-400 sm:py-5 sm:text-base">
					Нет совпадений
				</div>
			{/each}
		</div>
	</div>

	{#snippet footer()}
		<Button
			type="button"
			color="alternative"
			onclick={() => (open = false)}
			disabled={isSubmitting}
		>
			Отмена
		</Button>
		<Button type="button" onclick={handleSubmit} disabled={!selectedId || isSubmitting}>
			{#if isSubmitting}
				<Spinner size="4" class="me-2 fill-white" />
				Перенос…
			{:else}
				Перенести
			{/if}
		</Button>
	{/snippet}
</Modal>
