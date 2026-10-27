<script lang="ts">
	import { ParaglideMessage } from '@inlang/paraglide-js-svelte';
	import ArrowUpDown from '@lucide/svelte/icons/arrow-up-down';
	import BellRing from '@lucide/svelte/icons/bell-ring';
	import { createMutation, createQuery, useQueryClient } from '@tanstack/svelte-query';

	import type { ScheduleEventFullDto } from '#lib/api/generated/index.js';
	import type { MessageTagProps } from '#lib/types/markup.js';

	import { getApiErrorDetail } from '#lib/api/errors.js';
	import {
		getScheduleOptions,
		getScheduleQueryKey,
		updateScheduleEventMutation
	} from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import FormError from '#lib/components/FormError.svelte';
	import SearchInput from '#lib/components/SearchInput.svelte';
	import * as Alert from '#lib/components/ui/alert/index.js';
	import { Button } from '#lib/components/ui/button/index.js';
	import * as Dialog from '#lib/components/ui/dialog/index.js';
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

	const scheduleQuery = createQuery(() => getScheduleOptions());
	let schedule = $derived(scheduleQuery.data?.entries ?? []);

	const moveMutation = createMutation(() => ({
		...updateScheduleEventMutation(),
		onSuccess: () => void queryClient.invalidateQueries({ queryKey: getScheduleQueryKey() })
	}));

	let query = $state('');
	// `afterId: null` is the top of the schedule; `target: null` is nothing picked yet.
	let target: { afterId: string | null } | null = $state(null);
	let formError = $state('');
	let isSubmitting = $derived(moveMutation.isPending);

	let searchIndex = $derived.by(() => {
		const blockTitles = blockTitleByEventId(schedule);
		return createSearchIndex(schedule, (entry) => {
			if (entry.type === 'block_start') return [entry.title];
			return [entry.number, entry.title, blockTitles.get(entry.id), entry.nomination_title];
		});
	});

	let filtered = $derived(searchIndex.filter(query));

	const rowClass =
		'w-full cursor-pointer px-3 py-2.5 text-left text-body transition-colors hover:bg-primary/10 focus:outline-none focus-visible:bg-primary/10 focus-visible:ring-2 focus-visible:ring-primary sm:py-3';

	function handleSelect(afterId: string | null) {
		target = target?.afterId === afterId ? null : { afterId };
	}

	function handleSubmit() {
		if (!target || isSubmitting) return;

		formError = '';
		moveMutation.mutate(
			{ path: { event_id: event.id }, body: { place_after_entry_id: target.afterId } },
			{
				onSuccess: () => {
					toastService.add(m.event_moved_toast(), 'success');
					open = false;
					target = null;
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
			<FormError message={formError} />

			<Dialog.Description class="text-body">
				<ParaglideMessage message={m.event_move_choose} inputs={{ title: event.title }}>
					{#snippet strong({ children }: MessageTagProps)}
						<strong class="text-foreground">{@render children?.()}</strong>
					{/snippet}
					{#snippet eventName({ children }: MessageTagProps)}
						<strong class="text-primary">{@render children?.()}</strong>
					{/snippet}
				</ParaglideMessage>
			</Dialog.Description>

			<Alert.Root variant="warning">
				<BellRing class="shrink-0" />
				<Alert.Description>
					{m.confirm_notify_push_warning()}
				</Alert.Description>
			</Alert.Root>

			<SearchInput
				bind:value={query}
				name="schedule_move_search"
				label={m.event_move_search_label()}
				placeholder={m.event_move_search_placeholder()}
				oninput={() => (formError = '')}
			/>

			<div class="max-h-48 overflow-y-auto rounded-lg border border-border sm:max-h-60">
				{#if !query}
					<button
						type="button"
						class={[rowClass, 'bg-muted/60', target?.afterId === null && 'bg-primary/20']}
						onclick={() => handleSelect(null)}
					>
						<span class="font-semibold text-foreground">{m.event_move_to_schedule_start()}</span>
					</button>
				{/if}
				{#each filtered as entry (entry.id)}
					<button
						type="button"
						class={[
							rowClass,
							entry.type === 'block_start' && 'bg-muted/60',
							target?.afterId === entry.id && 'bg-primary/20'
						]}
						onclick={() => handleSelect(entry.id)}
					>
						{#if entry.type === 'block_start'}
							<span class="text-muted-foreground">{m.event_move_to_block_start()} </span>
							<span class="font-semibold text-foreground">{entry.title}</span>
						{:else if entry.number !== null}
							<span class="font-medium text-foreground">№{entry.number}</span>
							<span class="text-muted-foreground"> — {entry.title}</span>
						{:else}
							<span class="font-medium text-foreground">{entry.title}</span>
						{/if}
					</button>
				{:else}
					<div class="px-3 py-4 text-center text-body text-muted-foreground sm:py-5">
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
			<Button type="button" onclick={handleSubmit} disabled={!target || isSubmitting}>
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
