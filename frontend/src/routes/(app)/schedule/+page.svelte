<script lang="ts">
	import { afterNavigate, goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import BellRing from '@lucide/svelte/icons/bell-ring';
	import X from '@lucide/svelte/icons/x';
	import { createQuery } from '@tanstack/svelte-query';
	import { onDestroy, tick, untrack } from 'svelte';
	import { prefersReducedMotion } from 'svelte/motion';

	import type {
		ScheduleEntryWithSubscription,
		ScheduleEventWithSubscription
	} from '#lib/types/schedule.js';
	import type { ReadyView } from '#lib/utils/queryView.js';

	import {
		getPublicConfigOptions,
		getScheduleOptions,
		getSubscriptionsOptions
	} from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import { useQueuedSubscriptionChanges } from '#lib/api/queuedWrite.svelte.js';
	import EmptyState from '#lib/components/EmptyState.svelte';
	import QueryState from '#lib/components/QueryState.svelte';
	import SearchInput from '#lib/components/SearchInput.svelte';
	import StaleDataNotice from '#lib/components/StaleDataNotice.svelte';
	import { Button } from '#lib/components/ui/button/index.js';
	import * as ToggleGroup from '#lib/components/ui/toggle-group/index.js';
	import { FALLBACK_CONFIG } from '#lib/constants/festival.js';
	import { m } from '#lib/paraglide/messages.js';
	import { trackEvent } from '#lib/services/analytics.js';
	import { currentUserOptions } from '#lib/services/identity.js';
	import { reachability } from '#lib/services/reachability.js';
	import { queryView } from '#lib/utils/queryView.js';
	import {
		blockTitleByEventId,
		EMPTY_SCHEDULE,
		mergeSubscriptions,
		scheduleEvents,
		secondsUntilActs
	} from '#lib/utils/scheduleData.js';
	import { createSearchIndex } from '#lib/utils/search.js';

	import CurrentEventBar from './components/CurrentEventBar.svelte';
	import EventCard from './components/EventCard.svelte';
	import ScheduleNotificationsDialog from './components/ScheduleNotificationsDialog.svelte';
	import ScheduleSkeleton from './components/ScheduleSkeleton.svelte';
	import {
		buildScheduleFiltersQuery,
		parseScheduleFilters,
		type ScheduleFilters
	} from './scheduleFilters';
	import {
		buildScheduleGroups,
		filterScheduleGroups,
		type ScheduleBlockGroup
	} from './scheduleGrouping';

	const SEARCH_WRITE_DELAY_MS = 300;

	let showNotificationsDialog = $state(false);

	const userQuery = createQuery(() => currentUserOptions());
	let user = $derived(userQuery.data ?? null);

	const scheduleQuery = createQuery(() => getScheduleOptions());
	const subscriptionsQuery = createQuery(() => ({
		...getSubscriptionsOptions(),
		enabled: user !== null
	}));

	const queuedSubscriptions = useQueuedSubscriptionChanges();
	let subscriptions = $derived(user ? (subscriptionsQuery.data?.subscriptions ?? []) : []);
	let entries: ScheduleEntryWithSubscription[] = $derived(
		mergeSubscriptions(scheduleQuery.data ?? EMPTY_SCHEDULE, subscriptions, queuedSubscriptions)
	);
	let schedule: ScheduleEventWithSubscription[] = $derived(scheduleEvents(entries));
	const configQuery = createQuery(() => getPublicConfigOptions());
	let changeoverSeconds = $derived(
		(configQuery.data ?? FALLBACK_CONFIG).schedule_changeover_seconds
	);
	let secondsAhead = $derived(secondsUntilActs(schedule, changeoverSeconds));
	let scheduleView = $derived(
		queryView(scheduleQuery, {
			policy: 'cached',
			reachable: reachability.current,
			errorMessage: m.schedule_load_failed()
		})
	);

	let filters = $derived(parseScheduleFilters(page.url.searchParams));
	let showOnlySubscribed = $derived(filters.onlySubscribed);

	let searchQuery = $state(untrack(() => filters.search));

	// Counts turning a filter on, not each pause in typing.
	function trackFilterChange(next: ScheduleFilters) {
		if (!filters.search && next.search.trim()) trackEvent('schedule-filter', { kind: 'search' });
		if (!filters.onlySubscribed && next.onlySubscribed) {
			trackEvent('schedule-filter', { kind: 'mine' });
		}
	}

	function applyFilters(next: ScheduleFilters) {
		trackFilterChange(next);
		return goto(`${resolve('schedule')}${buildScheduleFiltersQuery(next)}`, {
			replace: true,
			reset: false
		});
	}

	let searchTimer: ReturnType<typeof setTimeout> | undefined;

	function cancelSearchWrite() {
		clearTimeout(searchTimer);
		searchTimer = undefined;
	}

	function writeSearchSoon() {
		cancelSearchWrite();
		searchTimer = setTimeout(() => {
			searchTimer = undefined;
			void applyFilters({ ...filters, search: searchQuery });
		}, SEARCH_WRITE_DELAY_MS);
	}

	onDestroy(cancelSearchWrite);

	afterNavigate(() => {
		if (searchTimer !== undefined) return;
		if (filters.search !== searchQuery.trim()) {
			searchQuery = filters.search;
		}
	});

	function getScope() {
		return showOnlySubscribed ? 'subscribed' : 'all';
	}

	function setScope(value: string) {
		if (value === '') return;
		cancelSearchWrite();
		void applyFilters({ search: searchQuery, onlySubscribed: value === 'subscribed' });
	}

	let currentEvent = $derived(schedule.find((event) => event.is_current) ?? null);

	let searchIndex = $derived.by(() => {
		const blockTitles = blockTitleByEventId(entries);
		return createSearchIndex(schedule, (event) => [
			event.number,
			event.title,
			blockTitles.get(event.id),
			event.nomination_title
		]);
	});

	let filtered: ScheduleEventWithSubscription[] = $derived(
		searchIndex
			.filter(searchQuery)
			.filter((event) => !showOnlySubscribed || event.user_subscription !== null)
	);

	let isCurrentEventFiltered = $derived(
		currentEvent !== null && !filtered.some((event) => event.id === currentEvent.id)
	);

	let allGroups = $derived(buildScheduleGroups(entries));
	let groupedSchedule = $derived(filterScheduleGroups(allGroups, filtered));

	let resultsSummary = $derived(
		filtered.length === schedule.length
			? m.schedule_total_events({ count: schedule.length })
			: m.results_shown_of({ count: filtered.length, total: schedule.length })
	);

	let hasActiveFilters = $derived(showOnlySubscribed || searchQuery.trim().length > 0);

	function resetFilters() {
		cancelSearchWrite();
		searchQuery = '';
		return applyFilters({ search: '', onlySubscribed: false });
	}

	let pageRoot: HTMLDivElement | null = null;
	let isCurrentRowOnScreen = $state(false);

	function capturePageRoot(node: HTMLDivElement) {
		pageRoot = node;

		return () => {
			if (pageRoot === node) {
				pageRoot = null;
			}
		};
	}

	function findEventRow(eventId: string) {
		return pageRoot?.querySelector<HTMLElement>(`[data-event-id="${eventId}"]`) ?? null;
	}

	async function scrollToCurrentEvent() {
		if (!currentEvent) return;

		if (isCurrentEventFiltered) {
			await resetFilters();
			await tick();
		}

		findEventRow(currentEvent.id)?.scrollIntoView({
			block: 'center',
			behavior: prefersReducedMotion.current ? 'instant' : 'smooth'
		});
	}

	$effect(() => {
		const eventId = currentEvent?.id;
		// eslint-disable-next-line @typescript-eslint/no-unused-expressions -- read only to track the filters
		groupedSchedule;
		if (!eventId || !pageRoot) return;

		const row = findEventRow(eventId);
		if (!row) {
			isCurrentRowOnScreen = false;
			return;
		}

		const observer = new IntersectionObserver((observed) => {
			isCurrentRowOnScreen = observed.some((entry) => entry.isIntersecting);
		});
		observer.observe(row);

		return () => observer.disconnect();
	});
</script>

<svelte:head>
	<title>{m.document_title({ title: m.nav_schedule() })}</title>
</svelte:head>

<QueryState view={scheduleView}>
	{#snippet loading()}
		<ScheduleSkeleton />
	{/snippet}

	{#snippet offline()}
		<EmptyState title={m.schedule_offline_title()} message={m.schedule_offline_message()} />
	{/snippet}

	{#snippet ready({ stale, cachedAt }: ReadyView<unknown>)}
		<div {@attach capturePageRoot} class="flex flex-col gap-4">
			{#if stale}
				<StaleDataNotice message={m.schedule_cached_notice()} {cachedAt} />
			{/if}

			<div class="flex flex-col gap-3">
				<SearchInput
					bind:value={searchQuery}
					name="schedule_search"
					label={m.schedule_search_label()}
					placeholder={m.schedule_search_placeholder()}
					oninput={writeSearchSoon}
					onclear={writeSearchSoon}
				/>

				<div class="flex items-center justify-between gap-3">
					<ToggleGroup.Root
						type="single"
						variant="outline"
						size="sm"
						bind:value={getScope, setScope}
						aria-label={m.schedule_filter_label()}
					>
						<ToggleGroup.Item value="all">{m.common_all()}</ToggleGroup.Item>
						<ToggleGroup.Item value="subscribed">{m.schedule_my_subscriptions()}</ToggleGroup.Item>
					</ToggleGroup.Root>

					<div class="flex items-center gap-2">
						<p
							class={['text-xs text-muted-foreground', !hasActiveFilters && 'sr-only']}
							aria-live="polite"
							role="status"
						>
							{resultsSummary}
						</p>
						{#if user}
							<Button
								variant="ghost"
								size="icon-sm"
								aria-label={m.schedule_notifications_button()}
								onclick={() => (showNotificationsDialog = true)}
							>
								<BellRing class="size-5" />
							</Button>
						{/if}
					</div>
				</div>
			</div>

			<div class="flex flex-col gap-6">
				{#each groupedSchedule as node (node.key)}
					{#if node.kind === 'interlude'}
						<div
							data-event-id={node.event.id}
							class="scroll-mt-28 overflow-clip rounded-xl border border-dashed border-border bg-muted/40 **:scroll-mt-28"
						>
							<EventCard
								event={node.event}
								{currentEvent}
								{user}
								secondsAhead={secondsAhead.get(node.event.id) ?? null}
								variant="interlude"
							/>
						</div>
					{:else}
						{@render blockSection(node)}
					{/if}
				{:else}
					{#if hasActiveFilters}
						<EmptyState title={m.common_nothing_found()} message={m.schedule_try_other_filters()}>
							<Button variant="outline" size="sm" onclick={resetFilters}>
								<X data-icon="inline-start" />
								{m.schedule_reset_filters()}
							</Button>
						</EmptyState>
					{:else}
						<EmptyState title={m.schedule_empty_title()} message={m.schedule_empty_message()} />
					{/if}
				{/each}
			</div>

			{#if currentEvent}
				<CurrentEventBar
					event={currentEvent}
					hidden={isCurrentRowOnScreen}
					onjump={scrollToCurrentEvent}
				/>
			{/if}
		</div>
	{/snippet}
</QueryState>

{#if user && showNotificationsDialog}
	<ScheduleNotificationsDialog bind:open={showNotificationsDialog} {user} />
{/if}

{#snippet blockSection(block: ScheduleBlockGroup)}
	<section class="flex flex-col gap-2">
		<div
			class="sticky z-20 bg-background/95 backdrop-blur-sm transition-[top] motion-reduce:transition-none reduced-transparency:bg-background"
			style:top="var(--sticky-top, 0px)"
			style:transition-duration="var(--sticky-top-duration, 0ms)"
			style:transition-timing-function="var(--sticky-top-easing, ease-out)"
		>
			<div class="flex min-h-11 items-center justify-between gap-3 px-1">
				<h2 class="truncate font-sans text-section tracking-tight text-foreground">
					{block.title}
				</h2>
				<span class="shrink-0 text-xs text-muted-foreground tabular-nums">
					{block.eventCount}
				</span>
			</div>
		</div>

		{#each block.nominations as nomination (nomination.key)}
			<div class="relative overflow-clip rounded-xl border border-border bg-card">
				{#if nomination.title !== null}
					<div
						class="sticky z-10 rounded-t-xl border-b border-border bg-card/95 px-3 py-2 backdrop-blur-sm transition-[top] motion-reduce:transition-none"
						style:top="calc(var(--sticky-top, 0px) + 2.75rem)"
						style:transition-duration="var(--sticky-top-duration, 0ms)"
						style:transition-timing-function="var(--sticky-top-easing, ease-out)"
					>
						<div class="flex items-center justify-between gap-3">
							<h3 class="min-w-0 truncate text-sm font-semibold text-foreground">
								{nomination.title}
							</h3>
							<span class="shrink-0 text-xs text-muted-foreground tabular-nums">
								{nomination.events.length}
							</span>
						</div>
					</div>
				{/if}

				<div class="divide-y divide-border">
					{#each nomination.events as event (event.id)}
						<div data-event-id={event.id} class="scroll-mt-28 **:scroll-mt-28">
							<EventCard
								{event}
								{currentEvent}
								{user}
								secondsAhead={secondsAhead.get(event.id) ?? null}
							/>
						</div>
					{/each}
				</div>
			</div>
		{/each}
	</section>
{/snippet}
