<script lang="ts">
	import type { Snippet } from 'svelte';

	interface Props {
		/**
		 * Omit on a section that leads the page: the top bar already shows the page
		 * title, so a heading here would repeat it. The description then leads alone.
		 */
		title?: string;
		description?: string;
		children: Snippet;
	}

	let { title, description, children }: Props = $props();
</script>

<!-- Deliberately not a Card: these settings pages are one task each, so a frame
     around the whole page groups nothing and costs a phone its side padding. The
     row groups inside (MenuGroup) are the only bordered surface. -->
<section class="flex flex-col gap-3">
	{#if title}
		<div class="flex flex-col gap-1">
			<h2 class="text-base leading-snug font-semibold text-foreground sm:text-lg">{title}</h2>
			{#if description}
				<p class="text-sm leading-5 text-muted-foreground">{description}</p>
			{/if}
		</div>
	{:else if description}
		<p class="text-sm leading-5 text-muted-foreground">{description}</p>
	{/if}

	{@render children()}
</section>
