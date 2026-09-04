<script lang="ts">
	import type { HTMLAttributes } from 'svelte/elements';

	import { cn, type WithElementRef } from '$lib/utils.js';

	let {
		ref = $bindable(null),
		class: className,
		children,
		size = 'default',
		as = 'div',
		...restProps
	}: WithElementRef<HTMLAttributes<HTMLDivElement>> & {
		size?: 'default' | 'sm';
		// Opt a card into a semantic container (e.g. `article` for a self-contained
		// content tile). Stays per-instance and defaults to `div` because most cards
		// — form panels, the login/error card — are not articles. Local addition
		// upstream lacks (shadcn ships Card as a bare div, issue #10301 open); a
		// `shadcn-svelte update` will drop this prop — keep it on merge.
		as?: 'div' | 'article' | 'section';
	} = $props();
</script>

<svelte:element
	this={as}
	bind:this={ref}
	data-slot="card"
	data-size={size}
	class={cn(
		'group/card flex flex-col gap-(--card-spacing) overflow-hidden rounded-xl bg-card py-(--card-spacing) text-sm text-card-foreground shadow-xs ring-1 ring-foreground/10 [--card-spacing:--spacing(6)] has-[>img:first-child]:pt-0 data-[size=sm]:[--card-spacing:--spacing(4)] *:[img:first-child]:rounded-t-xl *:[img:last-child]:rounded-b-xl',
		className
	)}
	{...restProps}
>
	{@render children?.()}
</svelte:element>
