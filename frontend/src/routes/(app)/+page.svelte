<script lang="ts">
	import { invalidate } from '$app/navigation';
	import { onMount } from 'svelte';

	import StaleDataNotice from '#lib/components/StaleDataNotice.svelte';
	import { documentVisibility } from '#lib/services/documentVisibility.js';
	import { getEventsClient } from '#lib/services/events.svelte.js';
	import { getPwaService } from '#lib/services/pwa.svelte.js';
	import { reachability } from '#lib/services/reachability.js';
	import { shouldShowStaleNotice } from '#lib/utils/offlineCache.js';
	import { type DevicePushState, getDevicePushState } from '#lib/utils/pushSubscription.js';
	import { hasVotingEnded, isVotingOpenNow } from '#lib/utils/votingStatus.js';

	import type { PageProps } from './$types';

	import { getFestivalPhase, nextBoundary } from './components/home/festivalPhase';
	import GetReadySection from './components/home/GetReadySection.svelte';
	import HeroCard from './components/home/HeroCard.svelte';
	import {
		getNotificationsOn,
		getReadySteps,
		type InstallState
	} from './components/home/readySteps';
	import { getStageSnapshot } from './components/home/stage';
	import UpNextCard from './components/home/UpNextCard.svelte';
	import VotingCard from './components/home/VotingCard.svelte';

	let { data }: PageProps = $props();
	let user = $derived(data.user);
	let config = $derived(data.config);
	let votingStatus = $derived(data.votingStatus);

	const eventsClient = getEventsClient();
	const pwa = getPwaService();

	let festivalStartMs = $derived(new Date(config.festival_start).getTime());
	let festivalEndMs = $derived(new Date(config.festival_end).getTime());
	let votingStartMs = $derived(timeOrNaN(votingStatus?.voting_start));
	let votingEndMs = $derived(timeOrNaN(votingStatus?.voting_end));

	function timeOrNaN(iso: string | null | undefined): number {
		return iso ? new Date(iso).getTime() : Number.NaN;
	}

	let now = $state(Date.now());

	let phase = $derived(getFestivalPhase(now, festivalStartMs, festivalEndMs));
	let votingOpen = $derived(isVotingOpenNow(votingStatus, now));
	let votingEnded = $derived(hasVotingEnded(votingStatus?.voting_end, now));

	let snapshot = $derived(getStageSnapshot(data.schedule));
	let hasProgramme = $derived(data.schedule.length > 0);
	let hasSubscriptions = $derived(data.schedule.some((event) => event.user_subscription !== null));
	// Before the festival the steps are preparation; once it runs they are app setup.
	let readyHeading = $derived(
		phase === 'before' ? 'Подготовься к фестивалю' : 'Настрой приложение'
	);
	let showStage = $derived(phase === 'during' && hasProgramme);
	let featuredAct = $derived(phase === 'during' ? snapshot.featured : null);
	let showUpNext = $derived(
		showStage &&
			(snapshot.upNext.length > 0 ||
				snapshot.nextSubscribed !== null ||
				snapshot.featured?.live === true)
	);
	let ticketAskedElsewhere = $derived(votingOpen && votingStatus?.status === 'no_ticket');

	// Read once per visit: coming back from the notifications page remounts home,
	// which re-checks. 'unknown' until the browser answers keeps the step out
	// rather than flashing a step that turns out to be done.
	let devicePush = $state<DevicePushState>('unknown');

	let install = $derived.by<InstallState>(() => {
		if (pwa.isInstalled) return 'installed';
		if (pwa.canInstall) return 'available';
		return 'unavailable';
	});

	// Decided here rather than in the section, because the layout depends on it:
	// the side column exists only when it has something to hold.
	let readySteps = $derived.by(() => {
		if (phase === 'after') return [];
		return getReadySteps({
			signedIn: user !== null,
			hasTicket: user?.ticket != null,
			votingEnded,
			ticketAskedElsewhere,
			hasProgramme,
			hasSubscriptions,
			notificationsOn: getNotificationsOn(user, devicePush),
			install,
			installBeforeNotifications: pwa.pushRequiresInstall
		});
	});

	let hasSupportingContent = $derived(votingOpen || readySteps.length > 0);
	// Material's supporting-pane layout: the live programme is the main pane (about
	// two-thirds) and voting plus setup sit beside it on wide screens, stacked below
	// on narrow ones (https://developer.android.com/guide/topics/ui/layout/canonical-layouts).
	// From xl only: below that the sidebar leaves too little width for a usable side
	// pane, and even at 2:1 rather than Material's 70/30 it is only ~310px wide.
	let twoColumns = $derived(showStage && hasSupportingContent);
	let showStaleNotice = $derived(
		showStage &&
			shouldShowStaleNotice({
				offlineMiss: false,
				stale: data.scheduleStale,
				isOnline: reachability.current
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
	// re-run on its own writes. A boundary that fires also refetches the voting
	// status, as the voting layout does: a `disabled` loaded just before the window
	// opened would otherwise keep the voting card hidden until a reload.
	$effect(() => {
		if (!documentVisibility.current) return;

		const boundaries = [festivalStartMs, festivalEndMs, votingStartMs, votingEndMs];
		let timer: ReturnType<typeof setTimeout> | undefined;

		const tick = (fired: boolean) => {
			const current = Date.now();
			now = current;
			if (fired) void invalidate('app:config');
			const next = nextBoundary(boundaries, current);
			if (next === null) return;
			timer = setTimeout(() => tick(true), Math.min(next - current, MAX_TIMEOUT_MS));
		};
		tick(false);

		return () => clearTimeout(timer);
	});

	onMount(() => {
		void getDevicePushState().then((state) => {
			devicePush = state;
		});

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

{#snippet supporting()}
	{#if votingOpen && votingStatus}
		<VotingCard status={votingStatus.status} />
	{/if}

	<GetReadySection heading={readyHeading} steps={readySteps} />
{/snippet}

{#snippet main()}
	<HeroCard {phase} festivalStart={config.festival_start} featured={featuredAct} />

	{#if showStaleNotice}
		<StaleDataNotice
			message="Нет связи. Показана сохранённая программа&nbsp;— обновится при подключении."
			cachedAt={data.scheduleCachedAt}
		/>
	{/if}

	{#if showUpNext}
		<UpNextCard {snapshot} />
	{/if}
{/snippet}

{#if twoColumns}
	<div
		class="flex flex-col gap-5 sm:gap-6 xl:grid xl:grid-cols-[minmax(0,2fr)_minmax(0,1fr)] xl:items-start"
	>
		<div class="flex flex-col gap-5 sm:gap-6">
			{@render main()}
		</div>
		<div class="flex flex-col gap-5 sm:gap-6">
			{@render supporting()}
		</div>
	</div>
{:else}
	<div class="flex flex-col gap-5 sm:gap-6">
		{@render main()}
		{@render supporting()}
	</div>
{/if}
