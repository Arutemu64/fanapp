<script lang="ts">
	import { Eye, EyeOff, Play, Shuffle, XCircle } from '@lucide/svelte';
	import { createMutation, useQueryClient } from '@tanstack/svelte-query';

	import type { ScheduleEventWithSubscription } from '#lib/types/schedule.js';

	import {
		getScheduleQueryKey,
		setEventAsCurrentMutation,
		uncheckCurrentEventMutation,
		updateScheduleEventMutation
	} from '#lib/api/generated/@tanstack/svelte-query.gen.js';
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
	// Staff-action labels, hoisted so each button's title stays a single ternary
	// (offline hint vs. action) rather than a nested one in the markup.
	let currentActionLabel = $derived(event.is_current ? 'Снять отметку' : 'Отметить текущим');
	let skipActionLabel = $derived(isSkipped ? 'Вернуть' : 'Пропустить');

	let moveModal = $state(false);

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
	// travels DB → outbox relay → NATS → SSE fan-out before it reaches us, and on a
	// flaky operator connection it can arrive late or be dropped — which would leave
	// the operator who made the change on a stale schedule while everyone else
	// already sees it. The refetch reads committed state (the write closed before
	// the 200), so it is correct even before the relay has ticked; the SSE echo
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
				onSuccess: () => toastService.add('Выступление отмечено как текущее', 'success'),
				onError: (error) => toastService.error(error)
			}
		);
	}

	function handleUnmarkCurrent() {
		unmarkCurrentMutation.mutate(
			{},
			{
				onSuccess: () => toastService.add('Отметка снята', 'success'),
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
					const toastMessage = skip
						? 'Выступление помечено как пропущенное'
						: 'Выступление возвращено в программу';
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
					title: 'Снять отметку',
					message: 'Снять отметку текущего выступления?',
					confirmLabel: 'Снять',
					color: 'primary',
					notifyTone: 'muted',
					run: handleUnmarkCurrent
				}
			: {
					title: 'Отметить текущим',
					message: `Отметить «${event.title}» как текущее выступление?`,
					confirmLabel: 'Отметить',
					color: 'primary',
					notifyTone: 'warning',
					run: handleMarkCurrent
				};
		confirmOpen = true;
	}

	function askToggleSkip() {
		confirmConfig = isSkipped
			? {
					title: 'Вернуть выступление',
					message: `Вернуть «${event.title}» в программу?`,
					confirmLabel: 'Вернуть',
					color: 'primary',
					notifyTone: 'muted',
					// Lock the direction to what the dialog shows now, so a concurrent
					// schedule_updated reload can't flip it before the staffer confirms.
					run: () => handleSkip(false)
				}
			: {
					title: 'Пропустить выступление',
					message: `Пропустить «${event.title}»? Оно будет помечено как пропущенное.`,
					confirmLabel: 'Пропустить',
					color: 'red',
					notifyTone: 'warning',
					run: () => handleSkip(true)
				};
		confirmOpen = true;
	}
</script>

<div class="mt-3 flex flex-wrap items-center justify-end gap-1.5 border-t border-border/50 pt-2.5">
	<!-- Icon-only staff actions: 44px square tap targets keep mobile usable while the strip stays compact on dense rows. Labels live in aria-label/title. -->
	<!-- Mark-current is the hot, repeated live-show action, so it carries a primary tint while move/skip stay quiet ghosts. -->
	<!-- Hidden on skipped events: a skipped event can't go on stage (backend rejects it), so don't offer the action. Still shown when it's somehow current, to keep the unmark affordance available. -->
	{#if event.is_current || !isSkipped}
		<button
			type="button"
			onclick={askToggleCurrent}
			disabled={offlineGate.disabled || isCurrentTogglePending}
			aria-label={currentActionLabel}
			title={offlineGate.disabled ? offlineGate.title : currentActionLabel}
			class="inline-flex h-11 w-11 items-center justify-center rounded-lg bg-primary/10 text-primary transition-colors hover:bg-primary/20 focus-visible:ring-2 focus-visible:ring-primary/50 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-40"
		>
			{#if event.is_current}
				<XCircle class="size-5" />
			{:else}
				<Play class="size-5" />
			{/if}
		</button>
	{/if}

	<button
		type="button"
		onclick={() => (moveModal = true)}
		disabled={offlineGate.disabled}
		aria-label="Перенести"
		title={offlineGate.disabled ? offlineGate.title : 'Перенести'}
		class="inline-flex h-11 w-11 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-accent hover:text-foreground focus-visible:ring-2 focus-visible:ring-primary/50 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-40"
	>
		<Shuffle class="size-5" />
	</button>

	<button
		type="button"
		onclick={askToggleSkip}
		disabled={offlineGate.disabled || skipMutation.isPending}
		aria-label={skipActionLabel}
		title={offlineGate.disabled ? offlineGate.title : skipActionLabel}
		class={[
			'inline-flex h-11 w-11 items-center justify-center rounded-lg transition-colors focus-visible:ring-2 focus-visible:ring-primary/50 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-40',
			isSkipped
				? 'text-muted-foreground hover:bg-accent hover:text-foreground'
				: 'text-destructive hover:bg-destructive/10'
		]}
	>
		{#if isSkipped}
			<Eye class="size-5" />
		{:else}
			<EyeOff class="size-5" />
		{/if}
	</button>
</div>

<!-- Mounted only while open, like EventCard's own dialogs: the strip renders once
	per schedule row for staff. -->
{#if moveModal}
	<MoveEventModal bind:open={moveModal} {event} />
{/if}

<!-- Shared confirm dialog for the staff strip's broadcast actions. -->
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
