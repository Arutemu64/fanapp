<script lang="ts" generics="T">
	import type { Snippet } from 'svelte';

	import type { QueryView, ReadyView } from '#lib/utils/queryView.js';

	import ErrorState from '#lib/components/ErrorState.svelte';
	import OfflineUnavailableState from '#lib/components/OfflineUnavailableState.svelte';

	// Renders the three non-ready branches of a `queryView`, so a page writes only
	// its skeleton and its content. A cached screen passes `offline` to promise
	// something different from the online-only default: it will work offline once
	// it has loaded (docs/frontend.md §2).
	let {
		view,
		loading,
		offline,
		ready
	}: {
		view: QueryView<T>;
		loading: Snippet;
		offline?: Snippet;
		ready: Snippet<[ReadyView<T>]>;
	} = $props();
</script>

{#if view.kind === 'offline'}
	{#if offline}
		{@render offline()}
	{:else}
		<OfflineUnavailableState />
	{/if}
{:else if view.kind === 'loading'}
	{@render loading()}
{:else if view.kind === 'error'}
	<ErrorState variant="inline" error={{ message: view.message }} onRetry={view.retry} />
{:else}
	{@render ready(view)}
{/if}
