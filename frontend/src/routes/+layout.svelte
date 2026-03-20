<script lang="ts">
	import type { LayoutProps } from './$types';
	import '../app.css';
	import { setToastService } from '$lib/services/toasts.svelte';
	import { setEventsClient } from '$lib/services/events.svelte';
	import { setPwaService } from '$lib/services/pwa.svelte';
	import { onDestroy } from 'svelte';

	let { children }: LayoutProps = $props();

	const eventsClient = setEventsClient();
	const toastService = setToastService();
	const pwaService = setPwaService();

	onDestroy(() => {
		eventsClient?.disconnect();
	});
</script>

{@render children()}
