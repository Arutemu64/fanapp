<script lang="ts">
	import type { ScheduleEventWithSubscription } from '$lib/types/schedule';

	import { resolve } from '$app/paths';
	import { formatMoscowTime, formatUntil } from '$lib/utils/formatters';
	import { ArrowRightOutline, BellActiveSolid } from 'flowbite-svelte-icons';

	interface Props {
		/** The acts coming up, already ordered and sliced by the page. */
		events: ScheduleEventWithSubscription[];
		/** The act on stage now, used to measure the queue distance. Null before the first one. */
		currentEvent: ScheduleEventWithSubscription | null;
	}

	let { events, currentEvent }: Props = $props();

	/**
	 * When an act is coming up. Queue distance is drift-proof and preferred, but it
	 * needs an act on stage to measure from — before the programme starts there is
	 * none, so fall back to the expected wall-clock time.
	 */
	function untilLabel(event: ScheduleEventWithSubscription): string | null {
		const queue = event.queue;
		const currentQueue = currentEvent?.queue ?? null;

		if (queue !== null && currentQueue !== null && queue >= currentQueue) {
			return formatUntil(queue - currentQueue, event.expected_start_time ?? null);
		}

		if (event.expected_start_time) {
			return `≈ ${formatMoscowTime(event.expected_start_time)}`;
		}

		return null;
	}
</script>

<section aria-labelledby="up-next-heading" class="space-y-3">
	<h2 id="up-next-heading" class="text-lg font-semibold text-gray-900 dark:text-white">Дальше</h2>

	<ul class="space-y-2">
		{#each events as event (event.id)}
			{@const until = untilLabel(event)}
			<li
				class="flex items-start gap-3 rounded-2xl border border-gray-200 bg-white p-3.5 shadow-sm dark:border-gray-800 dark:bg-gray-900"
			>
				<span
					class="mt-0.5 shrink-0 rounded-lg bg-gray-100 px-2 py-1 text-xs leading-none font-medium text-gray-600 tabular-nums dark:bg-gray-800 dark:text-gray-300"
				>
					{event.number.toString().padStart(3, '0')}
				</span>

				<div class="min-w-0 flex-1">
					<p class="text-sm font-semibold text-gray-900 sm:text-base dark:text-white">
						{event.title}
					</p>
					{#if until}
						<p class="mt-0.5 text-xs text-gray-500 dark:text-gray-400">{until}</p>
					{/if}
				</div>

				{#if event.user_subscription}
					<span class="mt-0.5 shrink-0 text-primary-600 dark:text-primary-400">
						<!-- Noun form, not «ты подписан»: a short-form adjective would have to
							 agree in gender, which the copy cannot know. -->
						<span class="sr-only">Подписка оформлена</span>
						<BellActiveSolid class="h-4 w-4" aria-hidden="true" />
					</span>
				{/if}
			</li>
		{/each}
	</ul>

	<a
		href={resolve('/schedule')}
		class="group inline-flex items-center gap-1.5 text-sm font-semibold text-primary-600 underline-offset-4 hover:underline dark:text-primary-400"
	>
		Вся программа
		<ArrowRightOutline
			class="h-4 w-4 transition-transform group-hover:translate-x-0.5"
			aria-hidden="true"
		/>
	</a>
</section>
