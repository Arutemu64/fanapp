<script lang="ts">
	import type { Snippet } from 'svelte';

	import { cn } from '#lib/utils.js';

	interface Props {
		class?: string;
		ref?: HTMLElement | null;
		children: Snippet;
	}

	let { class: className, ref = $bindable(null), children }: Props = $props();
</script>

<div
	bind:this={ref}
	class={cn('overflow-hidden rounded-2xl border border-border bg-card', className)}
>
	{@render children()}
</div>
