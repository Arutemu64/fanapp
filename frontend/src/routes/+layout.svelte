<script lang="ts">
	import type { LayoutProps } from './$types';
	import '../app.css';
	import { setToastService } from '$lib/services/toasts.svelte';
	import { setEventsClient } from '$lib/services/events.svelte';
	import { setPwaService } from '$lib/services/pwa.svelte';
	import { onDestroy } from 'svelte';
	import * as Sentry from '@sentry/sveltekit';

	let { children, data }: LayoutProps = $props();

	const eventsClient = setEventsClient();
	setToastService();
	setPwaService();

	$effect(() => {
		if (data?.user) {
			Sentry.setUser({
				id: String(data.user.id),
				username: data.user.username ?? undefined
			});
		} else {
			Sentry.setUser(null);
		}
	});

	onDestroy(() => {
		eventsClient?.disconnect();
	});
</script>

{@render children()}
