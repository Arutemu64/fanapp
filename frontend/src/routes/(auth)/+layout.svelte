<script lang="ts">
	import SkipLink from '#lib/components/SkipLink.svelte';
	import { m } from '#lib/paraglide/messages.js';

	import type { LayoutProps } from './$types';

	let { children }: LayoutProps = $props();
</script>

<SkipLink />

<main
	id="main-content"
	tabindex="-1"
	class="relative flex min-h-svh items-center justify-center bg-background px-4 py-6 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-600 sm:py-10"
>
	<div class="flex w-full max-w-sm flex-col gap-3">
		<img
			src="/icons/wordmark.svg"
			width="561"
			height="198"
			alt={m.app_name()}
			class="mx-auto mb-5 h-12 w-auto"
		/>

		{@render children()}
	</div>
</main>
