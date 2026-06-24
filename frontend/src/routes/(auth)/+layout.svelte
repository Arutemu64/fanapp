<script lang="ts">
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
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

		<!--
			The app is usable by guests, and login is reached both voluntarily (navbar)
			and via protected-route redirects, so always offer a way back into it.
			Navigate to the app root explicitly instead of history.back(): going back
			would re-enter a protected redirect straight to /login, and a direct
			deep-link to /login has no history to return to.
		-->
		<div class="text-center">
			<button
				type="button"
				class="inline-flex min-h-11 items-center justify-center rounded-lg px-3 text-sm font-medium text-gray-600 hover:text-gray-900 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-600 dark:text-gray-400 dark:hover:text-gray-200"
				onclick={() => goto(resolve('/'))}
			>
				Продолжить без входа
			</button>
		</div>
	</div>
</main>
