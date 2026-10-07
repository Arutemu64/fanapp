<script lang="ts">
	import type { LayoutProps } from './$types';

	let { children }: LayoutProps = $props();
</script>

<!-- The /profile hub itself lives outside (protected) so guests can open it; only
     these settings pages behind it need an account. -->
<!-- Same centred column as the /profile hub, so the cards stay where the hub's
     rows were. The way back is the navbar arrow, set in +layout.ts. -->
<div class="mx-auto max-w-2xl">
	<div class="flex flex-col gap-4 sm:gap-5">
		{@render children()}
	</div>
</div>
