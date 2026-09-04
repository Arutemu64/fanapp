<script lang="ts">
	import type { Snippet } from 'svelte';

	interface Props {
		/** Optional description (p) shown under the navbar page title */
		description?: string;
		/** Optional snippet for additional content below the description */
		children?: Snippet;
	}

	let { description, children }: Props = $props();
</script>

<!-- The page title now lives in the navbar; this only renders the optional
	intro text/extra content for screens that need extra context. -->
{#if description || children}
	<div class="mb-4 sm:mb-6">
		{#if description}
			<p class="text-base leading-relaxed text-muted-foreground">
				{description}
			</p>
		{/if}
		{#if children}
			{@render children()}
		{/if}
	</div>
{/if}
