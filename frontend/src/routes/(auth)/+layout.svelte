<script lang="ts">
	import ToastContainer from '$lib/components/ToastContainer.svelte';
	import SkipLink from '$lib/components/SkipLink.svelte';
	import type { LayoutProps } from './$types';

	let { children }: LayoutProps = $props();
</script>

<SkipLink />
<ToastContainer />

<main
	id="main-content"
	tabindex="-1"
	class="relative flex min-h-dvh items-center justify-center bg-gray-50 px-4 py-6 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-600 sm:py-10 dark:bg-gray-950"
>
	<div class="w-full max-w-md space-y-3">
		{@render children()}
	</div>
</main>
