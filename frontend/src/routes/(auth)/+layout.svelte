<script lang="ts">
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	// Bundled (not static/) so Vite content-hashes it like the other brand assets.
	import logo from '$lib/assets/logo.svg';
	import SkipLink from '$lib/components/SkipLink.svelte';

	import type { LayoutProps } from './$types';

	let { children }: LayoutProps = $props();
</script>

<SkipLink />

<main
	id="main-content"
	tabindex="-1"
	class="relative flex min-h-dvh items-center justify-center bg-background px-4 py-6 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-600 sm:py-10"
>
	<div class="flex w-full max-w-sm flex-col gap-3">
		<!-- Same mark as the sidebar; see AppSidebar.svelte for why `dark:invert` is enough
			on its own to cover both themes. -->
		<img src={logo} alt="ФАН ФАН" class="mx-auto h-12 w-auto dark:invert" />

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
				class="inline-flex min-h-11 items-center justify-center rounded-lg px-3 text-sm font-medium text-muted-foreground hover:text-foreground focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-600"
				onclick={() => goto(resolve('/'))}
			>
				Продолжить без входа
			</button>
		</div>
	</div>
</main>
