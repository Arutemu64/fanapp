<script lang="ts">
	import type { LayoutProps } from './$types';
	import '../app.css';
	import { setToastService } from '$lib/stores/toasts.svelte';
	import { setEventsClient } from '$lib/events.svelte';
	import { setPwaService } from '$lib/stores/pwa.svelte';
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
