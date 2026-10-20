<script lang="ts">
	import ArrowRight from '@lucide/svelte/icons/arrow-right';
	import BellRing from '@lucide/svelte/icons/bell-ring';

	import type { ScheduleEventWithSubscription } from '#lib/types/schedule.js';

	import NumberBadge from '#lib/components/NumberBadge.svelte';
	import StaleDataNotice from '#lib/components/StaleDataNotice.svelte';
	import { Button } from '#lib/components/ui/button/index.js';
	import { m } from '#lib/paraglide/messages.js';
	import { formatEventNumber, formatUntil } from '#lib/utils/formatters.js';

	import { actsUntil, type StageSnapshot } from './stage';

	interface Props {
		snapshot: StageSnapshot;
		/** Epoch millis of the shown programme, set only while it may be out of date. */
		cachedAt?: number;
	}

	let { snapshot, cachedAt }: Props = $props();

	// The art above shows the act on stage; this is what follows it.
	let isLastAct = $derived(snapshot.featured?.live === true && snapshot.upNext.length === 0);

	function untilLabel(event: ScheduleEventWithSubscription): string | null {
		const distance = actsUntil(event, snapshot.current);
		return distance === null ? null : formatUntil(distance);
	}

	// Distance and nomination share one line, so a row costs a title and a caption.
	// Distance first: when the line truncates on a phone, the nomination gives way.
	function metaLine(event: ScheduleEventWithSubscription): string {
		const parts = [untilLabel(event), event.nomination_title].filter(Boolean);
		return parts.join(' · ');
	}
</script>

<!-- Under the art, on the card's own surface: the next acts, then the viewer's
     nearest subscribed act beyond them. Kept to what fits beside the voting card on
     a phone's first screen; the schedule holds the rest. -->
<div class="flex flex-col gap-3 p-4 sm:px-6">
	<div class="-my-1 flex items-center justify-between gap-3">
		{#if snapshot.upNext.length > 0 || isLastAct}
			<h3 class="text-sm font-medium text-muted-foreground">{m.home_next()}</h3>
		{/if}
		<Button href="/schedule" variant="ghost" size="sm" class="-mr-2 ml-auto shrink-0">
			{m.home_full_schedule()}
			<ArrowRight aria-hidden="true" />
		</Button>
	</div>

	{#if isLastAct}
		<p class="text-sm text-muted-foreground">{m.home_last_event()}</p>
	{/if}

	{#if snapshot.upNext.length > 0}
		<ol class="flex flex-col gap-3">
			{#each snapshot.upNext as event (event.id)}
				{const number = $derived(formatEventNumber(event.number))}
				{const meta = $derived(metaLine(event))}
				<li class="flex min-w-0 items-center gap-3">
					{#if number !== null}
						<NumberBadge {number} />
					{:else}
						<!-- Numberless rows (breaks) keep the badge's width so titles share one column. -->
						<div class="w-12 shrink-0" aria-hidden="true"></div>
					{/if}
					<div class="min-w-0 flex-1">
						<p class="text-base leading-snug font-semibold text-foreground">{event.title}</p>
						{#if meta}
							<p class="mt-0.5 truncate text-xs text-muted-foreground">{meta}</p>
						{/if}
					</div>
					{#if event.user_subscription}
						<span class="shrink-0 text-primary">
							<BellRing class="size-4" aria-hidden="true" />
							<span class="sr-only">{m.home_has_subscription()}</span>
						</span>
					{/if}
				</li>
			{/each}
		</ol>
	{/if}

	{#if snapshot.nextSubscribed}
		{const subscribed = $derived(snapshot.nextSubscribed)}
		{const subscribedNumber = $derived(formatEventNumber(subscribed.number))}
		{const subscribedUntil = $derived(untilLabel(subscribed))}
		<!-- One tinted line instead of a third row with its own heading: it is a
		     reminder, and the bell already marks it as the viewer's. -->
		<div class="flex items-start gap-2 rounded-xl bg-primary/10 px-3 py-2 text-sm">
			<BellRing class="mt-0.5 size-4 shrink-0 text-primary" aria-hidden="true" />
			<p class="min-w-0">
				<span class="text-muted-foreground">{m.home_from_subscriptions()}:</span>
				<span class="font-semibold text-foreground">
					{#if subscribedNumber !== null}№{subscribedNumber}{/if}
					{subscribed.title}
				</span>
				{#if subscribedUntil}
					<span class="block text-xs text-muted-foreground">{subscribedUntil}</span>
				{/if}
			</p>
		</div>
	{/if}

	{#if cachedAt !== undefined}
		<StaleDataNotice message={m.schedule_cached_notice()} {cachedAt} />
	{/if}
</div>
