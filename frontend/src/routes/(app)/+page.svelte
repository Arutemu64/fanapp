<script lang="ts">
	import { invalidate } from '$app/navigation';
	import { getEventsClient } from '$lib/services/events.svelte';
	import { onMount } from 'svelte';

	import type { PageProps } from './$types';

	import GetReadySection from './components/home/GetReadySection.svelte';
	import HeroCard from './components/home/HeroCard.svelte';

	let { data }: PageProps = $props();
	let user = $derived(data.user);
	let config = $derived(data.config);

	const eventsClient = getEventsClient();

	onMount(() => {
		// Refetch config on a change and on every (re)connect, so the hero flips
		// phase (e.g. organizers ending the festival) without a reload, and a
		// 'config_updated' missed while the stream was down still self-heals.
		// Firing on first connect just re-runs the freshly loaded config once —
		// harmless and idempotent.
		const reloadConfig = () => {
			void invalidate('app:config');
		};

		eventsClient.on('config_updated', reloadConfig);
		eventsClient.on('connection_established', reloadConfig);

		return () => {
			eventsClient.off('config_updated', reloadConfig);
			eventsClient.off('connection_established', reloadConfig);
		};
	});
</script>

<svelte:head>
	<title>ФАН ФАН</title>
</svelte:head>

<div class="space-y-5 sm:space-y-6">
	<HeroCard festivalStart={config.festival_start} festivalEnd={config.festival_end} />
	<GetReadySection {user} />
</div>
