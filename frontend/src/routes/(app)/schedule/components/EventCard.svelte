<script lang="ts">
	import Ban from '@lucide/svelte/icons/ban';
	import Bell from '@lucide/svelte/icons/bell';
	import BellRing from '@lucide/svelte/icons/bell-ring';
	import Clock from '@lucide/svelte/icons/clock';
	import CloudOff from '@lucide/svelte/icons/cloud-off';
	import Hourglass from '@lucide/svelte/icons/hourglass';

	import type { CurrentUserDto } from '#lib/api/generated/index.js';
	import type { ScheduleEventWithSubscription } from '#lib/types/schedule.js';

	import NumberBadge from '#lib/components/NumberBadge.svelte';
	import { Badge } from '#lib/components/ui/badge/index.js';
	import { m } from '#lib/paraglide/messages.js';
	import { getToastService } from '#lib/services/toasts.svelte.js';
	import { formatDuration, formatEventNumber, formatUntil } from '#lib/utils/formatters.js';
	import { canManageSchedule } from '#lib/utils/permissions.js';

	import EventStaffActions from './EventStaffActions.svelte';
	import SubscribeModal from './SubscribeModal.svelte';
	import UnsubscribeModal from './UnsubscribeModal.svelte';

	interface Props {
		event: ScheduleEventWithSubscription;
		currentEvent: ScheduleEventWithSubscription | null;
		user: CurrentUserDto | null;
		secondsAhead?: number | null;
		variant?: 'default' | 'interlude';
	}

	let { event, currentEvent, user, secondsAhead = null, variant = 'default' }: Props = $props();
	const toastService = getToastService();

	let subscribeModal = $state(false);
	let unsubscribeModal = $state(false);

	let eventNumber = $derived(formatEventNumber(event.number));

	let optimisticSkipped = $state<boolean | null>(null);
	let isSkipped = $derived(optimisticSkipped ?? event.is_skipped);

	$effect(() => {
		if (optimisticSkipped !== null && event.is_skipped === optimisticSkipped) {
			optimisticSkipped = null;
		}
	});

	function aheadOf(value: number | null, currentValue: number | null): number | null {
		if (value === null || currentValue === null) return null;
		const diff = value - currentValue;
		return diff >= 0 ? diff : null;
	}

	let actsAhead = $derived(currentEvent ? aheadOf(event.position, currentEvent.position) : null);

	let untilLabel = $derived.by(() => {
		if (actsAhead === null || actsAhead <= 0) return null;
		return formatUntil(actsAhead, secondsAhead ?? 0);
	});

	function handleSubscribe() {
		if (!user) {
			toastService.add(m.event_subscribe_login_required(), 'error');
			return;
		}
		subscribeModal = true;
	}

	function handleUnsubscribe() {
		unsubscribeModal = true;
	}
</script>

<div
	class={[
		'flex items-start gap-3 px-3 py-4 transition-colors sm:px-4',
		event.is_current && 'bg-success/10',
		isSkipped && !event.is_current && 'bg-muted/50'
	]}
>
	{#if variant === 'default'}
		{#if eventNumber !== null}
			<NumberBadge number={eventNumber} highlighted={event.is_current} />
		{:else}
			<div class="w-12 shrink-0" aria-hidden="true"></div>
		{/if}
	{/if}

	<div class="min-w-0 flex-1">
		<div class="flex items-start gap-2">
			<div class="min-w-0 flex-1">
				<h3
					class={[
						'text-base leading-snug font-semibold text-foreground',
						isSkipped && 'line-through'
					]}
				>
					{event.title}
				</h3>

				{#if event.is_current || isSkipped}
					<div class="mt-1.5 flex flex-wrap items-center gap-1.5">
						{#if event.is_current}
							<Badge
								variant="outline"
								class="inline-flex items-center gap-1.5 border-success/30 bg-success/10 px-2 py-0.5 text-xs font-medium text-success"
							>
								<span class="relative flex size-2" aria-hidden="true">
									<span
										class="absolute inline-flex size-full animate-ping-brief rounded-full bg-success opacity-75"
									></span>
									<span class="relative inline-flex size-2 rounded-full bg-success"></span>
								</span>
								{m.common_now()}
							</Badge>
						{/if}

						{#if isSkipped}
							<Badge
								variant="destructive"
								class="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium"
							>
								<Ban class="size-3.5" />
								{m.schedule_status_skipped()}
							</Badge>
						{/if}
					</div>
				{/if}

				<div class="mt-1.5 flex flex-wrap items-center gap-x-2 gap-y-1">
					<span class="inline-flex items-start gap-1 text-xs font-medium text-muted-foreground">
						<Clock class="mt-px size-3.5 shrink-0" />
						{formatDuration(event.duration_seconds)}
					</span>

					{#if untilLabel}
						<span class="inline-flex items-start gap-1 text-xs font-medium text-muted-foreground">
							<Hourglass class="mt-px size-3.5 shrink-0" />
							{untilLabel}
						</span>
					{/if}

					{#if event.user_subscription}
						<span class="inline-flex items-start gap-1 text-xs font-medium text-muted-foreground">
							<BellRing class="mt-px size-3.5 shrink-0" />
							{m.subscribe_reminder({ count: event.user_subscription.lead_minutes })}
						</span>
						{#if event.user_subscription.queued}
							<span class="inline-flex items-start gap-1 text-xs font-medium text-muted-foreground">
								<CloudOff class="mt-px size-3.5 shrink-0" />
								{m.subscribe_queued_badge()}
							</span>
						{/if}
					{/if}
				</div>
			</div>

			<div class="ml-auto flex shrink-0 items-start">
				<button
					type="button"
					onclick={event.user_subscription ? handleUnsubscribe : handleSubscribe}
					class={[
						'flex size-11 items-center justify-center rounded-lg transition-colors focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none',
						event.user_subscription
							? 'text-primary hover:bg-primary/10'
							: 'text-muted-foreground hover:bg-accent hover:text-foreground'
					]}
					aria-label={event.user_subscription ? m.common_unsubscribe() : m.common_subscribe()}
					aria-pressed={event.user_subscription !== null}
				>
					{#if event.user_subscription}
						<BellRing class="size-5" />
					{:else}
						<Bell class="size-5" />
					{/if}
				</button>

				{#if canManageSchedule(user)}
					<EventStaffActions {event} {isSkipped} bind:optimisticSkipped />
				{/if}
			</div>
		</div>
	</div>
</div>

{#if subscribeModal}
	<SubscribeModal bind:open={subscribeModal} {event} />
{/if}

{#if unsubscribeModal}
	<UnsubscribeModal bind:open={unsubscribeModal} {event} />
{/if}
