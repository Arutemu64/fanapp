<script lang="ts">
	import { createMutation, useQueryClient } from '@tanstack/svelte-query';

	import type { ScheduleEventFullDto } from '#lib/api/generated/index.js';

	import {
		getScheduleQueryKey,
		moveScheduleEventMutation
	} from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import * as Dialog from '#lib/components/ui/dialog/index.js';
	import { getToastService } from '#lib/services/toasts.svelte.js';

	import MoveEventForm from './MoveEventForm.svelte';

	interface Props {
		open: boolean;
		event: ScheduleEventFullDto;
	}

	let { open = $bindable(), event }: Props = $props();
	const queryClient = useQueryClient();
	const toastService = getToastService();

	// The request is owned here, not by the form, so it outlives the form: a move
	// fans out an irreversible push to every subscriber, so dismissing the dialog
	// mid-flight must neither lose the confirmation toast nor let a reopened form
	// fire a second request — and a second mailing. `isPending` stays true across
	// reopens; the toast is an options-level callback because the per-call ones are
	// dropped once the form is gone.
	// Read-your-writes: refetch our own schedule off the successful response
	// rather than waiting for the schedule_updated SSE echo, which can arrive
	// late or be dropped on a flaky operator connection. See EventStaffActions'
	// reloadSchedule for the full rationale.
	const moveMutation = createMutation(() => ({
		...moveScheduleEventMutation(),
		onSuccess: () => {
			toastService.add('Выступление перенесено', 'success');
			void queryClient.invalidateQueries({ queryKey: getScheduleQueryKey() });
		}
	}));

	function move(
		placeAfterEventId: string,
		handlers: { onSuccess: () => void; onError: (error: unknown) => void }
	) {
		moveMutation.mutate(
			{ path: { event_id: event.id }, body: { place_after_event_id: placeAfterEventId } },
			handlers
		);
	}
</script>

<!-- The form owns the picker state and mounts with the dialog content, so every
     open starts with no selection or search without an effect to reset it. -->
<Dialog.Root bind:open>
	<Dialog.Content class="sm:max-w-md">
		<MoveEventForm
			{event}
			isSubmitting={moveMutation.isPending}
			onmove={move}
			onclose={() => (open = false)}
		/>
	</Dialog.Content>
</Dialog.Root>
