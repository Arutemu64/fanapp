<script lang="ts">
	import ToastContainer from '$lib/components/ToastContainer.svelte';
	import type { LayoutProps } from './$types';

	let { children }: LayoutProps = $props();
</script>

<main
	class="relative flex min-h-dvh items-center justify-center bg-gray-50 px-4 py-6 sm:py-10 dark:bg-gray-950"
>
	<ToastContainer />

	<div class="w-full max-w-md space-y-3">
		{@render children()}
	</div>
</main>
