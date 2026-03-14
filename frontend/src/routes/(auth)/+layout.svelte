<script lang="ts">
	import { browser } from '$app/environment';
	import { goto } from '$app/navigation';
	import ToastContainer from '$lib/components/ToastContainer.svelte';
	import { Button } from 'flowbite-svelte';
	import { ArrowLeftOutline } from 'flowbite-svelte-icons';
	import type { LayoutProps } from './$types';

	let { children }: LayoutProps = $props();

	async function handleBackClick(event: MouseEvent) {
		if (!browser) return;

		event.preventDefault();

		// Use browser history when available and fall back to the home page for direct visits.
		if (window.history.length > 1) {
			window.history.back();
			return;
		}

		await goto('/');
	}
</script>

<main
	class="relative flex min-h-dvh items-center justify-center bg-gray-50 px-4 py-6 sm:py-10 dark:bg-gray-950"
>
	<ToastContainer />

	<div class="w-full max-w-md space-y-3">
		{@render children()}
	</div>
</main>
