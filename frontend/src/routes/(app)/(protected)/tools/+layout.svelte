<script lang="ts">
	import OfflineUnavailableState from '#lib/components/OfflineUnavailableState.svelte';
	import { m } from '#lib/paraglide/messages.js';
	import { reachability } from '#lib/services/reachability.js';

	import type { LayoutProps } from './$types';

	let { data, children }: LayoutProps = $props();

	// Entered offline and still offline. Clears on reconnect without a reload, and
	// a connection that drops while a tool is open leaves the form in place (its
	// submit fails into a toast) rather than unmounting what was typed.
	let showOffline = $derived(data.offlineUnavailable && !reachability.current);
</script>

{#if showOffline}
	<!-- The whole toolbox is online-only (see +layout.ts): its actions all mutate
	     server state and none of it is worth reading offline. One state for the
	     section beats a doomed tool grid or a failing sub-page. -->
	<OfflineUnavailableState
		title={m.tools_online_only_title()}
		message={m.tools_online_only_message()}
	/>
{:else}
	{@render children()}
{/if}
