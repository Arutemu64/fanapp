<script lang="ts">
	import { invalidate } from '$app/navigation';
	import StaleDataNotice from '$lib/components/StaleDataNotice.svelte';
	import { documentVisibility } from '$lib/services/documentVisibility';
	import { getEventsClient } from '$lib/services/events.svelte';
	import { getOfflineService, shouldShowStaleNotice } from '$lib/services/offline.svelte';
	import { hasVotingEnded, isVotingWindowOpen } from '$lib/utils/votingStatus';
	import { onMount } from 'svelte';

	import type { PageProps } from './$types';

	import { getFestivalPhase, nextBoundary } from './components/home/festivalPhase';
	import GetReadySection from './components/home/GetReadySection.svelte';
	import HeroCard from './components/home/HeroCard.svelte';
	import NowOnStageCard from './components/home/NowOnStageCard.svelte';
	import { getStageSnapshot } from './components/home/stage';
	import VotingCard from './components/home/VotingCard.svelte';

	let { data }: PageProps = $props();
	let user = $derived(data.user);
	let config = $derived(data.config);
	let votingStatus = $derived(data.votingStatus);

	const eventsClient = getEventsClient();
	const offline = getOfflineService();

	let festivalStartMs = $derived(new Date(config.festival_start).getTime());
	let festivalEndMs = $derived(new Date(config.festival_end).getTime());
	let votingStartMs = $derived(timeOrNaN(votingStatus?.voting_start));
	let votingEndMs = $derived(timeOrNaN(votingStatus?.voting_end));

	function timeOrNaN(iso: string | null | undefined): number {
		return iso ? new Date(iso).getTime() : Number.NaN;
	}

	let now = $state(Date.now());

	let phase = $derived(getFestivalPhase(now, festivalStartMs, festivalEndMs));
	let votingOpen = $derived(
		votingStatus !== undefined &&
			isVotingWindowOpen(votingStatus.voting_start, votingStatus.voting_end, now)
	);
	let votingEnded = $derived(hasVotingEnded(votingStatus?.voting_end, now));

	let snapshot = $derived(getStageSnapshot(data.schedule));
	let hasProgramme = $derived(data.schedule.length > 0);
	let hasSubscriptions = $derived(data.schedule.some((event) => event.user_subscription !== null));
	// Before the festival the steps are preparation; once it runs they are app setup.
	let readyHeading = $derived(
		phase === 'before' ? 'Подготовься к фестивалю' : 'Настрой приложение'
	);
	let showStage = $derived(phase === 'during' && hasProgramme);
	let showStaleNotice = $derived(
		showStage &&
			shouldShowStaleNotice({
				offlineMiss: false,
				stale: data.scheduleStale,
				isOnline: offline.isOnline
			})
	);

	// setTimeout delays are stored in a signed 32-bit int of milliseconds; a delay
	// past this (~24.8 days) overflows and fires immediately, so longer waits are
	// re-armed in chunks rather than firing early and never rescheduling.
	const MAX_TIMEOUT_MS = 2_147_483_647;

	// The festival phase and the voting card both turn on instants (festival start
	// and end, the voting window), and crossing one emits no event. So instead of a
	// ticker, arm one timeout to the next boundary: it bumps `now`, everything else
	// derives from that, then it re-arms for the following boundary. Re-runs (and
	// resyncs `now`) when the tab returns to the front, since a hidden tab's timers
	// can fire late. Reads Date.now(), never the `now` state, so the effect does not
	// re-run on its own writes.
	$effect(() => {
		if (!documentVisibility.current) return;

		const boundaries = [festivalStartMs, festivalEndMs, votingStartMs, votingEndMs];
		let timer: ReturnType<typeof setTimeout> | undefined;

		const tick = () => {
			const current = Date.now();
			now = current;
			const next = nextBoundary(boundaries, current);
			if (next === null) return;
			timer = setTimeout(tick, Math.min(next - current, MAX_TIMEOUT_MS));
		};
		tick();

		return () => clearTimeout(timer);
	});

	onMount(() => {
		// Refetch config (and the voting window it gates) on a change and on every
		// (re)connect, so the phase flips (e.g. organizers ending the festival)
		// without a reload, and a 'config_updated' missed while the stream was down
		// still self-heals. Firing on first connect just re-runs the freshly loaded
		// data once — harmless and idempotent.
		const reloadConfig = () => {
			void invalidate('app:config');
		};
		// "Now on stage" moves with every act the operator marks current, which
		// arrives as schedule_updated, as on the schedule page.
		const reloadSchedule = () => {
			void invalidate('app:schedule');
		};

		eventsClient.on('config_updated', reloadConfig);
		eventsClient.on('connection_established', reloadConfig);
		eventsClient.on('schedule_updated', reloadSchedule);

		return () => {
			eventsClient.off('config_updated', reloadConfig);
			eventsClient.off('connection_established', reloadConfig);
			eventsClient.off('schedule_updated', reloadSchedule);
		};
	});
</script>

<svelte:head>
	<title>ФАН ФАН</title>
</svelte:head>

<div class="flex flex-col gap-5 sm:gap-6">
	{#if phase !== 'during'}
		<HeroCard {phase} festivalStart={config.festival_start} />
	{/if}

	{#if showStaleNotice}
		<StaleDataNotice
			message="Нет связи. Показана сохранённая программа&nbsp;— обновится при подключении."
			cachedAt={data.scheduleCachedAt}
		/>
	{/if}

	{#if showStage}
		<NowOnStageCard {snapshot} />
	{/if}

	{#if votingOpen && votingStatus}
		<VotingCard status={votingStatus.status} />
	{/if}

	{#if phase !== 'after'}
		<GetReadySection
			heading={readyHeading}
			{user}
			{hasProgramme}
			{hasSubscriptions}
			{votingEnded}
			ticketAskedElsewhere={votingOpen && votingStatus?.status === 'no_ticket'}
		/>
	{/if}
</div>
