<script lang="ts">
	import { ParaglideMessage } from '@inlang/paraglide-js-svelte';
	import { ArrowUpDown, BellRing, Search as SearchIcon, X } from '@lucide/svelte';
	import { createMutation, createQuery, useQueryClient } from '@tanstack/svelte-query';

	import type { ScheduleEntryDto, ScheduleEventFullDto } from '#lib/api/generated/index.js';
	import type { MessageTagProps } from '#lib/types/markup.js';

	import { getApiErrorDetail } from '#lib/api/errors.js';
	import {
		getScheduleOptions,
		getScheduleQueryKey,
		moveScheduleEventMutation
	} from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import * as Alert from '#lib/components/ui/alert/index.js';
	import { Button } from '#lib/components/ui/button/index.js';
	import * as Dialog from '#lib/components/ui/dialog/index.js';
	import { Input } from '#lib/components/ui/input/index.js';
	import { Spinner } from '#lib/components/ui/spinner/index.js';
	import { m } from '#lib/paraglide/messages.js';
	import { getToastService } from '#lib/services/toasts.svelte.js';
	import { blockTitleByEventId } from '#lib/utils/scheduleData.js';
	import { createSearchIndex } from '#lib/utils/search.js';

	interface Props {
		open: boolean;
		event: ScheduleEventFullDto;
	}

	let { open = $bindable(), event }: Props = $props();
	const queryClient = useQueryClient();
	const toastService = getToastService();

	// The move picker searches the whole programme. It reads that off the cached
	// schedule query rather than a prop, so the full array isn't drilled through
	// every EventCard row just to reach this rarely-opened dialog.
	const scheduleQuery = createQuery(() => getScheduleOptions());
	let schedule = $derived(scheduleQuery.data?.schedule ?? []);

	// Read-your-writes: refetch our own schedule off the successful response
	// rather than waiting for the schedule_updated SSE echo, which can arrive
	// late or be dropped on a flaky operator connection. See EventStaffActions'
	// reloadSchedule for the full rationale.
	const moveMutation = createMutation(() => ({
		...moveScheduleEventMutation(),
		onSuccess: () => void queryClient.invalidateQueries({ queryKey: getScheduleQueryKey() })
	}));

	// No reset on open: EventStaffActions mounts this modal only while it is open,
	// so a cancelled selection never lingers.
	let query = $state('');
	let selectedId: string | null = $state(null);
	let formError = $state('');
	// Blocks re-entry while the move request is in flight. A move fans out an
	// irreversible push to every subscriber, so a double-tap on a slow venue cell
	// must not fire the request — and the mailing — twice.
	let isSubmitting = $derived(moveMutation.isPending);

	// Shared matcher folds ё/е and matches space-separated tokens in any order.
	// Indexed once per schedule so typing through a few hundred events stays cheap.
	// Block starts are targets too: placing an event after one moves it to the
	// top of that block, which is how an event changes blocks.
	let searchIndex = $derived.by(() => {
		const blockTitles = blockTitleByEventId(schedule);
		return createSearchIndex(schedule, (entry) => {
			if (entry.type === 'block_start') return [entry.title];
			return [entry.number, entry.title, blockTitles.get(entry.id), entry.nomination_title];
		});
	});

	let filtered = $derived(searchIndex.filter(query));

	function handleSelect(entry: ScheduleEntryDto) {
		selectedId = selectedId === entry.id ? null : entry.id;
	}

	function handleSubmit() {
		if (!selectedId || isSubmitting) return;

		formError = '';
		moveMutation.mutate(
			{ path: { event_id: event.id }, body: { place_after_entry_id: selectedId } },
			{
				onSuccess: () => {
					toastService.add(m.event_moved_toast(), 'success');
					open = false;
					selectedId = null;
					query = '';
				},
				onError: (error) => {
					formError = getApiErrorDetail(error) ?? m.event_move_failed();
				}
			}
		);
	}
</script>

<Dialog.Root bind:open>
	<Dialog.Content class="sm:max-w-md">
		<Dialog.Header>
			<Dialog.Title class="flex items-center gap-2">
				<ArrowUpDown class="size-5 text-muted-foreground" />
				{m.event_move_title()}
			</Dialog.Title>
		</Dialog.Header>

		<div class="flex flex-col gap-4 sm:gap-5">
			{#if formError}
				<Alert.Root variant="destructive">
					<Alert.Description>{formError}</Alert.Description>
				</Alert.Root>
			{/if}

			<Dialog.Description class="sm:text-base">
				<ParaglideMessage message={m.event_move_choose} inputs={{ title: event.title }}>
					{#snippet strong({ children }: MessageTagProps)}
						<strong class="text-foreground">{@render children?.()}</strong>
					{/snippet}
					{#snippet eventName({ children }: MessageTagProps)}
						<strong class="text-primary">{@render children?.()}</strong>
					{/snippet}
				</ParaglideMessage>
			</Dialog.Description>

			<!-- Moving an event sends a change announcement to every subscriber. Push notifications cannot be recalled, so warn before sending. -->
			<Alert.Root variant="warning">
				<BellRing class="shrink-0" />
				<Alert.Description>
					{m.confirm_notify_push_warning()}
				</Alert.Description>
			</Alert.Root>

			<div class="relative flex items-center">
				<SearchIcon class="pointer-events-none absolute left-3 size-4 text-muted-foreground" />
				<Input
					name="schedule_move_search"
					aria-label={m.event_move_search_label()}
					placeholder={m.event_move_search_placeholder()}
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
						aria-label={m.common_clear_search()}
					>
						<X class="size-4" />
					</button>
				{/if}
			</div>

			<div class="max-h-48 overflow-y-auto rounded-lg border border-border sm:max-h-60">
				{#each filtered as entry (entry.id)}
					<button
						type="button"
						class={[
							'w-full cursor-pointer px-3 py-2.5 text-left text-sm transition-colors hover:bg-primary/10 focus:outline-none focus-visible:bg-primary/10 focus-visible:ring-2 focus-visible:ring-primary sm:py-3 sm:text-base',
							entry.type === 'block_start' && 'bg-muted/60',
							selectedId === entry.id && 'bg-primary/20'
						]}
						onclick={() => handleSelect(entry)}
					>
						{#if entry.type === 'block_start'}
							<span class="text-muted-foreground">{m.event_move_to_block_start()} </span>
							<span class="font-semibold text-foreground">{entry.title}</span>
						{:else if entry.number !== null}
							<span class="font-medium text-foreground">№{entry.number}</span>
							<span class="text-muted-foreground"> — {entry.title}</span>
						{:else}
							<!-- No number to lead with (a break), so the title carries the row. -->
							<span class="font-medium text-foreground">{entry.title}</span>
						{/if}
					</button>
				{:else}
					<div class="px-3 py-4 text-center text-sm text-muted-foreground sm:py-5 sm:text-base">
						{m.event_move_no_matches()}
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
				{m.common_cancel()}
			</Button>
			<Button type="button" onclick={handleSubmit} disabled={!selectedId || isSubmitting}>
				{#if isSubmitting}
					<Spinner data-icon="inline-start" />
					{m.event_moving()}
				{:else}
					{m.event_move_action()}
				{/if}
			</Button>
		</Dialog.Footer>
	</Dialog.Content>
</Dialog.Root>
