<script lang="ts">
	import { Undo2 } from '@lucide/svelte';
	import { createMutation, useQueryClient } from '@tanstack/svelte-query';

	import type {
		ScheduleChangeEntryDto,
		ScheduleChangeFullDto,
		ScheduleChangeType
	} from '#lib/api/generated/index.js';

	import {
		getScheduleQueryKey,
		listScheduleChangesQueryKey,
		undoScheduleChangeMutation
	} from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import { Badge } from '#lib/components/ui/badge/index.js';
	import { Button } from '#lib/components/ui/button/index.js';
	import * as Card from '#lib/components/ui/card/index.js';
	import { Spinner } from '#lib/components/ui/spinner/index.js';
	import { m } from '#lib/paraglide/messages.js';
	import { getToastService } from '#lib/services/toasts.svelte.js';
	import { offlineWriteGate } from '#lib/utils/offlineAction.js';

	interface Props {
		change: ScheduleChangeFullDto;
	}

	let { change }: Props = $props();

	const toastService = getToastService();
	const queryClient = useQueryClient();

	const offlineGate = offlineWriteGate();
	const undoMutation = createMutation(() => ({
		...undoScheduleChangeMutation(),
		onSuccess: () => {
			// Toasted here, not in a `mutate` callback: the refetched feed can drop or
			// re-key this card, and TanStack skips a call's callbacks once it unmounts.
			toastService.add(m.changes_cancelled(), 'success');
			// Read-your-writes, without waiting for the schedule_updated echo (see
			// EventStaffActions' reloadSchedule).
			void queryClient.invalidateQueries({ queryKey: getScheduleQueryKey() });
			return queryClient.invalidateQueries({ queryKey: listScheduleChangesQueryKey() });
		}
	}));

	function undoChange() {
		undoMutation.mutate(
			{ path: { schedule_change_id: change.id } },
			{ onError: (error) => toastService.error(error, m.changes_cancel_failed()) }
		);
	}

	const changeTypeLabels: Record<ScheduleChangeType, () => string> = {
		set_as_current: m.change_set_as_current,
		moved: m.change_moved,
		skipped: m.change_skipped,
		unskipped: m.change_unskipped
	};

	const changeTypeBadgeClasses: Record<ScheduleChangeType, string> = {
		set_as_current: 'border-success/30 bg-success/10 text-success',
		moved: 'border-info/30 bg-info/10 text-info',
		skipped: 'border-warning/30 bg-warning/10 text-warning',
		// "Restored" = back to normal, a neutral reset rather than a semantic state.
		unskipped: 'border-border bg-muted text-muted-foreground'
	};

	// A move records where the event stood before it, for undo: the entry it sat
	// right after, which is a block start when the event opened its block.
	let relatedLabel = $derived.by(() => {
		if (change.type !== 'moved') return m.change_related();
		if (change.related_entry?.type === 'block_start') return m.change_was_block_start();
		return m.change_was_after();
	});

	function formatEvent(event: ScheduleChangeEntryDto | null | undefined): string {
		if (!event) return '';
		// Breaks carry no public number — the title is all there is to show.
		if (event.number === null) return event.title;
		return `#${event.number} ${event.title}`;
	}
</script>

<Card.Root as="article" class="w-full max-w-none p-4">
	<div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
		<div class="flex-1">
			<div class="mb-2 flex flex-wrap items-center gap-2">
				<Badge variant="outline" class={['text-sm', changeTypeBadgeClasses[change.type]]}>
					{changeTypeLabels[change.type]()}
				</Badge>
				{#if change.next_event_changed}
					<Badge variant="destructive" class="text-sm">{m.change_announcement()}</Badge>
				{/if}
			</div>

			<div class="flex flex-col gap-1 text-sm">
				{#if change.changed_event}
					<p>
						<span class="font-bold text-muted-foreground">{m.change_event()}</span>
						<span class="text-foreground">
							{formatEvent(change.changed_event)}
						</span>
					</p>
				{/if}

				{#if change.related_entry}
					<p>
						<span class="font-bold text-muted-foreground">
							{relatedLabel}
						</span>
						<span class="text-foreground">
							{formatEvent(change.related_entry)}
						</span>
					</p>
				{/if}

				{#if change.user}
					<p>
						<span class="font-bold text-muted-foreground">{m.change_user()}</span>
						<span class="text-foreground">
							{change.user.username}
						</span>
					</p>
				{/if}

				{#if change.mailing_id}
					<p>
						<span class="font-bold text-muted-foreground">{m.change_mailing_id()}</span>
						<span class="text-foreground">
							{change.mailing_id}
						</span>
					</p>
				{/if}
			</div>
		</div>

		<div class="flex items-center gap-2 sm:shrink-0">
			<span class="text-xs text-muted-foreground">
				ID: {change.id}
			</span>
			<Button
				variant="outline"
				size="sm"
				onclick={offlineGate.guard(undoChange)}
				disabled={undoMutation.isPending}
				aria-disabled={offlineGate.blocked}
			>
				{#if undoMutation.isPending}
					<Spinner data-icon="inline-start" />
				{:else}
					<Undo2 data-icon="inline-start" />
				{/if}
				{m.change_revert()}
			</Button>
		</div>
	</div>
</Card.Root>
