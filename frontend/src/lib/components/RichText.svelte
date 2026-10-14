<script lang="ts">
	import type { Snippet } from 'svelte';

	// Renders a translated sentence that wraps some words in markup — bold, an
	// accent, a link. The message marks them with simple tags
	// ("…<strong>after</strong>…") and the caller supplies one snippet per tag
	// name, so a translator keeps control of where the markup falls in the
	// sentence while the HTML itself stays in the component. Only the tag names
	// in `tags` are markup; anything else, including text that came from data,
	// renders as plain text.
	let { text, tags }: { text: string; tags: Record<string, Snippet<[string]>> } = $props();

	interface Part {
		// The snippet for a tagged span; null for plain text.
		snippet: Snippet<[string]> | null;
		content: string;
	}

	let parts = $derived.by(() => {
		const result: Part[] = [];
		const pattern = /<([a-z]+)>(.*?)<\/\1>/gs;
		let cursor = 0;
		for (const match of text.matchAll(pattern)) {
			const [whole, tag = '', content = ''] = match;
			const snippet = tags[tag];
			if (!snippet) continue;
			if (match.index > cursor) {
				result.push({ snippet: null, content: text.slice(cursor, match.index) });
			}
			result.push({ snippet, content });
			cursor = match.index + whole.length;
		}
		if (cursor < text.length) {
			result.push({ snippet: null, content: text.slice(cursor) });
		}
		return result;
	});
</script>

{#each parts as part, index (index)}
	{#if part.snippet}
		{@render part.snippet(part.content)}
	{:else}
		{part.content}
	{/if}
{/each}
