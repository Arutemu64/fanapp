<script lang="ts">
	// Deviates from upstream: the focus ring is solid `ring-ring`, not `ring-ring/50`.
	// At half alpha it measures ~2.4:1 against the surface, under the 3:1 WCAG 1.4.11
	// asks of a focus indicator; see `--ring` in app.css.
	import type { HTMLTextareaAttributes } from 'svelte/elements';

	import { cn, type WithElementRef, type WithoutChildren } from '#lib/utils.js';

	let {
		ref = $bindable(null),
		value = $bindable(),
		class: className,
		'data-slot': dataSlot = 'textarea',
		...restProps
	}: WithoutChildren<WithElementRef<HTMLTextareaAttributes>> = $props();
</script>

<textarea
	bind:this={ref}
	data-slot={dataSlot}
	class={cn(
		'flex field-sizing-content min-h-16 w-full rounded-md border border-input bg-transparent px-2.5 py-2 text-base shadow-xs transition-[color,box-shadow] outline-none placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50 aria-invalid:border-destructive aria-invalid:ring-3 aria-invalid:ring-destructive/20 md:text-sm dark:bg-input/30 dark:aria-invalid:border-destructive/50 dark:aria-invalid:ring-destructive/40',
		className
	)}
	bind:value
	{...restProps}></textarea>
