<script lang="ts">
	import type { ScheduleEventFullDTO } from '$lib/types/schedule';

	import { invalidate } from '$app/navigation';
	import { page } from '$app/state';
	import { createApiClient } from '$lib/api';
	import { getApiErrorDetail } from '$lib/api/errors';
	import * as Alert from '$lib/components/ui/alert';
	import { Button } from '$lib/components/ui/button';
	import * as Dialog from '$lib/components/ui/dialog';
	import { Input } from '$lib/components/ui/input';
	import { Spinner } from '$lib/components/ui/spinner';
	import { getToastService } from '$lib/services/toasts.svelte';
	import { createSearchIndex } from '$lib/utils/search';
	import { ArrowUpDown, BellRing, Search as SearchIcon, X } from '@lucide/svelte';

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

<Dialog.Root bind:open>
	<Dialog.Content class="sm:max-w-md">
		<Dialog.Header>
			<Dialog.Title class="flex items-center gap-2">
				<ArrowUpDown class="size-5 text-muted-foreground" />
				Перенести выступление
			</Dialog.Title>
		</Dialog.Header>

		<div class="flex flex-col gap-4 sm:gap-5">
			{#if formError}
				<Alert.Root variant="destructive">
					<Alert.Description>{formError}</Alert.Description>
				</Alert.Root>
			{/if}

			<Dialog.Description class="sm:text-base">
				Выбери выступление, <strong class="text-foreground">после</strong> которого разместить:
				<strong class="text-primary">{event.title}</strong>
			</Dialog.Description>

			<!-- Moving an event broadcasts a mailing to every subscriber. Push notifications cannot be recalled, so warn before sending. -->
			<Alert.Root variant="warning">
				<BellRing class="shrink-0" />
				<Alert.Description>
					Все подписчики получат уведомление. Пуш-уведомление нельзя будет отозвать.
				</Alert.Description>
			</Alert.Root>

			<div class="relative flex items-center">
				<SearchIcon class="pointer-events-none absolute left-3 size-4 text-muted-foreground" />
				<Input
					name="schedule_move_search"
					aria-label="Поиск выступления для переноса"
					placeholder="Поиск выступления…"
					autocomplete="off"
					spellcheck={false}
					class="pr-8 pl-9"
					bind:value={query}
					oninput={() => (formError = '')}
				/>
				{#if query}
					<button
						type="button"
						class="absolute right-2 text-muted-foreground hover:text-foreground"
						onclick={() => (query = '')}
						aria-label="Очистить поиск"
					>
						<X class="size-4" />
					</button>
				{/if}
			</div>

			<div class="max-h-48 overflow-y-auto rounded-lg border border-border sm:max-h-60">
				{#each filtered as ev (ev.id)}
					<button
						type="button"
						class={[
							'w-full cursor-pointer px-3 py-2.5 text-left text-sm transition-colors hover:bg-primary/10 focus:outline-none focus-visible:bg-primary/10 focus-visible:ring-2 focus-visible:ring-primary sm:py-3 sm:text-base',
							selectedId === ev.id && 'bg-primary/20'
						]}
						onclick={() => handleSelect(ev)}
					>
						{#if ev.number !== null}
							<span class="font-medium text-foreground">№{ev.number}</span>
							<span class="text-muted-foreground"> — {ev.title}</span>
						{:else}
							<!-- No number to lead with (a break), so the title carries the row. -->
							<span class="font-medium text-foreground">{ev.title}</span>
						{/if}
					</button>
				{:else}
					<div class="px-3 py-4 text-center text-sm text-muted-foreground sm:py-5 sm:text-base">
						Нет совпадений
					</div>
				{/each}
			</div>
		</div>

		<Dialog.Footer class="flex flex-row justify-end gap-2">
			<Button
				type="button"
				variant="outline"
				onclick={() => (open = false)}
				disabled={isSubmitting}
			>
				Отмена
			</Button>
			<Button type="button" onclick={handleSubmit} disabled={!selectedId || isSubmitting}>
				{#if isSubmitting}
					<Spinner data-icon="inline-start" />
					Перенос…
				{:else}
					Перенести
				{/if}
			</Button>
		</Dialog.Footer>
	</Dialog.Content>
</Dialog.Root>
