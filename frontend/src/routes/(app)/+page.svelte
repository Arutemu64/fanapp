<script lang="ts">
	import { getApiClient } from '$lib/api/context';
	import { getPublicConfigOptions } from '$lib/api/queries';
	import { FALLBACK_CONFIG } from '$lib/constants/festival';
	import { invalidateConfig } from '$lib/query/invalidate';
	import { persisted } from '$lib/query/persist';
	import { getEventsClient } from '$lib/services/events.svelte';
	import { createQuery, useQueryClient } from '@tanstack/svelte-query';
	import { onMount } from 'svelte';

	import type { PageProps } from './$types';

	import GetReadySection from './components/home/GetReadySection.svelte';
	import HeroCard from './components/home/HeroCard.svelte';

	let { data }: PageProps = $props();
	let user = $derived(data.user);

	const client = getApiClient();
	const queryClient = useQueryClient();
	const eventsClient = getEventsClient();

	// The hero's phase (before/during/after) and countdown must render for guests
	// and offline, so the config is persisted under the universal scope — one entry
	// serves everyone and survives logout.
	const configQuery = createQuery(() => persisted(getPublicConfigOptions({ client }), 'universal'));

	// Defaults cover the one case the cache can't: a first-ever visit made offline,
	// before /config has ever been fetched. Any loaded copy wins over them.
	let config = $derived(configQuery.data ?? FALLBACK_CONFIG);

	onMount(() => {
		// Refetch config on a change and on every (re)connect, so the hero flips
		// phase (e.g. organizers ending the festival) without a reload, and a
		// 'config_updated' missed while the stream was down still self-heals.
		// Firing on first connect just re-runs the freshly loaded config once —
		// harmless and idempotent.
		const reloadConfig = () => {
			void invalidateConfig(queryClient);
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
