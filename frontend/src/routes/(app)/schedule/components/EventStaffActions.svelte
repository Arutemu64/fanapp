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

	interface Props {
		event: ScheduleEventWithSubscription;
		isSkipped: boolean;
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

	type ConfirmConfig = {
		title: string;
		message: string;
		confirmLabel: string;
		color: 'primary' | 'red';
		notifyTone: 'warning' | 'muted';
		run: () => void;
	};
	let confirmOpen = $state(false);
	let confirmConfig = $state<ConfirmConfig | null>(null);

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

	function handleSkip(skip: boolean) {
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

{#if actionsOpen}
	<Dialog.Root bind:open={actionsOpen}>
		<Dialog.Content>
			<Dialog.Header>
				<Dialog.Title>{event.title}</Dialog.Title>
				<Dialog.Description>{m.event_manage_hint()}</Dialog.Description>
			</Dialog.Header>

			<div class="flex flex-col gap-1">
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

{#if moveModal}
	<MoveEventModal bind:open={moveModal} {event} />
{/if}

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
