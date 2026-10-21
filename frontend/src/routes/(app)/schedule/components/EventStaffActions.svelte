<script lang="ts">
	import CircleX from '@lucide/svelte/icons/circle-x';
	import Ellipsis from '@lucide/svelte/icons/ellipsis';
	import Eye from '@lucide/svelte/icons/eye';
	import EyeOff from '@lucide/svelte/icons/eye-off';
	import Play from '@lucide/svelte/icons/play';
	import Shuffle from '@lucide/svelte/icons/shuffle';
	import { createMutation, useQueryClient } from '@tanstack/svelte-query';

	import type { ScheduleEventWithSubscription } from '#lib/types/schedule.js';

	import {
		getScheduleQueryKey,
		setEventAsCurrentMutation,
		uncheckCurrentEventMutation,
		updateScheduleEventMutation
	} from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import { Button } from '#lib/components/ui/button/index.js';
	import * as Dialog from '#lib/components/ui/dialog/index.js';
	import { m } from '#lib/paraglide/messages.js';
	import { getToastService } from '#lib/services/toasts.svelte.js';
	import { offlineWriteGate } from '#lib/utils/offlineAction.js';

	import ConfirmActionModal from './ConfirmActionModal.svelte';
	import MoveEventModal from './MoveEventModal.svelte';

	// Its own component so the mutations exist only for staff: EventCard renders
	// once per schedule row, and every other viewer would pay for three unused
	// mutation observers per row.
	interface Props {
		event: ScheduleEventWithSubscription;
		isSkipped: boolean;
		// EventCard's override of `event.is_skipped`, so the whole row (strikethrough,
		// badge) reflects a skip before the schedule refetch confirms it.
		optimisticSkipped: boolean | null;
	}

	let { event, isSkipped, optimisticSkipped = $bindable() }: Props = $props();
	const queryClient = useQueryClient();
	const toastService = getToastService();

	const offlineGate = offlineWriteGate();
	let currentActionLabel = $derived(
		event.is_current ? m.event_staff_unmark() : m.event_staff_mark_current()
	);
	let skipActionLabel = $derived(isSkipped ? m.event_staff_restore() : m.event_staff_skip());

	let actionsOpen = $state(false);
	let moveModal = $state(false);

	function runFromSheet(action: () => void) {
		actionsOpen = false;
		action();
	}

	// Confirmation dialog for management actions. Each one broadcasts an
	// irreversible push, so the action only runs after the staffer confirms.
	type ConfirmConfig = {
		title: string;
		message: string;
		confirmLabel: string;
		color: 'primary' | 'red';
		// 'warning' for actions that push new info; 'muted' for reverting actions.
		notifyTone: 'warning' | 'muted';
		run: () => void;
	};
	// Two pieces of state, set together when a staff button is tapped:
	// confirmOpen drives the modal's visibility (bound two-way so Esc/backdrop
	// can close it), and confirmConfig holds what that modal should show.
	let confirmOpen = $state(false);
	let confirmConfig = $state<ConfirmConfig | null>(null);

	// Read-your-writes: after our own successful mutation, refetch straight off the
	// response instead of waiting for the schedule_updated SSE echo. That echo
	// travels DB → job worker → Valkey → SSE fan-out before it reaches us, and on a
	// flaky operator connection it can arrive late or be dropped — which would leave
	// the operator who made the change on a stale schedule while everyone else
	// already sees it. The refetch reads committed state (the write closed before
	// the 200), so it is correct even before the worker has run its job; the SSE echo
	// still drives every other client.
	function reloadSchedule() {
		void queryClient.invalidateQueries({ queryKey: getScheduleQueryKey() });
	}

	const markCurrentMutation = createMutation(() => ({
		...setEventAsCurrentMutation(),
		onSuccess: reloadSchedule
	}));
	const unmarkCurrentMutation = createMutation(() => ({
		...uncheckCurrentEventMutation(),
		onSuccess: reloadSchedule
	}));
	// Settled, not just succeeded: the skip is shown optimistically, and a failure
	// (another staffer's change raced it) must still resync the row.
	const skipMutation = createMutation(() => ({
		...updateScheduleEventMutation(),
		onSettled: reloadSchedule
	}));

	let isCurrentTogglePending = $derived(
		markCurrentMutation.isPending || unmarkCurrentMutation.isPending
	);

	function handleMarkCurrent() {
		markCurrentMutation.mutate(
			{ path: { event_id: event.id } },
			{
				onSuccess: () => toastService.add(m.event_marked_current_toast(), 'success'),
				onError: (error) => toastService.error(error)
			}
		);
	}

	function handleUnmarkCurrent() {
		unmarkCurrentMutation.mutate(
			{},
			{
				onSuccess: () => toastService.add(m.event_unmarked_toast(), 'success'),
				onError: (error) => toastService.error(error)
			}
		);
	}

	// `skip` is captured when the confirm dialog opens, not recomputed here: if
	// another staffer flips this event while the modal is open, the schedule_updated
	// reload could change `isSkipped` under us and make a generic toggle broadcast
	// the opposite action from what the dialog promised.
	function handleSkip(skip: boolean) {
		// Flip the row immediately; revert below if the request fails.
		optimisticSkipped = skip;

		skipMutation.mutate(
			{ path: { event_id: event.id }, body: { is_skipped: skip } },
			{
				onSuccess: () => {
					const toastMessage = skip ? m.event_skipped_toast() : m.event_restored_toast();
					toastService.add(toastMessage, 'success');
				},
				onError: (error) => {
					optimisticSkipped = null;
					toastService.error(error);
				}
			}
		);
	}

	function askToggleCurrent() {
		confirmConfig = event.is_current
			? {
					title: m.event_staff_unmark(),
					message: m.event_unmark_confirm(),
					confirmLabel: m.event_unmark_confirm_action(),
					color: 'primary',
					notifyTone: 'muted',
					run: handleUnmarkCurrent
				}
			: {
					title: m.event_staff_mark_current(),
					message: m.event_mark_current_confirm({ title: event.title }),
					confirmLabel: m.event_mark_current_confirm_action(),
					color: 'primary',
					notifyTone: 'warning',
					run: handleMarkCurrent
				};
		confirmOpen = true;
	}

	function askToggleSkip() {
		confirmConfig = isSkipped
			? {
					title: m.event_restore_title(),
					message: m.event_restore_confirm({ title: event.title }),
					confirmLabel: m.event_staff_restore(),
					color: 'primary',
					notifyTone: 'muted',
					// Lock the direction to what the dialog shows now, so a concurrent
					// schedule_updated reload can't flip it before the staffer confirms.
					run: () => handleSkip(false)
				}
			: {
					title: m.event_skip_title(),
					message: m.event_skip_confirm({ title: event.title }),
					confirmLabel: m.event_staff_skip(),
					color: 'red',
					notifyTone: 'warning',
					run: () => handleSkip(true)
				};
		confirmOpen = true;
	}
</script>

<!-- One ⋯ button beside the bell instead of an always-visible strip: these are
	occasional actions, and three icon buttons on every row crowded the list the whole
	audience reads. An overflow menu fits secondary, less frequent actions
	(https://www.nngroup.com/articles/contextual-menus/). -->
<button
	type="button"
	onclick={offlineGate.guard(() => (actionsOpen = true))}
	aria-disabled={offlineGate.blocked}
	aria-label={m.event_manage()}
	aria-haspopup="dialog"
	title={m.event_manage()}
	class="flex size-11 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-accent hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none aria-disabled:cursor-not-allowed aria-disabled:opacity-40"
>
	<Ellipsis class="size-5" />
</button>

<!-- A Dialog, so phones get the repo's bottom sheet and wider screens a centred
	dialog (docs/frontend.md). Mounted only while open: the button renders once per
	schedule row for staff. Each action closes the sheet before opening its own
	dialog, so two modals never stack. -->
{#if actionsOpen}
	<Dialog.Root bind:open={actionsOpen}>
		<Dialog.Content>
			<Dialog.Header>
				<Dialog.Title>{event.title}</Dialog.Title>
				<Dialog.Description>{m.event_manage_hint()}</Dialog.Description>
			</Dialog.Header>

			<div class="flex flex-col gap-1">
				<!-- Hidden on skipped events: a skipped event can't go on stage (backend rejects it), so don't offer the action. Still shown when it's somehow current, to keep the unmark affordance available. -->
				{#if event.is_current || !isSkipped}
					<Button
						variant="ghost"
						class="h-11 justify-start"
						disabled={isCurrentTogglePending}
						aria-disabled={offlineGate.blocked}
						onclick={offlineGate.guard(() => runFromSheet(askToggleCurrent))}
					>
						{#if event.is_current}
							<CircleX data-icon="inline-start" />
						{:else}
							<Play data-icon="inline-start" />
						{/if}
						{currentActionLabel}
					</Button>
				{/if}

				<Button
					variant="ghost"
					class="h-11 justify-start"
					aria-disabled={offlineGate.blocked}
					onclick={offlineGate.guard(() => runFromSheet(() => (moveModal = true)))}
				>
					<Shuffle data-icon="inline-start" />
					{m.event_move_action()}
				</Button>

				<Button
					variant="ghost"
					class={['h-11 justify-start', !isSkipped && 'text-destructive hover:text-destructive']}
					disabled={skipMutation.isPending}
					aria-disabled={offlineGate.blocked}
					onclick={offlineGate.guard(() => runFromSheet(askToggleSkip))}
				>
					{#if isSkipped}
						<Eye data-icon="inline-start" />
					{:else}
						<EyeOff data-icon="inline-start" />
					{/if}
					{skipActionLabel}
				</Button>
			</div>
		</Dialog.Content>
	</Dialog.Root>
{/if}

<!-- Mounted only while open, like EventCard's own dialogs: the menu renders once
	per schedule row for staff. -->
{#if moveModal}
	<MoveEventModal bind:open={moveModal} {event} />
{/if}

<!-- Shared confirm dialog for the broadcast actions. -->
{#if confirmOpen && confirmConfig}
	<ConfirmActionModal
		bind:open={confirmOpen}
		title={confirmConfig.title}
		message={confirmConfig.message}
		confirmLabel={confirmConfig.confirmLabel}
		confirmColor={confirmConfig.color}
		notifyTone={confirmConfig.notifyTone}
		onconfirm={() => confirmConfig?.run()}
	/>
{/if}
