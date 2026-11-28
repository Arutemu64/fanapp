<script lang="ts">
	import LocateFixed from '@lucide/svelte/icons/locate-fixed';

	import type { ScheduleEventWithSubscription } from '#lib/types/schedule.js';

	import { Button } from '#lib/components/ui/button/index.js';
	import { m } from '#lib/paraglide/messages.js';
	import { formatEventNumber } from '#lib/utils/formatters.js';

	interface Props {
		event: ScheduleEventWithSubscription;
		onjump: () => void;
	}

	let { event, onjump }: Props = $props();

	let eventNumber = $derived(formatEventNumber(event.number));
	let title = $derived(eventNumber === null ? event.title : `${eventNumber} · ${event.title}`);

	let barHeight = $state(0);
	let titleViewportWidth = $state(0);
	let titleWidth = $state(0);
	let titleOverflow = $derived(Math.max(0, titleWidth - titleViewportWidth));

	$effect(() => {
		const root = document.documentElement;
		root.style.setProperty('--bottom-accessory-clearance', `calc(${barHeight}px + 0.5rem)`);

		return () => root.style.removeProperty('--bottom-accessory-clearance');
	});
</script>

<div
	class="@container pointer-events-none fixed inset-x-0 bottom-[calc(var(--bottom-nav-clearance)+0.5rem)] z-30 bottom-nav-insets md:sticky md:inset-x-auto md:bottom-6 md:mt-auto md:px-0 lg:bottom-8"
	bind:clientHeight={barHeight}
>
	<Button
		variant="floating"
		onclick={onjump}
		aria-label={m.schedule_jump_to_current({ title })}
		class="pointer-events-auto mx-auto flex h-auto min-h-12 w-full max-w-md justify-start gap-2.5 rounded-full px-3.5 py-1.5 text-left whitespace-normal active:not-aria-[haspopup]:rounded-full md:min-h-14 md:max-w-lg md:px-5"
	>
		<span class="relative size-2 shrink-0 rounded-full bg-success" aria-hidden="true">
			{#key event.id}
				<span data-live-pulse class="absolute inset-0 rounded-full bg-success opacity-0"></span>
			{/key}
		</span>

		<span class="flex min-w-0 flex-1 flex-col gap-0.5">
			<span
				data-title-viewport
				data-title-overflow={titleOverflow > 1 ? true : undefined}
				class="block text-sm leading-tight font-semibold text-foreground"
				style:--title-overflow={`${titleOverflow}px`}
				bind:clientWidth={titleViewportWidth}
			>
				{#key title}
					<span data-title-track class="block" bind:clientWidth={titleWidth}>{title}</span>
				{/key}
			</span>
			<span class="text-xs leading-tight font-medium text-muted-foreground">
				{m.home_on_stage()}
			</span>
		</span>

		<LocateFixed class="size-5 shrink-0 text-primary" aria-hidden="true" />
	</Button>
</div>

<style>
	[data-title-track] {
		overflow-wrap: anywhere;
	}

	@media (prefers-reduced-motion: no-preference) {
		[data-live-pulse] {
			animation: live-pulse 600ms ease-out;
		}

		@container (width >= 13em) {
			[data-title-viewport] {
				overflow: hidden;
			}

			[data-title-track] {
				width: max-content;
				white-space: nowrap;
			}

			[data-title-overflow] {
				mask-image: linear-gradient(to right, black calc(100% - 0.5rem), transparent);
			}

			[data-title-overflow] [data-title-track] {
				animation: scroll-title 4.8s ease-in-out;
			}
		}
	}

	@keyframes live-pulse {
		from {
			scale: 1;
			opacity: 0.55;
		}

		to {
			scale: 2.5;
			opacity: 0;
		}
	}

	@keyframes scroll-title {
		0%,
		18% {
			translate: 0;
		}

		78%,
		100% {
			translate: calc(-1 * (var(--title-overflow) + 0.5rem));
		}
	}
</style>
