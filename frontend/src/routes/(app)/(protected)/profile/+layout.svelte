<script lang="ts">
	import type { LayoutProps } from './$types';

	let { children }: LayoutProps = $props();
</script>

<div class="mx-auto max-w-2xl">
	<div class="flex flex-col gap-4 sm:gap-5">
		{@render children()}
	</div>
</div>
