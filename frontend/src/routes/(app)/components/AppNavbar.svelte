<script lang="ts">
	import type { CurrentUserDto } from '$lib/api/generated';

	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import { Button } from '$lib/components/ui/button';
	import { ArrowLeft } from '@lucide/svelte';

	import NotificationBell from './NotificationBell.svelte';

	// Pages expose their heading through `load` -> `page.data.title`.
	let pageTitle = $derived(page.data.title);
	// Nested pages name their parent the same way; tab roots set none.
	let back = $derived(page.data.back);

	interface Props {
		user: CurrentUserDto | null;
	}

	let { user }: Props = $props();
</script>

<!-- Full width so the bell pins to the right edge. Account actions (login, logout)
	live on the Profile tab, not here, so the bar is identical on phones and desktop.
	Positioning (overlay, z-index, hide-on-scroll) and the backdrop blur are owned by the
	(app) layout's chrome wrapper; this bar supplies only the translucent tint. -->
<header
	class="flex items-center justify-between gap-2 border-b border-border/50 bg-background/80 px-4 py-2.5 pt-[calc(0.625rem+env(safe-area-inset-top))] transition-colors duration-300 select-none [-webkit-touch-callout:none] sm:px-6 reduced-transparency:bg-background"
>
	<!-- Page title comes from each page's `load` via `page.data.title`; render it
		as the single page <h1>. The row is held at the bell's h-11 so the bar keeps
		one height whether or not the bell renders (guests have none). -->
	<div class="flex h-11 min-w-0 flex-1 items-center gap-1">
		<!-- Leading back arrow, the top-app-bar convention: an installed iOS PWA has no
			system back button, and unlike an in-content link this one returns with the
			bar on any upward scroll. -ml-2 lines the arrow glyph up with the page edge. -->
		{#if back}
			<Button
				href={resolve(back.href)}
				variant="ghost"
				size="icon"
				class="-ml-2"
				aria-label={back.label}
			>
				<ArrowLeft class="size-5" />
			</Button>
		{/if}
		{#if pageTitle}
			<h1 class="truncate text-lg font-semibold text-foreground sm:text-xl">
				{pageTitle}
			</h1>
		{/if}
	</div>

	{#if user}
		<!-- The bell lives in the (app) layout, above the route's error boundary, so
		     a render error in it would otherwise take the whole shell down to the
		     root error page. Render nothing in its place instead. No onerror: every
		     boundary already runs SvelteKit's transformError, so handleError has
		     reported it. -->
		<svelte:boundary>
			<NotificationBell />
			{#snippet failed()}{/snippet}
		</svelte:boundary>
	{/if}
</header>
