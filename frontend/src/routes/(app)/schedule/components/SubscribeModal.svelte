<script lang="ts">
	import { resolve } from '$app/paths';
	import { ParaglideMessage } from '@inlang/paraglide-js-svelte';
	import { BellRing, Minus, Plus } from '@lucide/svelte';
	import { createMutation, useQueryClient } from '@tanstack/svelte-query';

	import type { ScheduleEventFullDto } from '#lib/api/generated/index.js';
	import type { MessageTagProps } from '#lib/types/markup.js';

	import { getApiErrorDetail } from '#lib/api/errors.js';
	import {
		getSubscriptionsQueryKey,
		newSubscriptionMutation
	} from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import * as Alert from '#lib/components/ui/alert/index.js';
	import { Button } from '#lib/components/ui/button/index.js';
	import * as Dialog from '#lib/components/ui/dialog/index.js';
	import { m } from '#lib/paraglide/messages.js';
	import { getToastService } from '#lib/services/toasts.svelte.js';

	interface Props {
		open: boolean;
		event: ScheduleEventFullDto;
	}
	let { open = $bindable(), event }: Props = $props();
	const queryClient = useQueryClient();
	const toastService = getToastService();

	const subscribeMutation = createMutation(() => ({
		...newSubscriptionMutation(),
		onSuccess: () => queryClient.invalidateQueries({ queryKey: getSubscriptionsQueryKey() })
	}));

	// No reset on open: EventCard mounts this modal only while it is open.
	let counter = $state(5);
	let formError = $state('');

	// Clamp to the valid 1–100 range, snapping a cleared/NaN input back to the min
	// so +/- never dead-locks and submit never POSTs null.
	function setCounter(next: number) {
		counter = Number.isFinite(next) ? Math.max(1, Math.min(100, Math.floor(next))) : 1;
	}

	function handleSubmit() {
		setCounter(counter);
		formError = '';
		subscribeMutation.mutate(
			{ body: { event_id: event.id, counter } },
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

		{#if formError}
			<Alert.Root variant="destructive">
				<Alert.Description>{formError}</Alert.Description>
			</Alert.Root>
		{/if}

		<Dialog.Description>
			<ParaglideMessage message={m.subscribe_intro} inputs={{ title: event.title }}>
				{#snippet eventName({ children }: MessageTagProps)}
					<strong class="text-foreground">{@render children?.()}</strong>
				{/snippet}
			</ParaglideMessage>
		</Dialog.Description>

		<div class="my-4 flex items-center justify-center">
			<div
				class="flex -space-x-px overflow-hidden rounded-lg border border-border bg-card has-[input:focus-visible]:border-ring has-[input:focus-visible]:ring-3 has-[input:focus-visible]:ring-ring"
			>
				<button
					type="button"
					onclick={() => {
						setCounter(counter - 1);
						formError = '';
					}}
					class="flex h-11 w-12 items-center justify-center border-r border-border bg-muted/50 text-muted-foreground transition-colors hover:bg-muted disabled:cursor-not-allowed disabled:opacity-50"
					disabled={counter <= 1}
					aria-label={m.subscribe_decrease()}
				>
					<Minus class="size-5" />
				</button>

				<div class="relative flex h-11 w-44 flex-col items-center justify-center">
					<input
						name="subscription_counter"
						type="number"
						aria-label={m.subscribe_counter_label()}
						min="1"
						max="100"
						inputmode="numeric"
						autocomplete="off"
						bind:value={counter}
						onblur={() => setCounter(counter)}
						class="size-full border-0 bg-transparent pb-5 text-center font-bold text-foreground [-moz-appearance:textfield] focus:ring-0 focus:outline-none [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
					/>
					<div
						class="pointer-events-none absolute bottom-1 flex items-center text-xs text-muted-foreground select-none"
					>
						<span>{m.subscribe_counter_unit({ count: counter })}</span>
					</div>
				</div>

				<button
					type="button"
					onclick={() => {
						setCounter(counter + 1);
						formError = '';
					}}
					class="flex h-11 w-12 items-center justify-center border-l border-border bg-muted/50 text-muted-foreground transition-colors hover:bg-muted disabled:cursor-not-allowed disabled:opacity-50"
					disabled={counter >= 100}
					aria-label={m.subscribe_increase()}
				>
					<Plus class="size-5" />
				</button>
			</div>
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
