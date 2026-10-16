<script lang="ts">
	import { Search as SearchIcon, X } from '@lucide/svelte';
	import { createQuery } from '@tanstack/svelte-query';
	import { tick } from 'svelte';
	import { prefersReducedMotion } from 'svelte/motion';

	import type {
		ScheduleEntryWithSubscription,
		ScheduleEventWithSubscription
	} from '#lib/types/schedule.js';

	import { getApiErrorDetail } from '#lib/api/errors.js';
	import {
		getScheduleOptions,
		getSubscriptionsOptions
	} from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import { currentUserOptions } from '#lib/api/index.js';
	import ErrorState from '#lib/components/ErrorState.svelte';
	import StaleDataNotice from '#lib/components/StaleDataNotice.svelte';
	import { Button } from '#lib/components/ui/button/index.js';
	import { Input } from '#lib/components/ui/input/index.js';
	import * as ToggleGroup from '#lib/components/ui/toggle-group/index.js';
	import { m } from '#lib/paraglide/messages.js';
	import { reachability } from '#lib/services/reachability.js';
	import {
		blockTitleByEventId,
		mergeSubscriptions,
		scheduleEvents
	} from '#lib/utils/scheduleData.js';
	import { createSearchIndex } from '#lib/utils/search.js';

	import CurrentEventBar from './components/CurrentEventBar.svelte';
	import EventCard from './components/EventCard.svelte';
	import ScheduleSkeleton from './components/ScheduleSkeleton.svelte';
	import {
		buildScheduleGroups,
		filterScheduleGroups,
		type ScheduleBlockGroup
	} from './scheduleGrouping';

	const userQuery = createQuery(() => currentUserOptions());
	let user = $derived(userQuery.data ?? null);

	const scheduleQuery = createQuery(() => getScheduleOptions());
	const subscriptionsQuery = createQuery(() => ({
		...getSubscriptionsOptions(),
		enabled: user !== null
	}));

	// A guest has no subscriptions, whatever an earlier session left cached.
	let subscriptions = $derived(user ? (subscriptionsQuery.data?.subscriptions ?? []) : []);
	let entries: ScheduleEntryWithSubscription[] = $derived(
		mergeSubscriptions(scheduleQuery.data?.schedule ?? [], subscriptions)
	);
	let schedule: ScheduleEventWithSubscription[] = $derived(scheduleEvents(entries));
	// Nothing saved yet and no way to fetch it: a calm inline state that keeps the
	// app shell usable, not an error.
	let offlineMiss = $derived(scheduleQuery.data === undefined && !reachability.current);

	// Store filter state locally because it only affects this page view.
	let searchQuery: string = $state('');
	let showOnlySubscribed: boolean = $state(false);

	// A single-select toggle group clears its value when the pressed item is tapped
	// again. The function binding below keeps the group fully controlled
	// (https://bits-ui.com/docs/components/toggle-group): the setter ignores the
	// clear, and the getter hands the real scope back, so one scope always stays
	// selected, like a segmented control. A one-way `value` would let the group's
	// own state drift from the filter.
	function getScope() {
		return showOnlySubscribed ? 'subscribed' : 'all';
	}

	function setScope(value: string) {
		if (value === '') return;
		showOnlySubscribed = value === 'subscribed';
	}

	// We use the full schedule current event for countdown labels inside every row.
	let currentEvent = $derived(schedule.find((event) => event.is_current) ?? null);

	// What's on screen may be out of date: the last refetch failed, or the server
	// is out of reach.
	let showStaleNotice = $derived(
		scheduleQuery.data !== undefined && (scheduleQuery.isRefetchError || !reachability.current)
	);

	// Rebuilt only when the schedule reloads, so a keystroke re-runs token
	// comparisons instead of re-normalizing every field of every row.
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

	// The current event's row can be filtered out while the event is still on stage.
	let isCurrentEventFiltered = $derived(
		currentEvent !== null && !filtered.some((event) => event.id === currentEvent.id)
	);

	// Group rows into block and nomination sections so we can make headers sticky.
	// Built off the unfiltered schedule (recomputes only on reload); the filter
	// pass below reuses these groups so a keystroke never re-groups. See
	// scheduleGrouping.ts for the keying contract that keeps rows stable.
	let allGroups = $derived(buildScheduleGroups(entries));
	let groupedSchedule = $derived(filterScheduleGroups(allGroups, filtered));

	let resultsSummary = $derived(
		filtered.length === schedule.length
			? m.schedule_total_events({ count: schedule.length })
			: m.results_shown_of({ count: filtered.length, total: schedule.length })
	);

	let hasActiveFilters = $derived(showOnlySubscribed || searchQuery.trim().length > 0);

	// Recovery for the no-results state: clear search + subscription filter in one tap
	// so a user mid-event isn't stuck hunting back to two separate controls.
	function resetFilters() {
		searchQuery = '';
		showOnlySubscribed = false;
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

		// The bar stays up while a filter hides the row, so tapping it clears the
		// filters first and waits for the row to render.
		if (isCurrentEventFiltered) {
			resetFilters();
			await tick();
		}

		// An explicit 'smooth' animates even for users who opted out of motion, so it
		// follows the preference (https://developer.mozilla.org/en-US/docs/Web/API/Element/scrollIntoView).
		findEventRow(currentEvent.id)?.scrollIntoView({
			block: 'center',
			behavior: prefersReducedMotion.current ? 'instant' : 'smooth'
		});
	}

	// Watches the current row against the viewport, so the bar steps aside while
	// the row it points at is already visible. An observer rather than a scroll
	// listener: no layout reads on every scroll frame. Re-runs when the current event,
	// the filters (which mount and unmount rows) or the page root change.
	$effect(() => {
		const eventId = currentEvent?.id;
		void groupedSchedule;
		if (!eventId || !pageRoot) return;

		const row = findEventRow(eventId);
		if (!row) {
			isCurrentRowOnScreen = false;
			return;
		}

		const observer = new IntersectionObserver((entries) => {
			isCurrentRowOnScreen = entries.some((entry) => entry.isIntersecting);
		});
		observer.observe(row);

		return () => observer.disconnect();
	});
</script>

<svelte:head>
	<title>{m.document_title({ title: m.nav_schedule() })}</title>
</svelte:head>

{#if scheduleQuery.data === undefined && !offlineMiss}
	{#if scheduleQuery.isError}
		<ErrorState
			variant="inline"
			onRetry={() => void scheduleQuery.refetch()}
			error={{
				status: 500,
				message: getApiErrorDetail(scheduleQuery.error) ?? m.schedule_load_failed()
			}}
		/>
	{:else}
		<ScheduleSkeleton />
	{/if}
{:else}
	<div {@attach capturePageRoot} class="flex flex-col gap-4">
		{#if showStaleNotice}
			<StaleDataNotice
				message={m.schedule_cached_notice()}
				cachedAt={scheduleQuery.dataUpdatedAt}
			/>
		{/if}

		<!-- Controls sit straight on the page, not in a card: DESIGN "When not to" use a
	     card. Search plus a scope switch under it is the iOS search-field + scope-bar
	     pattern (https://developer.apple.com/design/human-interface-guidelines/search-fields).
	     Kept static so the schedule's block headers can be the sticky ones. -->
		<div class="flex flex-col gap-3">
			<div class="relative flex items-center">
				<SearchIcon class="pointer-events-none absolute left-3 size-4 text-muted-foreground" />
				<Input
					bind:value={searchQuery}
					name="schedule_search"
					aria-label={m.schedule_search_label()}
					placeholder={m.schedule_search_placeholder()}
					autocomplete="off"
					spellcheck={false}
					class="pr-8 pl-9"
				/>
				{#if searchQuery}
					<button
						type="button"
						class="absolute right-2 text-muted-foreground hover:text-foreground"
						onclick={() => (searchQuery = '')}
						aria-label={m.common_clear_search()}
					>
						<X class="size-4" />
					</button>
				{/if}
			</div>

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

				<!-- Always mounted so screen readers hear the list shrink and grow, but shown
			     only while a filter is on: an unfiltered total tells a sighted user nothing. -->
				<p
					class={['text-xs text-muted-foreground', !hasActiveFilters && 'sr-only']}
					aria-live="polite"
					role="status"
				>
					{resultsSummary}
				</p>
			</div>
		</div>

		<div class="flex flex-col gap-6">
			{#each groupedSchedule as node (node.key)}
				{#if node.kind === 'interlude'}
					<!-- A row above the first block (the opening) sits outside the block sections
				     as a lighter, dashed row so it reads as an interlude, not a block card.
				     Still interactive (mark-current, skip) via EventCard's interlude variant. -->
					<div
						data-event-id={node.event.id}
						class="scroll-mt-28 overflow-clip rounded-xl border border-dashed border-border bg-muted/40 **:scroll-mt-28"
					>
						<EventCard event={node.event} {currentEvent} {user} variant="interlude" />
					</div>
				{:else}
					{@render blockSection(node)}
				{/if}
			{:else}
				<div
					class="rounded-2xl border border-dashed border-border bg-card px-4 py-10 text-center sm:py-14"
				>
					<p class="text-base font-bold text-foreground">
						{#if offlineMiss}
							{m.schedule_offline_title()}
						{:else if hasActiveFilters}
							{m.common_nothing_found()}
						{:else}
							{m.schedule_empty_title()}
						{/if}
					</p>
					<p class="mt-1 text-sm text-muted-foreground">
						{#if offlineMiss}
							{m.schedule_offline_message()}
						{:else if hasActiveFilters}
							{m.schedule_try_other_filters()}
						{:else}
							{m.schedule_empty_message()}
						{/if}
					</p>

					<!-- No-results recovery: one tap clears every active filter. Hidden on the
				     first-use empty state, where there's nothing to reset. -->
					{#if hasActiveFilters}
						<Button variant="outline" size="sm" class="mt-4" onclick={resetFilters}>
							<X data-icon="inline-start" />
							{m.schedule_reset_filters()}
						</Button>
					{/if}
				</div>
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
{/if}

<!-- A block section: sticky block header + its nomination cards. Taken as a
	snippet so the {#each} above narrows a node to a concrete ScheduleBlockGroup
	before rendering, keeping the union out of this markup. -->
{#snippet blockSection(block: ScheduleBlockGroup)}
	<section class="flex flex-col gap-2">
		<!-- Keep the active block visible while the user scrolls through dense rows. -->
		<!-- Inter (not display): block headers are repeated structural data, and DESIGN reserves Unbounded for rare identity moments. -->
		<!-- A plain heading on the page background, not a card: the nomination cards under it
		     already group the rows, so a framed header would be a box stacked on boxes
		     (DESIGN "No boxes in boxes"). Size/weight carry the hierarchy; the count stays
		     gray because it is not a state (Color-Earns-Its-Place). -->
		<!-- top / transition come from the (app) layout's <main> (--sticky-top): a bare top-0
			would tuck the header under the top bar. See the note there. -->
		<div
			class="sticky z-20 bg-background/95 backdrop-blur-sm transition-[top] ease-out motion-reduce:transition-none reduced-transparency:bg-background"
			style:top="var(--sticky-top, 0px)"
			style:transition-duration="var(--sticky-top-duration, 0ms)"
		>
			<!-- min-h-11 is load-bearing: the nomination header sticks 2.75rem below this one. -->
			<div class="flex min-h-11 items-center justify-between gap-3 px-1">
				<h2 class="truncate text-section tracking-tight text-foreground">
					{block.title}
				</h2>
				<span class="shrink-0 text-xs text-muted-foreground tabular-nums">
					{block.eventCount}
				</span>
			</div>
		</div>

		{#each block.nominations as nomination (nomination.key)}
			<!-- Clip the card edges without creating a new scroll container, so sticky headers keep working. -->
			<div class="relative overflow-clip rounded-xl border border-border bg-card">
				<!-- Stick the nomination header below the block header for better context.
				     Skipped when a block's rows carry no nomination — there is nothing to label. -->
				{#if nomination.title !== null}
					<!-- Stacks 2.75rem below the block header (its min-h-11), sharing the layout's
						--sticky-top offset so both track the top bar together. -->
					<div
						class="sticky z-10 rounded-t-xl border-b border-border bg-card/95 px-3 py-2 backdrop-blur-sm transition-[top] ease-out motion-reduce:transition-none"
						style:top="calc(var(--sticky-top, 0px) + 2.75rem)"
						style:transition-duration="var(--sticky-top-duration, 0ms)"
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
						<!-- The margin reaches every descendant too: keyboard focus scrolls the focused
							control into view, not its row, and it must clear the sticky headers. -->
						<div data-event-id={event.id} class="scroll-mt-28 **:scroll-mt-28">
							<EventCard {event} {currentEvent} {user} />
						</div>
					{/each}
				</div>
			</div>
		{/each}
	</section>
{/snippet}
