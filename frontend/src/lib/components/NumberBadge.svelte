<script lang="ts">
	interface Props {
		number: number | string;
		highlighted?: boolean;
	}

	let { number, highlighted = false }: Props = $props();
</script>

<div
	class={[
		'flex w-12 shrink-0 flex-col items-center rounded-lg border p-1.5 text-center',
		highlighted ? 'border-success/40 bg-card' : 'border-border bg-muted'
	]}
>
	<span class="text-xs font-bold tracking-widest text-primary uppercase"> № </span>
	<span class="font-display text-base leading-none font-bold text-foreground tabular-nums"
		>{number}</span
	>
</div>
