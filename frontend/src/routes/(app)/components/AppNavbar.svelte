<script lang="ts">
	import type { CurrentUserDto } from '$lib/api/generated';

	import { page } from '$app/state';

	import NotificationBell from './NotificationBell.svelte';

	// Pages expose their heading through `load` -> `page.data.title`.
	let pageTitle = $derived(page.data.title);

	interface Props {
		user: CurrentUserDto | null;
	}

	let { user }: Props = $props();
</script>

<!-- Full width so the bell pins to the right edge. Account actions (login, logout)
	live on the Profile tab, not here, so the bar is identical on phones and desktop.
	Positioning (overlay, z-index, hide-on-scroll) is owned by the (app) layout, which
	slides this bar with `top` to keep its backdrop blur intact. -->
<header
	class="flex items-center justify-between gap-2 border-b border-border/50 bg-background/80 px-4 py-2.5 pt-[calc(0.625rem+env(safe-area-inset-top))] backdrop-blur-md transition-colors duration-300 sm:px-6"
>
	<!-- Page title comes from each page's `load` via `page.data.title`; render it
		as the single page <h1>. The row is held at the bell's h-11 so the bar keeps
		one height whether or not the bell renders (guests have none). -->
	<div class="flex h-11 min-w-0 flex-1 items-center">
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
