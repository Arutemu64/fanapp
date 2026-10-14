<script lang="ts">
	import type { HTMLAttributes } from 'svelte/elements';

	import { Dialog as DialogPrimitive } from 'bits-ui';

	import { Button } from '#lib/components/ui/button/index.js';
	// Deviates from upstream: built-in accessible names go through Paraglide
	// instead of fixed English text, so they follow the interface language.
	import { m } from '#lib/paraglide/messages.js';
	import { cn, type WithElementRef } from '#lib/utils.js';

	let {
		ref = $bindable(null),
		class: className,
		children,
		showCloseButton = false,
		...restProps
	}: WithElementRef<HTMLAttributes<HTMLDivElement>> & {
		showCloseButton?: boolean;
	} = $props();
</script>

<!-- Deviates from upstream: the close button's label is Russian. -->
<div
	bind:this={ref}
	data-slot="dialog-footer"
	class={cn('flex flex-col-reverse gap-2 gap-2 sm:flex-row sm:justify-end', className)}
	{...restProps}
>
	{@render children?.()}
	{#if showCloseButton}
		<DialogPrimitive.Close>
			{#snippet child({ props })}
				<Button variant="outline" {...props}>{m.common_close()}</Button>
			{/snippet}
		</DialogPrimitive.Close>
	{/if}
</div>
