<script lang="ts">
	import ToastContainer from '$lib/components/ToastContainer.svelte';
	import SkipLink from '$lib/components/SkipLink.svelte';
	import { ArrowLeftOutline } from 'flowbite-svelte-icons';
	import { resolve } from '$app/paths';
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
		<!-- The auth group has no app shell, so a PWA in standalone mode has no
			browser back button. Always offer an explicit way back to the public app. -->
		<a
			href={resolve('/')}
			class="inline-flex items-center text-sm font-medium text-gray-500 transition hover:text-gray-900 dark:text-gray-400 dark:hover:text-white"
		>
			<ArrowLeftOutline class="me-1.5 h-4 w-4" />
			На главную
		</a>
		{@render children()}
	</div>
</main>
