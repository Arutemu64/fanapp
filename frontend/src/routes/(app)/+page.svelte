<script lang="ts">
	import { createQuery, useQueryClient } from '@tanstack/svelte-query';
	import { onMount } from 'svelte';

	import {
		getPublicConfigOptions,
		getPublicConfigQueryKey,
		getScheduleOptions,
		getVotingStatusOptions,
		getVotingStatusQueryKey,
		listSubscriptionsOptions
	} from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import { useQueuedSubscriptionChanges } from '#lib/api/queuedWrite.svelte.js';
	import StaleDataNotice from '#lib/components/StaleDataNotice.svelte';
	import { FALLBACK_CONFIG } from '#lib/constants/festival.js';
	import { m } from '#lib/paraglide/messages.js';
	import { documentVisibility } from '#lib/services/documentVisibility.js';
	import { currentUserOptions } from '#lib/services/identity.js';
	import { type DevicePushState, getDevicePushState } from '#lib/services/pushDevice.svelte.js';
	import { getPwaService } from '#lib/services/pwa.svelte.js';
	import { reachability } from '#lib/services/reachability.js';
	import { queryView } from '#lib/utils/queryView.js';
	import { EMPTY_SCHEDULE, mergeSubscriptions, scheduleEvents } from '#lib/utils/scheduleData.js';
	import { hasVotingEnded, isVotingOpenNow } from '#lib/utils/votingStatus.js';

	import ContactLinks from './components/home/ContactLinks.svelte';
	import { getFestivalPhase, nextBoundary } from './components/home/festivalPhase';
	import GetReadySection from './components/home/GetReadySection.svelte';
	import GuideSections from './components/home/GuideSections.svelte';
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

	const configQuery = createQuery(() => getPublicConfigOptions());
	const scheduleQuery = createQuery(() => getScheduleOptions());
	const subscriptionsQuery = createQuery(() => ({
		...listSubscriptionsOptions(),
		enabled: user !== null
	}));
	const votingStatusQuery = createQuery(() => getVotingStatusOptions());

	let config = $derived(configQuery.data ?? FALLBACK_CONFIG);
	const queuedSubscriptions = useQueuedSubscriptionChanges();
	let subscriptions = $derived(user ? (subscriptionsQuery.data?.subscriptions ?? []) : []);
	let schedule = $derived(
		scheduleEvents(
			mergeSubscriptions(scheduleQuery.data ?? EMPTY_SCHEDULE, subscriptions, queuedSubscriptions)
		)
	);
	let votingStatus = $derived(reachability.current ? votingStatusQuery.data : undefined);

	const pwa = getPwaService();

	let festivalStartMs = $derived(new Date(config.festival_starts_at).getTime());
	let festivalEndMs = $derived(new Date(config.festival_ends_at).getTime());
	let votingStartMs = $derived(timeOrNaN(votingStatus?.voting_starts_at));
	let votingEndMs = $derived(timeOrNaN(votingStatus?.voting_ends_at));

	function timeOrNaN(iso: string | null | undefined): number {
		return iso ? new Date(iso).getTime() : Number.NaN;
	}

	let now = $state(Date.now());

	let phase = $derived(getFestivalPhase(now, festivalStartMs, festivalEndMs));
	let votingOpen = $derived(isVotingOpenNow(votingStatus, now));
	let votingEnded = $derived(hasVotingEnded(votingStatus?.voting_ends_at, now));

	let snapshot = $derived(getStageSnapshot(schedule, config.schedule_changeover_seconds));
	let hasProgramme = $derived(schedule.length > 0);
	let hasSubscriptions = $derived(schedule.some((event) => event.user_subscription !== null));
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

	let devicePush = $state<DevicePushState>('unknown');

	let install = $derived.by<InstallState>(() => {
		if (pwa.isInstalled) return 'installed';
		if (pwa.canInstall) return 'available';
		return 'unavailable';
	});

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
	let twoColumns = $derived(showStage && hasSupportingContent);
	let scheduleView = $derived(
		queryView(scheduleQuery, {
			policy: 'cached',
			reachable: reachability.current,
			errorMessage: m.schedule_load_failed()
		})
	);
	let showStaleNotice = $derived(showStage && scheduleView.kind === 'ready' && scheduleView.stale);

	const MAX_TIMEOUT_MS = 2_147_483_647;

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
	<HeroCard {phase} festivalStart={config.festival_starts_at} featured={featuredAct} />

	{#if showStaleNotice}
		<StaleDataNotice message={m.schedule_cached_notice()} cachedAt={scheduleQuery.dataUpdatedAt} />
	{/if}

	{#if showUpNext}
		<UpNextCard {snapshot} />
	{/if}
{/snippet}

<div class="flex flex-col gap-10">
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

	{#if phase !== 'after'}
		<GuideSections {phase} />
	{/if}

	<ContactLinks />
</div>
