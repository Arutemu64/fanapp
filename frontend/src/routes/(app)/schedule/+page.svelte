<script lang="ts">
	import { invalidate } from '$app/navigation';
	import { page } from '$app/state';
	import { ChevronUp, Play, Search as SearchIcon, X } from '@lucide/svelte';
	import { onMount } from 'svelte';

	import type { CurrentUserDto } from '#lib/api/generated/index.js';
	import type { ScheduleEventWithSubscription } from '#lib/types/schedule.js';

	import StaleDataNotice from '#lib/components/StaleDataNotice.svelte';
	import { Button } from '#lib/components/ui/button/index.js';
	import { Input } from '#lib/components/ui/input/index.js';
	import * as ToggleGroup from '#lib/components/ui/toggle-group/index.js';
	import { documentVisibility } from '#lib/services/documentVisibility.js';
	import { getEventsClient } from '#lib/services/events.svelte.js';
	import { reachability } from '#lib/services/reachability.js';
	import { shouldShowStaleNotice } from '#lib/utils/offlineCache.js';
	import { createSearchIndex } from '#lib/utils/search.js';

	import type { PageProps } from './$types';

	import EventCard from './components/EventCard.svelte';
	import {
		buildScheduleGroups,
		filterScheduleGroups,
		type ScheduleBlockGroup
	} from './scheduleGrouping';

	// Mirror the loaded page data so the component reads schedule from one local source.
	let { data }: PageProps = $props();
	let schedule: ScheduleEventWithSubscription[] = $derived(data.schedule);

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
	let user: CurrentUserDto | null = $derived(page.data.user);

	const eventsClient = getEventsClient();
	let showStaleNotice = $derived(
		shouldShowStaleNotice({
			offlineMiss: data.offlineMiss,
			stale: data.stale,
			isOnline: reachability.current
		})
	);

	// Rebuilt only when the schedule reloads, so a keystroke re-runs token
	// comparisons instead of re-normalizing every field of every row.
	let searchIndex = $derived(
		createSearchIndex(schedule, (event) => [
			event.number,
			event.title,
			event.block_title,
			event.nomination_title
		])
	);

	let filtered: ScheduleEventWithSubscription[] = $derived(
		searchIndex
			.filter(searchQuery)
			.filter((event) => !showOnlySubscribed || event.user_subscription !== null)
	);

	// Hide the FAB for the current event when the active filters remove that row from the page.
	let visibleCurrentEvent = $derived(filtered.find((event) => event.is_current) ?? null);

	// Group rows into block and nomination sections so we can make headers sticky.
	// Built off the unfiltered schedule (recomputes only on reload); the filter
	// pass below reuses these groups so a keystroke never re-groups. See
	// scheduleGrouping.ts for the keying contract that keeps rows stable.
	let allGroups = $derived(buildScheduleGroups(schedule));
	let groupedSchedule = $derived(filterScheduleGroups(allGroups, filtered));

	let resultsSummary = $derived(
		filtered.length === schedule.length
			? `Всего выступлений: ${schedule.length}`
			: `Показано ${filtered.length} из ${schedule.length}`
	);

	let hasActiveFilters = $derived(showOnlySubscribed || searchQuery.trim().length > 0);

	// Recovery for the no-results state: clear search + subscription filter in one tap
	// so a user mid-event isn't stuck hunting back to two separate controls.
	function resetFilters() {
		searchQuery = '';
		showOnlySubscribed = false;
	}

	let pageRoot: HTMLDivElement | null = null;
	let showScrollTopButton = $state(false);

	function capturePageRoot(node: HTMLDivElement) {
		pageRoot = node;

		return () => {
			if (pageRoot === node) {
				pageRoot = null;
			}
		};
	}

	function getScrollContainer() {
		// Matched by id, not tag: the layout's scrolling region is the SkipLink target, and
		// its element has already changed once (section -> main) — which silently broke this.
		const container = pageRoot?.closest('#main-content');

		return container instanceof HTMLElement ? container : null;
	}

	function scrollToCurrentEvent() {
		if (!visibleCurrentEvent || !pageRoot) return;

		const element = pageRoot.querySelector<HTMLElement>(
			`[data-event-id="${visibleCurrentEvent.id}"]`
		);

		// No `behavior` in either scroll: the default ('auto') takes <main>'s CSS
		// scroll-behavior, smooth normally and instant under reduced motion (app.css). An
		// explicit 'smooth' would override that and animate for users who opted out
		// (https://developer.mozilla.org/en-US/docs/Web/API/Element/scrollTo).
		element?.scrollIntoView({ block: 'center' });
	}

	function scrollToTop() {
		getScrollContainer()?.scrollTo({ top: 0 });
	}

	// The button appears only once the way back is long: NN/g advises holding a
	// back-to-top control until the user has scrolled down several screens
	// (https://www.nngroup.com/articles/back-to-top/). Measured in screens, not pixels,
	// so it scales with the phone; re-tapping the active tab covers shorter trips.
	const SCROLL_TOP_AFTER_SCREENS = 2;

	const VISIBILITY_REFETCH_THROTTLE_MS = 30000;
	// Seeded to now: the page has just loaded fresh data, so the initial visible
	// state must not trip the foreground refetch below.
	let lastRefetch = Date.now();

	// Also refetch on every (re)connect, so a schedule_updated missed while the SSE
	// stream was down doesn't leave a stale page.
	function reloadSchedule() {
		lastRefetch = Date.now();
		void invalidate('app:schedule');
	}

	// Shorter background trips (<60s) can lose an SSE event without triggering a
	// reconnect — refetch on return to the foreground to catch up, throttled so a
	// quick tab-flip doesn't refetch what we just loaded. Tracks only visibility;
	// lastRefetch is a plain read so an SSE-driven reload never re-runs this.
	$effect(() => {
		if (!documentVisibility.current) return;
		if (Date.now() - lastRefetch < VISIBILITY_REFETCH_THROTTLE_MS) return;
		reloadSchedule();
	});

	onMount(() => {
		const scrollContainer = getScrollContainer();

		const updateScrollState = () => {
			if (!scrollContainer) return;
			const threshold = scrollContainer.clientHeight * SCROLL_TOP_AFTER_SCREENS;
			showScrollTopButton = scrollContainer.scrollTop > threshold;
		};

		updateScrollState();
		scrollContainer?.addEventListener('scroll', updateScrollState, { passive: true });
		eventsClient.on('schedule_updated', reloadSchedule);
		eventsClient.on('connection_established', reloadSchedule);

		return () => {
			scrollContainer?.removeEventListener('scroll', updateScrollState);
			eventsClient.off('schedule_updated', reloadSchedule);
			eventsClient.off('connection_established', reloadSchedule);
		};
	});
</script>

<svelte:head>
	<title>Программа · ФАН ФАН</title>
</svelte:head>

<div {@attach capturePageRoot} class="flex flex-col gap-4">
	{#if showStaleNotice}
		<StaleDataNotice
			message="Нет связи. Показана сохранённая программа — обновится при подключении."
			cachedAt={data.cachedAt}
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
				aria-label="Поиск по программе"
				placeholder="Поиск по номеру или названию…"
				autocomplete="off"
				spellcheck={false}
				class="pr-8 pl-9"
			/>
			{#if searchQuery}
				<button
					type="button"
					class="absolute right-2 text-muted-foreground hover:text-foreground"
					onclick={() => (searchQuery = '')}
					aria-label="Очистить поиск"
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
				aria-label="Какие выступления показать"
			>
				<ToggleGroup.Item value="all">Все</ToggleGroup.Item>
				<ToggleGroup.Item value="subscribed">Мои подписки</ToggleGroup.Item>
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
				<!-- A block-less row (break, opening, closing) sits between block sections
				     as a lighter, dashed row so it reads as an interlude, not a block card.
				     Still interactive (mark-current, skip) via EventCard's interlude variant. -->
				<div
					data-event-id={node.event.id}
					class="scroll-mt-28 overflow-clip rounded-xl border border-dashed border-border bg-muted/40"
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
					{#if data.offlineMiss}
						Программа недоступна офлайн
					{:else if hasActiveFilters}
						Ничего не нашлось
					{:else}
						Программа пока пуста
					{/if}
				</p>
				<p class="mt-1 text-sm text-muted-foreground">
					{#if data.offlineMiss}
						Появится после подключения к интернету
					{:else if hasActiveFilters}
						Попробуй изменить поиск или фильтры
					{:else}
						Программа появится ближе к фестивалю
					{/if}
				</p>

				<!-- No-results recovery: one tap clears every active filter. Hidden on the
				     first-use empty state, where there's nothing to reset. -->
				{#if hasActiveFilters}
					<Button variant="outline" size="sm" class="mt-4" onclick={resetFilters}>
						<X data-icon="inline-start" />
						Сбросить фильтры
					</Button>
				{/if}
			</div>
		{/each}
	</div>

	{#if visibleCurrentEvent || showScrollTopButton}
		<!-- Lift FAB actions above the floating bottom mobile navigation so they stay
			tappable. The right inset keeps them clear of a landscape phone's notch and
			rounded corners; on desktop the bottom inset clears the home indicator. -->
		<div
			class="pointer-events-none fixed right-[calc(1rem+env(safe-area-inset-right))] bottom-[calc(var(--bottom-nav-clearance)+1rem)] z-30 md:bottom-[calc(1.5rem+env(safe-area-inset-bottom))]"
		>
			<div class="flex flex-col items-end gap-2">
				{#if showScrollTopButton}
					<Button
						variant="floating"
						size="sm"
						class="pointer-events-auto size-12 rounded-full px-0 lg:w-32 lg:rounded-full lg:px-3"
						onclick={scrollToTop}
						aria-label="Подняться наверх"
					>
						<ChevronUp class="size-5 shrink-0" />
						<span class="sr-only lg:not-sr-only lg:ml-2">Наверх</span>
					</Button>
				{/if}

				{#if visibleCurrentEvent}
					<Button
						size="sm"
						class="pointer-events-auto size-12 rounded-full bg-success px-0 text-success-foreground shadow-lg hover:bg-success/90 lg:w-32 lg:rounded-full lg:px-3"
						onclick={scrollToCurrentEvent}
						aria-label="Перейти к текущему выступлению"
					>
						<Play class="size-5 shrink-0 fill-current" />
						<span class="sr-only lg:not-sr-only lg:ml-2">Текущее</span>
					</Button>
				{/if}
			</div>
		</div>
	{/if}
</div>

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
			would leave a gap under the hidden top bar. See the note there. -->
		<div
			class="sticky z-20 bg-background/95 backdrop-blur transition-[top] ease-out motion-reduce:transition-none reduced-transparency:bg-background"
			style:top="var(--sticky-top, 0px)"
			style:transition-duration="var(--sticky-top-duration, 0ms)"
		>
			<!-- min-h-11 is load-bearing: the nomination header sticks 2.75rem below this one. -->
			<div class="flex min-h-11 items-center justify-between gap-3 px-1">
				<h2 class="truncate text-base font-semibold tracking-tight text-foreground">
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
						class="sticky z-10 rounded-t-xl border-b border-border bg-card/95 px-3 py-2 backdrop-blur transition-[top] ease-out motion-reduce:transition-none"
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

				<!-- Row divider sits at full border strength, one step stronger than the
				     in-card staff-strip separator (border-border/50), so event boundaries
				     read as the primary split and the strip separator stays subordinate. -->
				<div class="divide-y divide-border">
					{#each nomination.events as event (event.id)}
						<div data-event-id={event.id} class="scroll-mt-28">
							<EventCard {event} {currentEvent} {user} />
						</div>
					{/each}
				</div>
			</div>
		{/each}
	</section>
{/snippet}
