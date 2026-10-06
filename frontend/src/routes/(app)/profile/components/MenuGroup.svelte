<script lang="ts">
	import type { Snippet } from 'svelte';

	interface Props {
		children: Snippet;
	}

	let { children }: Props = $props();
</script>

<!-- One bordered block per group of rows: the grouped-list shape of a phone's
     settings screen, so the hub stays short enough that logout sits about a screen
     down instead of under a stack of cards. -->
<div class="overflow-hidden rounded-2xl border border-border bg-card">
	{@render children()}
</div>
