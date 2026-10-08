<script lang="ts">
	import CircleCheckIcon from '@lucide/svelte/icons/circle-check';
	import InfoIcon from '@lucide/svelte/icons/info';
	import Loader2Icon from '@lucide/svelte/icons/loader-2';
	import OctagonXIcon from '@lucide/svelte/icons/octagon-x';
	import TriangleAlertIcon from '@lucide/svelte/icons/triangle-alert';
	import { Toaster as Sonner, type ToasterProps as SonnerProps } from 'svelte-sonner';

	import { getThemeService } from '#lib/services/theme.svelte.js';

	let { ...restProps }: SonnerProps = $props();
	const theme = getThemeService();

	// Two toast lanes share this one Toaster via per-toast `position` (set in
	// toasts.svelte.ts): action feedback at bottom-center (the default below),
	// push notifications at top-right. A single object offset covers both — a
	// top-anchored toast reads top/right, a bottom-anchored one reads bottom — so
	// each lane clears its own chrome. The insets are CSS vars (app.css) that
	// trace the top bar and the mobile-only bottom nav.
	const offset = {
		top: 'var(--toast-top-offset)',
		bottom: 'var(--toast-bottom-offset)',
		left: '1.5rem',
		right: '1.5rem'
	};
	const mobileOffset = {
		top: 'var(--toast-top-offset)',
		bottom: 'var(--toast-bottom-offset)',
		left: '1rem',
		right: '1rem'
	};

	// Sonner's own button styles carry three-attribute selectors, so these
	// overrides need `!` to win. The close button moves from Sonner's macOS-style
	// top-left corner badge into the card's top-right corner (where Carbon and
	// most web toasts put it), and the toast reserves a column for it. The ::after
	// widens the tap target to 44px — WCAG 2.5.8's 24px floor, Apple's 44pt touch
	// guidance — without growing the visible icon.
	const toastClasses = {
		toast: 'has-[[data-close-button]]:pe-12!',
		closeButton: [
			'top-2! right-2! left-auto! size-8! transform-none! rounded-md! border-0! bg-transparent!',
			'text-muted-foreground! hover:bg-accent! hover:text-accent-foreground! [&_svg]:size-4',
			"after:absolute after:-inset-1.5 after:content-['']"
		].join(' '),
		actionButton: [
			'h-8! rounded-md! px-3! text-sm! font-medium!',
			'bg-primary! text-primary-foreground! hover:bg-primary/80!'
		].join(' ')
	};

	// Sonner's default only swipes toward the toast's own edge, so a bottom toast
	// could be flicked only downward, into the bottom nav. Any direction dismisses.
	const swipeDirections: SonnerProps['swipeDirections'] = ['top', 'right', 'bottom', 'left'];
</script>

<Sonner
	theme={theme.mode}
	class="toaster group"
	position="bottom-center"
	{offset}
	{mobileOffset}
	toastOptions={{ classes: toastClasses }}
	{swipeDirections}
	containerAriaLabel="Всплывающие сообщения"
	closeButtonAriaLabel="Закрыть"
	style="--normal-bg: var(--color-popover); --normal-text: var(--color-popover-foreground); --normal-border: var(--color-border);"
	{...restProps}
>
	{#snippet loadingIcon()}
		<Loader2Icon class="size-4 animate-spin" />
	{/snippet}
	{#snippet successIcon()}
		<CircleCheckIcon class="size-4 text-success" />
	{/snippet}
	{#snippet errorIcon()}
		<OctagonXIcon class="size-4 text-destructive" />
	{/snippet}
	{#snippet infoIcon()}
		<InfoIcon class="size-4 text-info" />
	{/snippet}
	{#snippet warningIcon()}
		<TriangleAlertIcon class="size-4 text-warning" />
	{/snippet}
</Sonner>
