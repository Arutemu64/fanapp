<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { ComponentProps } from 'svelte';

	import { Button } from '$lib/components/ui/button/index.js';
	import { cn, type WithoutChildrenOrChild } from '$lib/utils.js';
	import XIcon from '@lucide/svelte/icons/x';
	import { Dialog as DialogPrimitive } from 'bits-ui';

	import DialogPortal from './dialog-portal.svelte';
	import * as Dialog from './index.js';

	let {
		ref = $bindable(null),
		class: className,
		portalProps,
		children,
		showCloseButton = true,
		...restProps
	}: WithoutChildrenOrChild<DialogPrimitive.ContentProps> & {
		portalProps?: WithoutChildrenOrChild<ComponentProps<typeof DialogPortal>>;
		children: Snippet;
		showCloseButton?: boolean;
	} = $props();
</script>

<DialogPortal {...portalProps}>
	<Dialog.Overlay />
	<DialogPrimitive.Content
		bind:ref
		data-slot="dialog-content"
		class={cn(
			'fixed z-50 grid w-full gap-6 bg-popover p-6 text-sm text-popover-foreground ring-1 ring-foreground/10 outline-none data-open:animate-in data-closed:animate-out',
			// Phones: a bottom sheet — thumb-reachable, scrolling inside itself when taller
			// than the screen, clear of the home indicator. The easing is iOS's sheet curve
			// (the one Vaul uses).
			'max-sm:inset-x-0 max-sm:bottom-0 max-sm:max-h-[calc(100dvh-env(safe-area-inset-top)-2rem)] max-sm:overflow-y-auto max-sm:overscroll-contain max-sm:rounded-t-2xl max-sm:pb-[calc(1.5rem+env(safe-area-inset-bottom))] max-sm:duration-250 max-sm:ease-[cubic-bezier(0.32,0.72,0,1)] max-sm:data-open:slide-in-from-bottom max-sm:data-closed:slide-out-to-bottom',
			// sm and up: the centred dialog, unchanged.
			'sm:top-1/2 sm:left-1/2 sm:max-w-md sm:-translate-x-1/2 sm:-translate-y-1/2 sm:rounded-2xl sm:duration-100 sm:data-open:fade-in-0 sm:data-open:zoom-in-95 sm:data-closed:fade-out-0 sm:data-closed:zoom-out-95',
			className
		)}
		{...restProps}
	>
		{@render children?.()}
		{#if showCloseButton}
			<DialogPrimitive.Close data-slot="dialog-close">
				{#snippet child({ props })}
					<Button variant="ghost" class="absolute top-4 right-4" size="icon-sm" {...props}>
						<XIcon />
						<span class="sr-only">Закрыть</span>
					</Button>
				{/snippet}
			</DialogPrimitive.Close>
		{/if}
	</DialogPrimitive.Content>
</DialogPortal>
