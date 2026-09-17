<script lang="ts">
	import { getPublicConfigQueryKey } from '$lib/api/generated/@tanstack/svelte-query.gen';
	import { publicConfigQueryOptions } from '$lib/api/queries';
	import { FALLBACK_CONFIG } from '$lib/constants/festival';
	import { getCurrentUserContext } from '$lib/services/currentUser.svelte';
	import { getEventsClient } from '$lib/services/events.svelte';
	import { createQuery, useQueryClient } from '@tanstack/svelte-query';
	import { onMount } from 'svelte';

	import GetReadySection from './components/home/GetReadySection.svelte';
	import HeroCard from './components/home/HeroCard.svelte';

	const currentUser = getCurrentUserContext();
	const queryClient = useQueryClient();

	const configQuery = createQuery(publicConfigQueryOptions);

	// Until config has ever loaded — a first-ever visit made offline — fall back to
	// the shipped defaults so the hero still renders a phase and countdown. Any
	// response, live or restored from the persisted cache, wins over them.
	let config = $derived(configQuery.data ?? FALLBACK_CONFIG);

	const eventsClient = getEventsClient();

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
	<GetReadySection user={currentUser.current} />
</div>
