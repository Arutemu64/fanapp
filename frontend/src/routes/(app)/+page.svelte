<script lang="ts">
	import {
		getPublicConfigOptions,
		getPublicConfigQueryKey
	} from '$lib/api/generated/@tanstack/svelte-query.gen';
	import { FALLBACK_CONFIG } from '$lib/constants/festival';
	import { getEventsClient } from '$lib/services/events.svelte';
	import { createQuery, useQueryClient } from '@tanstack/svelte-query';
	import { onMount } from 'svelte';

	import type { PageProps } from './$types';

	import GetReadySection from './components/home/GetReadySection.svelte';
	import HeroCard from './components/home/HeroCard.svelte';

	let { data }: PageProps = $props();
	let user = $derived(data.user);

	const eventsClient = getEventsClient();
	const queryClient = useQueryClient();

	// The hero's phase (before/during/after) and countdown must render for guests
	// and offline. A complete miss — a first-ever visit made offline — falls back to
	// the shipped defaults; any response, live or persisted, wins over them.
	const configQuery = createQuery(() => getPublicConfigOptions());
	let config = $derived(configQuery.data ?? FALLBACK_CONFIG);

	onMount(() => {
		// Refetch config on a change and on every (re)connect, so the hero flips
		// phase (e.g. organizers ending the festival) without a reload, and a
		// 'config_updated' missed while the stream was down still self-heals.
		// Firing on first connect just re-runs the freshly loaded config once —
		// harmless and idempotent.
		const reloadConfig = () => {
			void queryClient.invalidateQueries({ queryKey: getPublicConfigQueryKey() });
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

<div class="flex flex-col gap-5 sm:gap-6">
	<HeroCard festivalStart={config.festival_start} festivalEnd={config.festival_end} />
	<GetReadySection {user} />
</div>
