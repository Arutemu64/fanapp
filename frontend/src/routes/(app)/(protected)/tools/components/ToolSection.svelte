<script lang="ts">
	import type { Component, Snippet } from 'svelte';

	import * as Card from '#lib/components/ui/card/index.js';

	interface Props {
		title?: string;
		icon?: Component<{ class?: string; 'aria-hidden'?: 'true' }>;
		children: Snippet;
	}

	let { title, icon: Icon, children }: Props = $props();
</script>

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
