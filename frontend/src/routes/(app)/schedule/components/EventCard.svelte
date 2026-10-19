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
		// 'interlude' for a block-less row (a break, the opening, the closing):
		// drops the number column, since these stand alone rather than in the
		// numbered list. Everything else — the bell, staff actions, the live
		// highlight — stays, so an interlude can still be subscribed to or marked
		// current.
		variant?: 'default' | 'interlude';
	}

	let { event, currentEvent, user, variant = 'default' }: Props = $props();
	const toastService = getToastService();

	let subscribeModal = $state(false);
	let unsubscribeModal = $state(false);

	let eventNumber = $derived(formatEventNumber(event.number));

	// Optimistic skip flag: the row reflects the toggle instantly instead of waiting
	// for the schedule refetch to round-trip (a flaky connection can delay it for
	// seconds). null = trust the server-loaded prop; otherwise show our pending guess.
	let optimisticSkipped = $state<boolean | null>(null);
	let isSkipped = $derived(optimisticSkipped ?? event.is_skipped);

	// Once the reloaded schedule confirms our guess, drop the override so external
	// changes (another staffer skipping the same event) flow through again.
	$effect(() => {
		if (optimisticSkipped !== null && event.is_skipped === optimisticSkipped) {
			optimisticSkipped = null;
		}
	});

	// How far ahead this event is compared to the one on stage now.
	// Returns null if either value is missing or the event has already passed.
	function aheadOf(value: number | null, currentValue: number | null): number | null {
		if (value === null || currentValue === null) return null;
		const diff = value - currentValue;
		return diff >= 0 ? diff : null;
	}

	let actsAhead = $derived(currentEvent ? aheadOf(event.position, currentEvent.position) : null);

	// Position distance only ("how many acts away"): the schedule carries no predicted
	// clock time (ADR-0014), and the distance decrements as the current-event
	// pointer advances (one set-current SSE per act reloads the schedule).
	let untilLabel = $derived(actsAhead === null || actsAhead <= 0 ? null : formatUntil(actsAhead));

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
	<!-- Interludes stand alone, not in the numbered list, so they drop the number
		column entirely rather than reserving its width. -->
	{#if variant === 'default'}
		<!-- Keep the public number visible so the list stays easy to scan on mobile. -->
		{#if eventNumber !== null}
			<NumberBadge number={eventNumber} highlighted={event.is_current} />
		{:else}
			<!-- Numberless rows (breaks) keep the badge's width as empty space: dropping
				it would pull their title out of the column every other row shares, and
				the ragged left edge reads as a broken list while scrolling. -->
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

				<!-- Colored state badges get their own row so they read as a distinct tier above the quiet meta, and wrap predictably on narrow screens. Rendered only when a state is present, so the common no-badge row stays single-line. -->
				{#if event.is_current || isSkipped}
					<div class="mt-1.5 flex flex-wrap items-center gap-1.5">
						{#if event.is_current}
							<Badge
								variant="outline"
								class="inline-flex items-center gap-1.5 border-success/30 bg-success/10 px-2 py-0.5 text-xs font-medium text-success"
							>
								<!-- Live dot reads as "on stage now" at a glance. The ping runs three
									     times and stops (WCAG 2.2.2, see --animate-ping-brief); reduced motion
									     mutes it via global CSS. -->
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

				<!-- Quiet meta row: duration, countdown, subscription — muted text, no colored chip.
				     Every chip aligns its icon to the first line (items-start + mt-px on the icon),
				     not the centre: any chip can wrap to two lines on a narrow phone, and a centred
				     icon would then float in the gap beside the first line. -->
				<div class="mt-1.5 flex flex-wrap items-center gap-x-2 gap-y-1">
					<span class="inline-flex items-start gap-1 text-xs font-medium text-muted-foreground">
						<Clock class="mt-px size-3.5 shrink-0" />
						{formatDuration(event.duration)}
					</span>

					{#if untilLabel}
						<span class="inline-flex items-start gap-1 text-xs font-medium text-muted-foreground">
							<Hourglass class="mt-px size-3.5 shrink-0" />
							{untilLabel}
						</span>
					{/if}

					{#if event.user_subscription}
						<!-- Subscription threshold is personal meta, not event state: muted text like duration. The right-side bell carries the colored "subscribed" marker. -->
						<span class="inline-flex items-start gap-1 text-xs font-medium text-muted-foreground">
							<BellRing class="mt-px size-3.5 shrink-0" />
							{m.subscribe_reminder({ count: event.user_subscription.counter })}
						</span>
						<!-- Subscribing works offline (ADR-0038): until it is sent, say so beside the
						     threshold rather than pretend the reminder is already set up. -->
						{#if event.user_subscription.queued}
							<span class="inline-flex items-start gap-1 text-xs font-medium text-muted-foreground">
								<CloudOff class="mt-px size-3.5 shrink-0" />
								{m.subscribe_queued_badge()}
							</span>
						{/if}
					{/if}
				</div>
			</div>

			<!-- The bell stays top-right for every user; staff get the ⋯ management menu beside it. -->
			<div class="ml-auto flex shrink-0 items-start">
				<!-- Inline bell: subscribe/unsubscribe in one tap. -->
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

<!-- Mounted only while open. This card renders once per schedule row, so
	always-mounted dialogs cost component instances per row for something almost
	never opened. -->
{#if subscribeModal}
	<SubscribeModal bind:open={subscribeModal} {event} />
{/if}

{#if unsubscribeModal}
	<UnsubscribeModal bind:open={unsubscribeModal} {event} />
{/if}
