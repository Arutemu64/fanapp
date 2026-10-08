<script lang="ts">
	// Bundled (not static/) so Vite content-hashes it like the other brand assets.
	import logo from '#lib/assets/logo.svg';
	import SkipLink from '#lib/components/SkipLink.svelte';

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
			on its own to cover both themes. The extra margin keeps the brand apart from
			the card: at the column's 12px gap it reads as part of the form (NN/g,
			https://www.nngroup.com/articles/gestalt-proximity/). -->
		<img src={logo} alt="ФАН ФАН" class="mx-auto mb-5 h-12 w-auto dark:invert" />

		{@render children()}
	</div>
</main>
