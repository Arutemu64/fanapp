<script lang="ts">
	import { invalidate } from '$app/navigation';
	import { getEventsClient } from '$lib/services/events.svelte';
	import { onMount } from 'svelte';

	import type { LayoutProps } from './$types';

	let { children }: LayoutProps = $props();

	const eventsClient = getEventsClient();

	onMount(() => {
		// Refetch voting status on a config change and on every (re)connect, so the
		// banner flips open/closed the moment organizers change the range — without a
		// reload — and a 'config_updated' missed while the stream was down self-heals.
		// The server still enforces the range at vote time, so a missed refresh is
		// cosmetic, never a votable dead end. Firing on first connect just re-runs the
		// freshly loaded status once — harmless and idempotent.
		const reloadStatus = () => {
			void invalidate('app:config');
		};

		eventsClient.on('config_updated', reloadStatus);
		eventsClient.on('connection_established', reloadStatus);

		return () => {
			eventsClient.off('config_updated', reloadStatus);
			eventsClient.off('connection_established', reloadStatus);
		};
	});
</script>

{@render children()}
