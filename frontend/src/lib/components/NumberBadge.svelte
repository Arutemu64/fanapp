<script lang="ts">
	interface Props {
		number: number | string;
		/** Lifts the badge onto a tinted row (a live event, a voted participant). */
		highlighted?: boolean;
	}

	let { number, highlighted = false }: Props = $props();
</script>

<!-- Signature element: the public number is how people find an act in the programme
     and in the voting gallery, and it scrolls past hundreds of times, so it carries
     the brand. Shared by the schedule and voting lists so both read as one app. -->
<div
	class={[
		'flex w-12 shrink-0 flex-col items-center rounded-lg border px-1.5 py-1.5 text-center',
		highlighted ? 'border-success/40 bg-card' : 'border-border bg-muted'
	]}
>
	<span class="text-xs font-bold tracking-widest text-primary uppercase"> № </span>
	<span class="font-display text-base leading-none font-bold text-foreground tabular-nums"
		>{number}</span
	>
</div>
