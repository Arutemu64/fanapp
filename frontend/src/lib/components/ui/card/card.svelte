<script lang="ts">
	import type { HTMLAttributes } from 'svelte/elements';

	import { cn, type WithElementRef } from '#lib/utils.js';

	let {
		ref = $bindable(null),
		class: className,
		children,
		size = 'default',
		as = 'div',
		...restProps
	}: WithElementRef<HTMLAttributes<HTMLDivElement>> & {
		size?: 'default' | 'sm';
		// Deviates from upstream: opt a card into a semantic container (e.g. `article`
		// for a self-contained content tile). Stays per-instance and defaults to `div`
		// because most cards — form panels, the login/error card — are not articles.
		// Upstream ships Card as a bare div (shadcn issue #10301 open).
		as?: 'div' | 'article' | 'section';
	} = $props();
</script>

<!--
	Deviates from upstream: `rounded-2xl` (18px), not `rounded-xl`, so a card sits with the
	pill buttons and the `MenuGroup` lists beside it; between Material 3's Large (16dp)
	and Large Increased (20dp) container shapes. Content inside the 16–24px padding
	reads as its own surface, not a concentric inner curve, so it keeps its own radius.
-->
<svelte:element
	this={as}
	bind:this={ref}
	data-slot="card"
	data-size={size}
	class={cn(
		'group/card flex flex-col gap-(--card-spacing) overflow-hidden rounded-2xl bg-card py-(--card-spacing) text-sm text-card-foreground shadow-xs ring-1 ring-foreground/10 [--card-spacing:--spacing(6)] has-[>img:first-child]:pt-0 data-[size=sm]:[--card-spacing:--spacing(4)] *:[img:first-child]:rounded-t-2xl *:[img:last-child]:rounded-b-2xl',
		className
	)}
	{...restProps}
>
	{@render children?.()}
</svelte:element>
