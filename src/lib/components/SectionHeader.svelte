<script lang="ts">
	import type { Snippet } from 'svelte';

	interface Props {
		/** Main title (h1) */
		title: string;
		/** Optional description (p) */
		description?: string;
		/** Optional snippet for additional content below description */
		children?: Snippet;
	}

	let { title, description, children }: Props = $props();
</script>

<div class="mb-4 sm:mb-6">
	<h1 class="text-2xl font-bold text-gray-900 sm:text-3xl dark:text-white">
		{title}
	</h1>
	{#if description}
		<p class="mt-1 text-base leading-relaxed text-gray-500 dark:text-gray-400">
			{description}
		</p>
	{/if}
	{#if children}
		{@render children()}
	{/if}
</div>
