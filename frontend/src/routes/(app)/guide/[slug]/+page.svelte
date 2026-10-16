<script lang="ts">
	import { m } from '#lib/paraglide/messages.js';

	import type { PageProps } from './$types';

	let { data }: PageProps = $props();

	const Content = $derived(data.article.Content);
</script>

<svelte:head>
	<title>{m.document_title({ title: data.article.title })}</title>
</svelte:head>

<!-- The markdown renders bare elements, so the spacing, list and link style come from here.
     Links stay underlined: colour alone must not mark them (WCAG 1.4.1). -->
<article
	class="mx-auto w-full max-w-2xl rounded-2xl border bg-card p-5 leading-relaxed sm:p-6 [&_a]:font-medium [&_a]:text-primary [&_a]:underline [&_a]:underline-offset-4 [&_h2]:mt-6 [&_h2]:text-lg [&_h2]:leading-snug [&_h2]:font-semibold [&_li]:mt-1.5 [&_p]:mt-3 [&_p:first-child]:mt-0 [&_ul]:mt-3 [&_ul]:list-disc [&_ul]:ps-5"
>
	<Content />
</article>
