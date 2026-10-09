<script lang="ts">
	import StaleDataNotice from '#lib/components/StaleDataNotice.svelte';
	import { reachability } from '#lib/services/reachability.js';

	import type { LayoutProps } from './$types';

	let { children }: LayoutProps = $props();

	// Every profile sub-page renders from the layout-cached user, so the only "out of
	// date" state is being offline. The notice also carries why every write control
	// below is disabled: offlineWriteGate's `title` hint never shows on a touch
	// screen (https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Global_attributes/title).
	let showStaleNotice = $derived(!reachability.current);
	const staleNoticeMessage =
		'Нет связи. Показан сохранённый профиль — изменения доступны только онлайн.';
</script>

<!-- The /profile hub itself lives outside (protected) so guests can open it; only
     these settings pages behind it need an account. -->
<!-- Same centred column as the /profile hub, so the cards stay where the hub's
     rows were. The way back is the navbar arrow, set in +layout.ts. -->
<div class="mx-auto max-w-2xl">
	<div class="flex flex-col gap-4 sm:gap-5">
		{#if showStaleNotice}
			<StaleDataNotice message={staleNoticeMessage} />
		{/if}

		{@render children()}
	</div>
</div>
