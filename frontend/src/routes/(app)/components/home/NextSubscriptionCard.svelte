<script lang="ts">
	import type { ScheduleEventWithSubscription } from '$lib/types/schedule';

	import { formatMoscowTime, formatUntil } from '$lib/utils/formatters';
	import { BellActiveSolid } from 'flowbite-svelte-icons';

	interface Props {
		/** The viewer's nearest upcoming subscribed act. */
		event: ScheduleEventWithSubscription;
		/** The act on stage now, used to measure the queue distance. */
		currentEvent: ScheduleEventWithSubscription | null;
	}

	let { event, currentEvent }: Props = $props();

	// Same rule as the "Дальше" rows: queue distance survives a drifting programme,
	// the expected time is the fallback while nothing is on stage yet.
	let until = $derived.by(() => {
		const queue = event.queue;
		const currentQueue = currentEvent?.queue ?? null;

		if (queue !== null && currentQueue !== null && queue >= currentQueue) {
			return formatUntil(queue - currentQueue, event.expected_start_time ?? null);
		}

		if (event.expected_start_time) {
			return `≈ ${formatMoscowTime(event.expected_start_time)}`;
		}

		return null;
	});
</script>

<section
	aria-labelledby="next-subscription-heading"
	class="rounded-2xl border border-secondary-200 bg-secondary-50 p-4 shadow-sm dark:border-secondary-800/50 dark:bg-secondary-900/20"
>
	<div class="flex items-center gap-2.5">
		<span
			class="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-secondary-100 text-secondary-700 dark:bg-secondary-900/40 dark:text-secondary-300"
		>
			<BellActiveSolid class="h-4 w-4" aria-hidden="true" />
		</span>
		<h2
			id="next-subscription-heading"
			class="text-base font-semibold text-gray-900 sm:text-lg dark:text-white"
		>
			Твоё ближайшее
		</h2>
	</div>

	<p class="mt-3 text-base font-semibold text-gray-900 sm:text-lg dark:text-white">
		{event.title}
	</p>
	<p class="mt-1 text-sm text-gray-600 dark:text-gray-300">
		<span class="font-medium tabular-nums">№&nbsp;{event.number.toString().padStart(3, '0')}</span>
		{#if until}
			· {until}
		{/if}
	</p>
</section>
