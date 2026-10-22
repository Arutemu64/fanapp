<script lang="ts">
	import { resolve } from '$app/paths';
	import { ParaglideMessage } from '@inlang/paraglide-js-svelte';
	import BellRing from '@lucide/svelte/icons/bell-ring';
	import { createMutation } from '@tanstack/svelte-query';

	import type { ScheduleEventFullDto } from '#lib/api/generated/index.js';
	import type { MessageTagProps } from '#lib/types/markup.js';

	import { getApiErrorDetail } from '#lib/api/errors.js';
	import { handOffWhenQueued } from '#lib/api/queuedWrite.svelte.js';
	import { queuedSubscribeOptions } from '#lib/api/writeQueue.js';
	import FormError from '#lib/components/FormError.svelte';
	import { Button } from '#lib/components/ui/button/index.js';
	import * as Dialog from '#lib/components/ui/dialog/index.js';
	import * as ToggleGroup from '#lib/components/ui/toggle-group/index.js';
	import { m } from '#lib/paraglide/messages.js';
	import { getToastService } from '#lib/services/toasts.svelte.js';

	interface Props {
		open: boolean;
		event: ScheduleEventFullDto;
	}
	let { open = $bindable(), event }: Props = $props();
	const toastService = getToastService();

	// Queued (ADR-0038): offline it waits for the connection, shown on the card in
	// the meantime, and the subscription list refreshes when it lands.
	const subscribeMutation = createMutation(() => queuedSubscribeOptions(event.id));
	handOffWhenQueued(subscribeMutation, () => {
		toastService.add(m.subscribe_queued(), 'info');
		open = false;
	});

	// A few fixed choices rather than a free number: the minutes are an estimate
	// from planned durations, so finer steps would promise precision it lacks.
	const LEAD_MINUTE_OPTIONS = [10, 15, 30, 60];

	// No reset on open: EventCard mounts this modal only while it is open.
	let leadMinutes = $state(15);
	let formError = $state('');

	// Fully controlled, like the schedule's scope switch: a single-select toggle
	// group clears its value when the pressed item is tapped again, and the
	// setter ignores that so one option always stays chosen
	// (https://bits-ui.com/docs/components/toggle-group).
	function getLeadMinutes() {
		return String(leadMinutes);
	}

	function setLeadMinutes(value: string) {
		if (value === '') return;
		leadMinutes = Number(value);
		formError = '';
	}

	function handleSubmit() {
		formError = '';
		subscribeMutation.mutate(
			{ body: { event_id: event.id, lead_minutes: leadMinutes } },
			{
				onSuccess: () => {
					toastService.add(m.subscribe_done(), 'success');
					open = false;
				},
				onError: (error) => {
					formError = getApiErrorDetail(error) ?? m.subscribe_failed();
				}
			}
		);
	}
</script>

<Dialog.Root bind:open>
	<Dialog.Content class="sm:max-w-md">
		<Dialog.Header>
			<Dialog.Title class="flex items-center gap-2">
				<BellRing class="size-5 text-muted-foreground" />
				{m.subscribe_title()}
			</Dialog.Title>
		</Dialog.Header>

		<FormError message={formError} />

		<Dialog.Description>
			<ParaglideMessage message={m.subscribe_intro} inputs={{ title: event.title }}>
				{#snippet eventName({ children }: MessageTagProps)}
					<strong class="text-foreground">{@render children?.()}</strong>
				{/snippet}
			</ParaglideMessage>
		</Dialog.Description>

		<div class="my-2 flex flex-col gap-2">
			<ToggleGroup.Root
				type="single"
				variant="outline"
				class="w-full"
				bind:value={getLeadMinutes, setLeadMinutes}
				aria-label={m.subscribe_lead_label()}
			>
				{#each LEAD_MINUTE_OPTIONS as minutes (minutes)}
					<ToggleGroup.Item value={String(minutes)} class="h-11 flex-1">
						{m.subscribe_lead_option({ count: minutes })}
					</ToggleGroup.Item>
				{/each}
			</ToggleGroup.Root>
			<p class="text-sm leading-relaxed text-muted-foreground">{m.subscribe_estimate_note()}</p>
		</div>

		<p class="text-sm leading-relaxed text-muted-foreground">
			<ParaglideMessage message={m.subscribe_hint}>
				{#snippet link({ children }: MessageTagProps)}
					<a
						href={resolve('profile/notifications')}
						class="font-medium text-primary hover:underline">{@render children?.()}</a
					>
				{/snippet}
			</ParaglideMessage>
		</p>

		<Dialog.Footer class="flex flex-row justify-end gap-2">
			<Button type="button" variant="outline" onclick={() => (open = false)}
				>{m.common_cancel()}</Button
			>
			<Button type="button" onclick={handleSubmit} disabled={subscribeMutation.isPending}
				>{m.common_subscribe()}</Button
			>
		</Dialog.Footer>
	</Dialog.Content>
</Dialog.Root>
