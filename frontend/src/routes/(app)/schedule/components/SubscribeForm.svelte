<script lang="ts">
	import { resolve } from '$app/paths';
	import { BellRing, Minus, Plus } from '@lucide/svelte';
	import { createMutation, useQueryClient } from '@tanstack/svelte-query';

	import type { ScheduleEventFullDto } from '#lib/api/generated/index.js';

	import { getApiErrorDetail } from '#lib/api/errors.js';
	import {
		getSubscriptionsQueryKey,
		newSubscriptionMutation
	} from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import * as Alert from '#lib/components/ui/alert/index.js';
	import { Button } from '#lib/components/ui/button/index.js';
	import * as Dialog from '#lib/components/ui/dialog/index.js';
	import { getToastService } from '#lib/services/toasts.svelte.js';

	interface Props {
		event: ScheduleEventFullDto;
		onclose: () => void;
	}
	let { event, onclose }: Props = $props();
	const queryClient = useQueryClient();
	const toastService = getToastService();

	// The toast lives here, not in `mutate()`'s callbacks: those are dropped if the
	// dialog is dismissed while the request is in flight, which would lose the
	// confirmation of a subscription that was in fact created.
	const subscribeMutation = createMutation(() => ({
		...newSubscriptionMutation(),
		onSuccess: () => {
			toastService.add('Подписка оформлена', 'success');
			return queryClient.invalidateQueries({ queryKey: getSubscriptionsQueryKey() });
		}
	}));

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
				onSuccess: onclose,
				onError: (error) => {
					formError = getApiErrorDetail(error) ?? 'Не удалось оформить подписку';
				}
			}
		);
	}
</script>

<Dialog.Header>
	<Dialog.Title class="flex items-center gap-2">
		<BellRing class="size-5 text-muted-foreground" />
		Подписка на уведомления
	</Dialog.Title>
</Dialog.Header>

{#if formError}
	<Alert.Root variant="destructive">
		<Alert.Description>{formError}</Alert.Description>
	</Alert.Root>
{/if}

<Dialog.Description>
	За сколько выступлений до <strong class="text-foreground">{event.title}</strong>
	начать присылать тебе уведомления?
</Dialog.Description>

<div class="my-4 flex items-center justify-center">
	<div class="flex -space-x-px overflow-hidden rounded-lg border border-border bg-card">
		<button
			type="button"
			onclick={() => {
				setCounter(counter - 1);
				formError = '';
			}}
			class="flex h-11 w-12 items-center justify-center border-r border-border bg-muted/50 text-muted-foreground transition-colors hover:bg-muted disabled:cursor-not-allowed disabled:opacity-50"
			disabled={counter <= 1}
			aria-label="Уменьшить"
		>
			<Minus class="size-5" />
		</button>

		<div class="relative flex h-11 w-44 flex-col items-center justify-center">
			<input
				name="subscription_counter"
				type="number"
				aria-label="Сколько выступлений ждать до уведомления"
				min="1"
				max="100"
				inputmode="numeric"
				autocomplete="off"
				bind:value={counter}
				onblur={() => setCounter(counter)}
				class="h-full w-full border-0 bg-transparent pb-5 text-center font-bold text-foreground [-moz-appearance:textfield] focus:ring-0 focus:outline-none [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
			/>
			<div
				class="pointer-events-none absolute bottom-1 flex items-center text-xs text-muted-foreground select-none"
			>
				<span>выступлений</span>
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
			aria-label="Увеличить"
		>
			<Plus class="size-5" />
		</button>
	</div>
</div>

<p class="text-sm leading-relaxed text-muted-foreground">
	Напоминание придёт в уведомления — проверь, что они включены в <a
		href={resolve('profile/notifications')}
		class="font-medium text-primary hover:underline">профиле</a
	>.
</p>

<Dialog.Footer class="flex flex-row justify-end gap-2">
	<Button type="button" variant="outline" onclick={onclose}>Отмена</Button>
	<Button type="button" onclick={handleSubmit} disabled={subscribeMutation.isPending}
		>Подписаться</Button
	>
</Dialog.Footer>
