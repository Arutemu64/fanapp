<script lang="ts">
	import Play from '@lucide/svelte/icons/play';

	import type { ScheduleEventWithSubscription } from '#lib/types/schedule.js';

	import { Button } from '#lib/components/ui/button/index.js';
	import { m } from '#lib/paraglide/messages.js';
	import { formatEventNumber } from '#lib/utils/formatters.js';

	interface Props {
		event: ScheduleEventWithSubscription;
		hidden: boolean;
		onjump: () => void;
	}

	let { event, hidden, onjump }: Props = $props();

	let eventNumber = $derived(formatEventNumber(event.number));

	let barHeight = $state(0);

	$effect(() => {
		if (hidden) return;

		const root = document.documentElement;
		root.style.setProperty('--bottom-accessory-clearance', `calc(${barHeight}px + 0.5rem)`);

		return () => root.style.removeProperty('--bottom-accessory-clearance');
	});
</script>

<div
	class={[
		'pointer-events-none sticky bottom-[calc(var(--bottom-nav-clearance)+0.5rem)] z-30 transition-[opacity,translate] duration-200 ease-out md:bottom-[calc(1rem+env(safe-area-inset-bottom))]',
		hidden && 'translate-y-2 opacity-0'
	]}
	inert={hidden}
	bind:clientHeight={barHeight}
>
	<Button
		variant="floating"
		onclick={onjump}
		class="pointer-events-auto mx-auto flex h-14 w-full max-w-md justify-start gap-3 rounded-full py-2 pr-5 pl-2 text-left active:not-aria-[haspopup]:rounded-full"
	>
		<span
			class="flex size-10 shrink-0 items-center justify-center rounded-full bg-success text-success-foreground"
			aria-hidden="true"
		>
			<Play class="size-4 fill-current" />
		</span>
		<span class="flex min-w-0 flex-col">
			<span class="text-xs font-medium text-success">{m.home_on_stage()}</span>
			<span class="truncate text-sm font-semibold text-foreground">
				{#if eventNumber !== null}
					<span class="tabular-nums">{eventNumber}</span> ·
				{/if}
				{event.title}
			</span>
		</span>
	</Button>
</div>
