<script lang="ts">
	import { createQuery, useQueryClient } from '@tanstack/svelte-query';
	import { onMount } from 'svelte';

	import {
		getPublicConfigOptions,
		getPublicConfigQueryKey,
		getScheduleOptions,
		getSubscriptionsOptions,
		getVotingStatusOptions,
		getVotingStatusQueryKey
	} from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import StaleDataNotice from '#lib/components/StaleDataNotice.svelte';
	import { FALLBACK_CONFIG } from '#lib/constants/festival.js';
	import { m } from '#lib/paraglide/messages.js';
	import { documentVisibility } from '#lib/services/documentVisibility.js';
	import { currentUserOptions } from '#lib/services/identity.js';
	import { type DevicePushState, getDevicePushState } from '#lib/services/pushDevice.svelte.js';
	import { getPwaService } from '#lib/services/pwa.svelte.js';
	import { reachability } from '#lib/services/reachability.js';
	import { queryView } from '#lib/utils/queryView.js';
	import { mergeSubscriptions, scheduleEvents } from '#lib/utils/scheduleData.js';
	import { hasVotingEnded, isVotingOpenNow } from '#lib/utils/votingStatus.js';

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

	const queryClient = useQueryClient();
	const userQuery = createQuery(() => currentUserOptions());
	let user = $derived(userQuery.data ?? null);

	// Public config drives the hero's phase and countdown, so it renders for guests
	// and offline: the cached copy, or the shipped defaults on a first-ever visit
	// made offline. The phase is computed from the clock, so a cached copy still
	// flips to "after" on time; only an organizer's date edit waits for the refetch.
	const configQuery = createQuery(() => getPublicConfigOptions());
	const scheduleQuery = createQuery(() => getScheduleOptions());
	const subscriptionsQuery = createQuery(() => ({
		...getSubscriptionsOptions(),
		enabled: user !== null
	}));
	const votingStatusQuery = createQuery(() => getVotingStatusOptions());

	let config = $derived(configQuery.data ?? FALLBACK_CONFIG);
	// A guest has no subscriptions, whatever an earlier session left cached.
	let subscriptions = $derived(user ? (subscriptionsQuery.data?.subscriptions ?? []) : []);
	let schedule = $derived(
		scheduleEvents(mergeSubscriptions(scheduleQuery.data?.schedule ?? [], subscriptions))
	);
	// Voting status is a live read: a stale "open" offline would lead to a ballot
	// that can't be submitted, so offline it is treated as unknown and every
	// voting surface on this page hides.
	let votingStatus = $derived(reachability.current ? votingStatusQuery.data : undefined);

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

	let snapshot = $derived(getStageSnapshot(schedule));
	let hasProgramme = $derived(schedule.length > 0);
	let hasSubscriptions = $derived(schedule.some((event) => event.user_subscription !== null));
	// Before the festival the steps are preparation; once it runs they are app setup.
	let readyHeading = $derived(
		phase === 'before' ? m.home_ready_heading_before() : m.home_ready_heading_setup()
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
	// Home renders no offline or error state of its own (it falls back to the hero),
	// so it reads only the stale flag.
	let scheduleView = $derived(
		queryView(scheduleQuery, {
			policy: 'cached',
			reachable: reachability.current,
			errorMessage: m.schedule_load_failed()
		})
	);
	let showStaleNotice = $derived(showStage && scheduleView.kind === 'ready' && scheduleView.stale);

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
	// re-run on its own writes. A boundary that fires also refetches the config and
	// voting status, as the voting layout does: a `disabled` loaded just before the
	// window opened would otherwise keep the voting card hidden until a reload.
	$effect(() => {
		if (!documentVisibility.current) return;

		const boundaries = [festivalStartMs, festivalEndMs, votingStartMs, votingEndMs];
		let timer: ReturnType<typeof setTimeout> | undefined;

		const tick = (fired: boolean) => {
			const current = Date.now();
			now = current;
			if (fired) {
				void queryClient.invalidateQueries({ queryKey: getPublicConfigQueryKey() });
				void queryClient.invalidateQueries({ queryKey: getVotingStatusQueryKey() });
			}
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
	});
</script>

<svelte:head>
	<title>{m.app_name()}</title>
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
		<StaleDataNotice message={m.schedule_cached_notice()} cachedAt={scheduleQuery.dataUpdatedAt} />
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
