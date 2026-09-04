<script lang="ts">
	import { getThemeService } from '$lib/services/theme.svelte';
	import CircleCheckIcon from '@lucide/svelte/icons/circle-check';
	import InfoIcon from '@lucide/svelte/icons/info';
	import Loader2Icon from '@lucide/svelte/icons/loader-2';
	import OctagonXIcon from '@lucide/svelte/icons/octagon-x';
	import TriangleAlertIcon from '@lucide/svelte/icons/triangle-alert';
	import { Toaster as Sonner, type ToasterProps as SonnerProps } from 'svelte-sonner';

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
</script>

<Sonner
	theme={theme.mode}
	class="toaster group"
	position="bottom-center"
	{offset}
	{mobileOffset}
	style="--normal-bg: var(--color-popover); --normal-text: var(--color-popover-foreground); --normal-border: var(--color-border);"
	{...restProps}
>
	{#snippet loadingIcon()}
		<Loader2Icon class="size-4 animate-spin" />
	{/snippet}
	{#snippet successIcon()}
		<CircleCheckIcon class="size-4" />
	{/snippet}
	{#snippet errorIcon()}
		<OctagonXIcon class="size-4" />
	{/snippet}
	{#snippet infoIcon()}
		<InfoIcon class="size-4" />
	{/snippet}
	{#snippet warningIcon()}
		<TriangleAlertIcon class="size-4" />
	{/snippet}
</Sonner>
