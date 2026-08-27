<script lang="ts">
	import OfflineUnavailableState from '$lib/components/OfflineUnavailableState.svelte';

	import type { LayoutProps } from './$types';

	let { data, children }: LayoutProps = $props();
</script>

{#if data.offlineUnavailable}
	<!-- The whole toolbox is online-only (see +layout.ts): its actions all mutate
	     server state and none of it is worth reading offline. One state for the
	     section beats a doomed tool grid or a failing sub-page. -->
	<OfflineUnavailableState
		title="Инструменты доступны только онлайн"
		message="Подключись к интернету, чтобы пользоваться инструментами организатора."
	/>
{:else}
	{@render children()}
{/if}
