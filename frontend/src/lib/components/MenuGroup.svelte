<script lang="ts">
	import type { Snippet } from 'svelte';

	import { cn } from '#lib/utils.js';

	interface Props {
		class?: string;
		children: Snippet;
	}

	let { class: className, children }: Props = $props();
</script>

<!-- One bordered block per group of rows: the grouped-list shape of a phone's
     settings screen. It sits straight on the page, never inside a Card, so related
     rows read as one set rather than as boxes-inside-a-box — and the /profile hub
     stays short enough that logout sits about a screen down instead of under a
     stack of cards. -->
<div class={cn('overflow-hidden rounded-2xl border border-border bg-card', className)}>
	{@render children()}
</div>
