<script lang="ts">
	import type { Snippet } from 'svelte';

	interface Props {
		description?: string;
		children?: Snippet;
	}

	let { description, children }: Props = $props();
</script>

{#if description || children}
	<div class="mb-4 sm:mb-6">
		{#if description}
			<p class="text-body leading-relaxed text-muted-foreground">
				{description}
			</p>
		{/if}
		{#if children}
			{@render children()}
		{/if}
	</div>
{/if}
