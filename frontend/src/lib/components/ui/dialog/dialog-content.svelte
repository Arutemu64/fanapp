<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { ComponentProps } from 'svelte';

	import { Button } from '$lib/components/ui/button/index.js';
	import { cn, type WithoutChildrenOrChild } from '$lib/utils.js';
	import { keyboardInset } from '$lib/utils/keyboardInset';
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

	// On a phone the sheet is fixed to the layout viewport's bottom edge, which an
	// on-screen keyboard covers without moving it (see keyboardInset). While the
	// sheet is open, track the covered strip and lift the sheet's content above
	// it with padding — the sheet itself stays anchored, as a native one does.
	let coveredByKeyboard = $state(0);
	let visibleHeight = $state(0);

	$effect(() => {
		const viewport = window.visualViewport;
		if (!ref || !viewport) return;

		const update = () => {
			coveredByKeyboard = keyboardInset(window.innerHeight, viewport);
			visibleHeight = viewport.height;
		};
		update();
		// iOS fires `scroll`, not `resize`, when it pans to a focused field.
		viewport.addEventListener('resize', update);
		viewport.addEventListener('scroll', update);
		return () => {
			viewport.removeEventListener('resize', update);
			viewport.removeEventListener('scroll', update);
			coveredByKeyboard = 0;
		};
	});

	let keyboardStyle = $derived(
		coveredByKeyboard > 0
			? `--keyboard-inset: ${coveredByKeyboard}px; --visible-height: ${visibleHeight}px`
			: undefined
	);
</script>

<DialogPortal {...portalProps}>
	<Dialog.Overlay />
	<DialogPrimitive.Content
		bind:ref
		data-slot="dialog-content"
		class={cn(
			'fixed z-50 grid w-full gap-6 bg-popover p-6 text-sm text-popover-foreground ring-1 ring-foreground/10 outline-none data-open:animate-in data-closed:animate-out',
			// Phones: a bottom sheet — thumb-reachable, clear of the home indicator, and
			// scrolling its body (below) when taller than the screen. The easing is iOS's
			// sheet curve (the one Vaul uses).
			'max-sm:inset-x-0 max-sm:bottom-0 max-sm:flex max-sm:max-h-[calc(100dvh-env(safe-area-inset-top)-2rem)] max-sm:flex-col max-sm:rounded-t-2xl max-sm:pb-[calc(1.5rem+env(safe-area-inset-bottom))] max-sm:duration-250 max-sm:ease-[cubic-bezier(0.32,0.72,0,1)] max-sm:data-open:slide-in-from-bottom max-sm:data-closed:slide-out-to-bottom',
			// Keyboard open on a phone: pad the content clear of it (the inset replaces
			// the home-indicator inset, which the keyboard covers anyway), and cap the
			// height so the sheet's top stays inside what is still visible.
			coveredByKeyboard > 0 &&
				'max-sm:max-h-[calc(var(--visible-height)+var(--keyboard-inset)-1rem)] max-sm:pb-[calc(1.5rem+var(--keyboard-inset))]',
			// sm and up: a centred dialog.
			'sm:top-1/2 sm:left-1/2 sm:max-w-md sm:-translate-x-1/2 sm:-translate-y-1/2 sm:rounded-2xl sm:duration-100 sm:data-open:fade-in-0 sm:data-open:zoom-in-95 sm:data-closed:fade-out-0 sm:data-closed:zoom-out-95',
			className
		)}
		style={keyboardStyle}
		{...restProps}
	>
		<!-- On phones the body scrolls, not the sheet, so the absolutely positioned close
			button stays in view on a tall form. `contents` elsewhere keeps the children as
			direct grid items. The 1-unit inset stops the scroller clipping focus rings. -->
		<div
			class="contents max-sm:-m-1 max-sm:grid max-sm:min-h-0 max-sm:gap-6 max-sm:overflow-y-auto max-sm:overscroll-contain max-sm:p-1"
		>
			{@render children?.()}
		</div>
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
