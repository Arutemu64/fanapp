<script lang="ts">
	import type { ScheduleEventWithSubscription } from '$lib/types/schedule';

	import { PlaySolid } from 'flowbite-svelte-icons';

	interface Props {
		/** The act the organizers marked as current, or null when none is marked. */
		event: ScheduleEventWithSubscription | null;
	}

	let { event }: Props = $props();

	// Pad the public number to three digits, e.g. 7 → "007" — same as the programme rows.
	let eventNumber = $derived(event ? event.number.toString().padStart(3, '0') : null);
</script>

<section
	aria-labelledby="live-now-heading"
	class="rounded-2xl border border-primary-200 bg-primary-50 p-4 shadow-sm sm:p-5 dark:border-primary-800/50 dark:bg-primary-900/20"
>
	<div class="flex items-center gap-2.5">
		<span
			class="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-primary-100 text-primary-700 dark:bg-primary-900/40 dark:text-primary-300"
		>
			<PlaySolid class="h-4 w-4" aria-hidden="true" />
		</span>
		<h2
			id="live-now-heading"
			class="text-base font-semibold text-gray-900 sm:text-lg dark:text-white"
		>
			Сейчас на сцене
		</h2>
	</div>

	{#if event}
		<!-- aria-live so a screen reader hears the change when the SSE reload swaps
			 the act on stage while the page is open. -->
		<div class="mt-3" aria-live="polite">
			<p
				class="font-display text-2xl leading-tight font-bold text-gray-900 sm:text-3xl dark:text-white"
			>
				{event.title}
			</p>
			<p class="mt-1.5 text-sm text-gray-600 dark:text-gray-300">
				<span class="font-medium tabular-nums">№&nbsp;{eventNumber}</span>
				{#if event.nomination_title}
					· {event.nomination_title}
				{/if}
			</p>
		</div>
	{:else}
		<p class="mt-3 text-sm leading-relaxed text-gray-600 dark:text-gray-300">
			Пока ничего не отмечено. Как только выступление начнётся, оно появится здесь.
		</p>
	{/if}
</section>
