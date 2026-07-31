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

<!-- Green is the "on stage now" colour throughout the app — the programme tints the
	 current row `bg-green-50` and badges it «Сейчас». This card is the same fact on
	 another screen, so it wears the same colour. It stays neutral while nothing is
	 marked: green here always means an act really is running. -->
<section
	aria-labelledby="live-now-heading"
	class={[
		'rounded-2xl border p-4 shadow-sm sm:p-5',
		event
			? 'border-green-200 bg-green-50 dark:border-green-800/50 dark:bg-green-900/20'
			: 'border-gray-200 bg-white dark:border-gray-800 dark:bg-gray-900'
	]}
>
	<div class="flex items-center gap-2.5">
		<span
			class={[
				'flex h-9 w-9 shrink-0 items-center justify-center rounded-xl',
				event
					? 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300'
					: 'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400'
			]}
		>
			<PlaySolid class="h-4 w-4" aria-hidden="true" />
		</span>
		<h2
			id="live-now-heading"
			class="text-base font-semibold text-gray-900 sm:text-lg dark:text-white"
		>
			Сейчас на сцене
		</h2>

		{#if event}
			<!-- Same pulsing live dot as the programme's «Сейчас» badge, so the two screens
				 share one marker. animate-ping is muted under reduced-motion via global CSS.
				 Decorative: the heading above already says the act is on stage. -->
			<span class="relative ml-auto flex h-2.5 w-2.5" aria-hidden="true">
				<span
					class="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-500 opacity-75"
				></span>
				<span class="relative inline-flex h-2.5 w-2.5 rounded-full bg-green-600 dark:bg-green-500"
				></span>
			</span>
		{/if}
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
