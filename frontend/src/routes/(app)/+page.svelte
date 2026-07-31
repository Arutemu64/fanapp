<script lang="ts">
	import { invalidate } from '$app/navigation';
	import StaleDataNotice from '$lib/components/StaleDataNotice.svelte';
	import { getEventsClient } from '$lib/services/events.svelte';
	import { getOfflineService, shouldShowStaleNotice } from '$lib/services/offline.svelte';
	import { resolveFestivalPhase } from '$lib/utils/festival';
	import { ThumbsUpSolid } from 'flowbite-svelte-icons';
	import { onMount } from 'svelte';

	import type { PageProps } from './$types';

	import FestivalOverCard from './components/home/FestivalOverCard.svelte';
	import GetReadyCard from './components/home/GetReadyCard.svelte';
	import GetReadySection from './components/home/GetReadySection.svelte';
	import HeroCard from './components/home/HeroCard.svelte';
	import LiveNowCard from './components/home/LiveNowCard.svelte';
	import NextSubscriptionCard from './components/home/NextSubscriptionCard.svelte';
	import UpNextList from './components/home/UpNextList.svelte';

	// How many upcoming acts the "Дальше" list shows. Three fits one thumb-length of
	// screen under the current act; the full programme is one tap away.
	const UP_NEXT_LIMIT = 3;

	let { data }: PageProps = $props();
	let user = $derived(data.user);
	let schedule = $derived(data.schedule);

	const offline = getOfflineService();
	const eventsClient = getEventsClient();

	// Re-evaluated whenever the schedule reloads, which is exactly when the phase can
	// change: the `schedule_updated` stream fires as organizers mark acts, and that
	// same reload is what carries a fresh clock into the fallback below.
	let phase = $derived(resolveFestivalPhase(schedule, Date.now()));

	let currentEvent = $derived(schedule.find((event) => event.is_current) ?? null);

	// Everything still to come, in programme order. Before the first act is marked
	// there is no anchor, so "still to come" is the whole programme minus what has
	// already run.
	let upcoming = $derived.by(() => {
		const currentIndex = currentEvent ? schedule.indexOf(currentEvent) : -1;

		return schedule
			.slice(currentIndex + 1)
			.filter((event) => !event.is_skipped && event.actual_start_time === null);
	});

	let upNext = $derived(upcoming.slice(0, UP_NEXT_LIMIT));

	let nextSubscription = $derived.by(() => {
		const subscribed = upcoming.find((event) => event.user_subscription !== null);
		if (!subscribed) return null;

		// Already visible in "Дальше" — no need to say it twice.
		return upNext.includes(subscribed) ? null : subscribed;
	});

	let showStaleNotice = $derived(
		shouldShowStaleNotice({
			offlineMiss: data.offlineMiss,
			stale: data.stale,
			isOnline: offline.isOnline
		})
	);

	onMount(() => {
		// Same contract as the programme page: refetch on every schedule update and on
		// every (re)connect, so an update missed while the stream was down can't leave
		// a stale act on stage — this page is the PWA start_url and is often the first
		// thing reopened after the connection comes back.
		const reloadSchedule = () => {
			void invalidate('app:schedule');
		};

		eventsClient.on('schedule_updated', reloadSchedule);
		eventsClient.on('connection_established', reloadSchedule);

		return () => {
			eventsClient.off('schedule_updated', reloadSchedule);
			eventsClient.off('connection_established', reloadSchedule);
		};
	});
</script>

<svelte:head>
	<title>ФАН ФАН</title>
</svelte:head>

<div class="space-y-5 sm:space-y-6">
	{#if showStaleNotice}
		<StaleDataNotice
			message="Нет связи. Показана сохранённая программа — обновится при подключении."
			cachedAt={data.cachedAt}
		/>
	{/if}

	{#if phase === 'before'}
		<HeroCard />
	{:else if phase === 'live'}
		<LiveNowCard event={currentEvent} />

		{#if upNext.length > 0}
			<UpNextList events={upNext} {currentEvent} />
		{/if}

		{#if nextSubscription}
			<NextSubscriptionCard event={nextSubscription} {currentEvent} />
		{/if}

		{#if data.canVote}
			<!-- Same card as the setup steps: this is a "do it now" prompt too, and one
				 shared affordance keeps the home screen reading as a single list. -->
			<GetReadyCard
				featured
				title="Голосование открыто"
				description="Отдай голос за выступления, которые понравились больше всего."
				icon={ThumbsUpSolid}
				actionLabel="Голосовать"
				href="/voting"
			/>
		{/if}
	{:else}
		<FestivalOverCard />
	{/if}

	{#if phase !== 'after'}
		<GetReadySection {user} {phase} />
	{/if}
</div>
