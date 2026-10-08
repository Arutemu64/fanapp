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

	// Sonner's default only swipes toward the toast's own edge, so a bottom toast
	// could be flicked only downward, into the bottom nav. Any direction dismisses.
	const swipeDirections: SonnerProps['swipeDirections'] = ['top', 'right', 'bottom', 'left'];

	// Only Sonner's own options here, no overrides of its CSS (they break silently
	// on upgrade). Inline styles and the variables below beat its stylesheet. The
	// close-button variables mirror Sonner's macOS-style top-left badge to the
	// top-right corner, where Carbon and most web toasts put it.
	const toastOptions = {
		actionButtonStyle: 'background: var(--color-primary); color: var(--color-primary-foreground);'
	};
	const toasterStyle = [
		'--normal-bg: var(--color-popover);',
		'--normal-text: var(--color-popover-foreground);',
		'--normal-border: var(--color-border);',
		'--toast-close-button-start: unset;',
		'--toast-close-button-end: 0;',
		'--toast-close-button-transform: translate(35%, -35%);'
	].join(' ');
</script>

<Sonner
	theme={theme.mode}
	class="toaster group"
	position="bottom-center"
	{offset}
	{mobileOffset}
	containerAriaLabel="Всплывающие сообщения"
	closeButtonAriaLabel="Закрыть"
	{toastOptions}
	{swipeDirections}
	style={toasterStyle}
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
