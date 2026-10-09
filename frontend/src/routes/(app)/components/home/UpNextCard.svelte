<script lang="ts">
	import { ArrowRight, BellRing, Hourglass } from '@lucide/svelte';

	import type { ScheduleEventWithSubscription } from '#lib/types/schedule.js';

	import NumberBadge from '#lib/components/NumberBadge.svelte';
	import { Button } from '#lib/components/ui/button/index.js';
	import { formatUntil } from '#lib/utils/formatters.js';

	import { actsUntil, type StageSnapshot } from './stage';

	interface Props {
		snapshot: StageSnapshot;
	}

	let { snapshot }: Props = $props();

	// The hero shows the act on stage; this card is what follows it.
	let isLastAct = $derived(snapshot.featured?.live === true && snapshot.upNext.length === 0);

	function untilLabel(event: ScheduleEventWithSubscription): string | null {
		const distance = actsUntil(event, snapshot.current);
		return distance === null ? null : formatUntil(distance);
	}

	// Same padding as the schedule rows: "7" reads as "007", the public number format.
	function paddedNumber(event: ScheduleEventWithSubscription): string | null {
		return event.number === null ? null : String(event.number).padStart(3, '0');
	}
</script>

{#snippet eventRow(event: ScheduleEventWithSubscription)}
	{@const number = paddedNumber(event)}
	{@const until = untilLabel(event)}
	<div class="flex min-w-0 items-center gap-3">
		{#if number !== null}
			<NumberBadge {number} />
		{:else}
			<!-- Numberless rows (breaks) keep the badge's width so titles share one column. -->
			<div class="w-12 shrink-0" aria-hidden="true"></div>
		{/if}
		<div class="min-w-0 flex-1">
			<p class="text-sm leading-snug font-semibold text-foreground sm:text-base">{event.title}</p>
			{#if event.nomination_title}
				<p class="mt-0.5 truncate text-xs text-muted-foreground">{event.nomination_title}</p>
			{/if}
			{#if until}
				<p class="mt-1 inline-flex items-start gap-1 text-xs font-medium text-muted-foreground">
					<Hourglass class="mt-px size-3.5 shrink-0" aria-hidden="true" />
					{until}
				</p>
			{/if}
		</div>
		{#if event.user_subscription}
			<span class="shrink-0 text-primary">
				<BellRing class="size-4" aria-hidden="true" />
				<span class="sr-only">Есть подписка</span>
			</span>
		{/if}
	</div>
{/snippet}

<section
	aria-labelledby="up-next-heading"
	class="flex flex-col gap-4 rounded-2xl border border-border bg-card p-4 shadow-sm sm:p-5"
>
	<div class="flex items-center justify-between gap-3">
		<h2 id="up-next-heading" class="text-base font-semibold text-foreground sm:text-lg">Дальше</h2>
		<Button href="/schedule" variant="ghost" size="sm" class="-mr-2 shrink-0">
			Вся программа
			<ArrowRight aria-hidden="true" />
		</Button>
	</div>

	{#if isLastAct}
		<p class="text-sm text-muted-foreground">На сцене последнее выступление программы.</p>
	{/if}

	{#if snapshot.upNext.length > 0}
		<ol class="flex flex-col gap-3">
			{#each snapshot.upNext as event (event.id)}
				<li>{@render eventRow(event)}</li>
			{/each}
		</ol>
	{/if}

	{#if snapshot.nextSubscribed}
		<div class="flex flex-col gap-2 border-t border-border pt-4">
			<h3 class="text-sm font-medium text-muted-foreground">Из твоих подписок</h3>
			{@render eventRow(snapshot.nextSubscribed)}
		</div>
	{/if}
</section>
