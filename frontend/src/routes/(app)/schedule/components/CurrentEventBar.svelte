<script lang="ts">
	import { Play } from '@lucide/svelte';

	import type { ScheduleEventWithSubscription } from '#lib/types/schedule.js';

	import { Button } from '#lib/components/ui/button/index.js';
	import { formatEventNumber } from '#lib/utils/formatters.js';

	interface Props {
		event: ScheduleEventWithSubscription;
		// True while the event's own row is on screen: the bar would only repeat it.
		hidden: boolean;
		onjump: () => void;
	}

	let { event, hidden, onjump }: Props = $props();

	let eventNumber = $derived(formatEventNumber(event.number));
</script>

<!-- The iOS 26 tab-bar accessory shape (Music's MiniPlayer): a slim bar floating
	above the tab bar for something ongoing (https://developer.apple.com/design/human-interface-guidelines/tab-bars).
	Sticky at the bottom of the page's own column rather than fixed to the window, so
	on desktop it centres over the content, not over content + sidebar. z-30 keeps it
	above the sticky block headers (z-20) and under the top chrome. Hidden by class,
	not unmounted, so it fades instead of popping; `inert` takes it out of the tab
	order and the accessibility tree meanwhile. -->
<div
	class={[
		'pointer-events-none sticky bottom-[calc(var(--bottom-nav-clearance)+0.5rem)] z-30 transition-[opacity,translate] duration-200 ease-out md:bottom-[calc(1rem+env(safe-area-inset-bottom))]',
		hidden && 'translate-y-2 opacity-0'
	]}
	inert={hidden}
>
	<Button
		variant="floating"
		onclick={onjump}
		class="pointer-events-auto mx-auto flex h-14 w-full max-w-md justify-start gap-3 rounded-full py-2 pr-5 pl-2 text-left"
	>
		<span
			class="flex size-10 shrink-0 items-center justify-center rounded-full bg-success text-success-foreground"
			aria-hidden="true"
		>
			<Play class="size-4 fill-current" />
		</span>
		<span class="flex min-w-0 flex-col">
			<span class="text-xs font-medium text-success">Сейчас на сцене</span>
			<span class="truncate text-sm font-semibold text-foreground">
				{#if eventNumber !== null}
					<span class="tabular-nums">{eventNumber}</span> ·
				{/if}
				{event.title}
			</span>
		</span>
	</Button>
</div>
