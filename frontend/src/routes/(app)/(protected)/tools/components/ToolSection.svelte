<script lang="ts">
	import type { Component, Snippet } from 'svelte';

	import * as Card from '#lib/components/ui/card/index.js';

	interface Props {
		/** The section heading; a card that leads with its own content leaves it out. */
		title?: string;
		/** A leading icon for the heading. */
		icon?: Component<{ class?: string; 'aria-hidden'?: 'true' }>;
		children: Snippet;
	}

	let { title, icon: Icon, children }: Props = $props();
</script>

<!-- One card per block of a tool page, filling the page's capped column. -->
<Card.Root class="w-full max-w-none gap-4 p-4 sm:p-6">
	{#if title && Icon}
		<div class="flex items-center gap-2">
			<Icon class="size-5 text-primary" aria-hidden="true" />
			<h2 class="text-section text-foreground">{title}</h2>
		</div>
	{:else if title}
		<h2 class="text-section text-foreground">{title}</h2>
	{/if}
	{@render children()}
</Card.Root>
