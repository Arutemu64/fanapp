<script lang="ts">
	import type { Snippet } from 'svelte';

	interface Props {
		title?: string;
		description?: string;
		children: Snippet;
	}

	let { title, description, children }: Props = $props();
</script>

<section class="flex flex-col gap-3">
	{#if title}
		<div class="flex flex-col gap-1">
			<h2 class="text-section text-foreground">{title}</h2>
			{#if description}
				<p class="text-sm leading-5 text-muted-foreground">{description}</p>
			{/if}
		</div>
	{:else if description}
		<p class="text-sm leading-5 text-muted-foreground">{description}</p>
	{/if}

	{@render children()}
</section>
