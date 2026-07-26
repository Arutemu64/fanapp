<script lang="ts">
	import type { ScheduleEventWithSubscription } from '$lib/types/schedule';
	import type { CurrentUserDTO } from '$lib/types/user';

	import { invalidate } from '$app/navigation';
	import { page } from '$app/state';
	import StaleDataNotice from '$lib/components/StaleDataNotice.svelte';
	import { getEventsClient } from '$lib/services/events.svelte';
	import { getOfflineService, shouldShowStaleNotice } from '$lib/services/offline.svelte';
	import { buildSearchHaystack, matchesTokens, tokenizeQuery } from '$lib/utils/search';
	import { Button, Search, Toggle } from 'flowbite-svelte';
	import {
		ChevronUpOutline,
		CloseOutline,
		InfoCircleOutline,
		PlaySolid
	} from 'flowbite-svelte-icons';
	import { onMount } from 'svelte';

	import type { PageProps } from './$types';

	import EventCard from './components/EventCard.svelte';

	type ScheduleNominationGroup = {
		title: string;
		eventCount: number;
		events: ScheduleEventWithSubscription[];
	};

	type ScheduleBlockGroup = {
		title: string;
		eventCount: number;
		nominations: ScheduleNominationGroup[];
	};

	// Mirror the loaded page data so the component reads schedule from one local source.
	let { data }: PageProps = $props();
	let schedule: ScheduleEventWithSubscription[] = $derived(data.schedule);

	// Store filter state locally because it only affects this page view.
	let searchQuery: string = $state('');
	let showOnlySubscribed: boolean = $state(false);

	// We use the full schedule current event for countdown labels inside every row.
	let currentEvent = $derived(schedule.find((event) => event.is_current) ?? null);
	let user: CurrentUserDTO | null = $derived(page.data.user);

	const offline = getOfflineService();
	let showStaleNotice = $derived(
		shouldShowStaleNotice({
			offlineMiss: data.offlineMiss,
			stale: data.stale,
			isOnline: offline.isOnline
		})
	);

	// Normalized search text per event, rebuilt only when the schedule itself
	// changes. Keeps a keystroke down to a substring scan instead of re-running
	// NFD normalization over every event's four fields.
	let searchHaystacks: Map<string, string> = $derived(
		new Map(
			schedule.map((event) => [
				event.id,
				buildSearchHaystack([event.number, event.title, event.block_title, event.nomination_title])
			])
		)
	);

	let searchTokens: string[] = $derived(tokenizeQuery(searchQuery));

	let filtered: ScheduleEventWithSubscription[] = $derived(
		schedule.filter((event) => {
			const searchMatch = matchesTokens(searchTokens, searchHaystacks.get(event.id) ?? '');

			const subscriptionMatch = !showOnlySubscribed || event.user_subscription !== null;

			return searchMatch && subscriptionMatch;
		})
	);

	// Hide the FAB for the current event when the active filters remove that row from the page.
	let visibleCurrentEvent = $derived(filtered.find((event) => event.is_current) ?? null);

	// Group rows into block and nomination sections so we can make headers sticky.
	let groupedSchedule: ScheduleBlockGroup[] = $derived.by(() => {
		const groups: ScheduleBlockGroup[] = [];

		for (const event of filtered) {
			const blockTitle = event.block_title?.trim() || 'Без блока';
			const nominationTitle = event.nomination_title?.trim() || 'Без номинации';

			let blockGroup = groups.at(-1);
			if (!blockGroup || blockGroup.title !== blockTitle) {
				blockGroup = {
					title: blockTitle,
					eventCount: 0,
					nominations: []
				};
				groups.push(blockGroup);
			}

			blockGroup.eventCount += 1;

			let nominationGroup = blockGroup.nominations.at(-1);
			if (!nominationGroup || nominationGroup.title !== nominationTitle) {
				nominationGroup = {
					title: nominationTitle,
					eventCount: 0,
					events: []
				};
				blockGroup.nominations.push(nominationGroup);
			}

			nominationGroup.eventCount += 1;
			nominationGroup.events.push(event);
		}

		return groups;
	});

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
		const container = pageRoot?.closest('section');

		return container instanceof HTMLElement ? container : null;
	}

	function scrollToCurrentEvent() {
		if (!visibleCurrentEvent || !pageRoot) return;

		const element = pageRoot.querySelector<HTMLElement>(
			`[data-event-id="${visibleCurrentEvent.id}"]`
		);

		element?.scrollIntoView({
			behavior: 'smooth',
			block: 'center'
		});
	}

	function scrollToTop() {
		const scrollContainer = getScrollContainer();
		if (!scrollContainer) return;

		scrollContainer.scrollTo({
			top: 0,
			behavior: 'smooth'
		});
	}

	onMount(() => {
		const scrollContainer = getScrollContainer();
		const eventsClient = getEventsClient();

		const updateScrollState = () => {
			showScrollTopButton = (scrollContainer?.scrollTop ?? 0) > 320;
		};

		// Refetch on a schedule update and on every (re)connect, so a 'schedule_updated'
		// missed while the SSE stream was down doesn't leave a stale schedule. Firing on
		// first connect just refetches the freshly loaded data once — harmless and idempotent.
		const reloadSchedule = () => {
			void invalidate('app:schedule');
		};

		updateScrollState();
		scrollContainer?.addEventListener('scroll', updateScrollState, { passive: true });
		eventsClient?.on('schedule_updated', reloadSchedule);
		eventsClient?.on('connection_established', reloadSchedule);

		return () => {
			scrollContainer?.removeEventListener('scroll', updateScrollState);
			eventsClient?.off('schedule_updated', reloadSchedule);
			eventsClient?.off('connection_established', reloadSchedule);
		};
	});
</script>

<svelte:head>
	<title>Программа · ФАН ФАН</title>
</svelte:head>

<div {@attach capturePageRoot} class="space-y-4">
	{#if showStaleNotice}
		<StaleDataNotice
			message="Нет связи. Показана сохранённая программа — обновится при подключении."
			cachedAt={data.cachedAt}
		/>
	{/if}

	<!-- Keep filters compact and static so the schedule itself can use sticky headers. -->
	<div
		class="rounded-2xl border border-gray-200 bg-white p-3 dark:border-gray-700 dark:bg-gray-800"
	>
		<div class="flex flex-col gap-3">
			<Search
				bind:value={searchQuery}
				clearableOnClick={() => {
					searchQuery = '';
				}}
				name="schedule_search"
				aria-label="Поиск по программе"
				placeholder="Поиск по номеру или названию…"
				autocomplete="off"
				spellcheck={false}
				clearable
				size="sm"
				class="rounded-xl border-gray-300 dark:border-gray-600"
			/>

			<div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
				<Toggle bind:checked={showOnlySubscribed} size="small" color="primary" class="w-fit">
					<span class="text-sm font-medium text-gray-700 dark:text-gray-200">Только подписки</span>
				</Toggle>

				<!-- Announce filter result changes to screen readers, which otherwise get no
				     feedback that the list shrank/grew. -->
				<p class="text-xs text-gray-500 dark:text-gray-400" aria-live="polite" role="status">
					{resultsSummary}
				</p>
			</div>
		</div>
	</div>

	<!-- Estimate disclaimer: the "≈ HH:MM" times are drift-projected, not
	     guaranteed. Kept as a quiet inline note (no border/panel) so it reads as
	     guidance rather than a promo banner the eye skips. Shown only while an
	     event is live, since that's the only time projected start times appear. -->
	{#if currentEvent}
		<p class="flex items-start gap-1.5 px-1 text-xs text-gray-500 dark:text-gray-400">
			<InfoCircleOutline class="mt-px h-3.5 w-3.5 shrink-0" />
			<span>Время начала примерное — программа может сдвигаться.</span>
		</p>
	{/if}

	<div class="space-y-4">
		{#each groupedSchedule as block, blockIndex (`${block.title}-${blockIndex}`)}
			<section class="space-y-2">
				<!-- Keep the active block visible while the user scrolls through dense rows. -->
				<!-- Inter (not display): block headers are repeated structural data, and DESIGN reserves Unbounded for rare identity moments. Size/weight + filled count chip carry the hierarchy; no accent stripe. -->
				<div class="sticky top-0 z-20">
					<div
						class="flex min-h-11 items-center justify-between gap-3 overflow-hidden rounded-xl border border-gray-200 bg-white/95 px-3 py-2 shadow-sm backdrop-blur dark:border-gray-700 dark:bg-gray-900/95"
					>
						<h2
							class="truncate text-sm font-semibold tracking-tight text-gray-900 sm:text-base dark:text-white"
						>
							{block.title}
						</h2>
						<span
							class="shrink-0 rounded-full bg-primary-50 px-2 py-0.5 text-xs font-bold text-primary-600 tabular-nums dark:bg-primary-900/30 dark:text-primary-300"
						>
							{block.eventCount}
						</span>
					</div>
				</div>

				{#each block.nominations as nomination, nominationIndex (`${block.title}-${nomination.title}-${nominationIndex}`)}
					<!-- Clip the card edges without creating a new scroll container, so sticky headers keep working. -->
					<div
						class="relative overflow-clip rounded-xl border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800/80"
					>
						<!-- Stick the nomination header below the block header for better context. -->
						<div
							class="sticky top-12 z-10 rounded-t-xl border-b border-gray-100 bg-white/95 px-3 py-2 backdrop-blur dark:border-gray-700 dark:bg-gray-800/95"
						>
							<div class="flex items-center justify-between gap-3">
								<h3 class="min-w-0 truncate text-sm font-semibold text-gray-700 dark:text-gray-300">
									{nomination.title}
								</h3>
								<span class="shrink-0 text-xs text-gray-500 tabular-nums dark:text-gray-400">
									{nomination.eventCount}
								</span>
							</div>
						</div>

						<!-- Row divider sits one step stronger than the in-card staff-strip
						     border (gray-100 / gray-800), so event boundaries read as the
						     primary split and the strip separator stays subordinate. -->
						<div class="divide-y divide-gray-200 dark:divide-gray-700">
							{#each nomination.events as event (event.id)}
								<div data-event-id={event.id} class="scroll-mt-28">
									<EventCard {event} {schedule} {currentEvent} {user} />
								</div>
							{/each}
						</div>
					</div>
				{/each}
			</section>
		{:else}
			<div
				class="rounded-2xl border border-dashed border-gray-300 bg-white px-4 py-10 text-center sm:py-14 dark:border-gray-700 dark:bg-gray-800"
			>
				<p class="text-base font-bold text-gray-900 dark:text-white">
					{#if data.offlineMiss}
						Программа недоступна офлайн
					{:else if hasActiveFilters}
						Ничего не нашлось
					{:else}
						Программа пока пуста
					{/if}
				</p>
				<p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
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
					<Button color="light" size="sm" class="mt-4" onclick={resetFilters}>
						<CloseOutline class="me-1.5 h-4 w-4" />
						Сбросить фильтры
					</Button>
				{/if}
			</div>
		{/each}
	</div>

	{#if visibleCurrentEvent || showScrollTopButton}
		<!-- Lift FAB actions above the bottom mobile navigation so they stay tappable. -->
		<div class="pointer-events-none fixed right-4 bottom-24 z-30 md:bottom-6">
			<div class="flex flex-col items-end gap-2">
				{#if showScrollTopButton}
					<Button
						color="light"
						size="sm"
						pill
						class="pointer-events-auto h-12 w-12 rounded-full px-0 shadow-lg lg:w-32 lg:px-3 dark:border-gray-700 dark:bg-gray-800 dark:text-white"
						onclick={scrollToTop}
						aria-label="Подняться наверх"
					>
						<ChevronUpOutline class="h-4 w-4 shrink-0" />
						<span class="sr-only lg:not-sr-only lg:ml-2">Наверх</span>
					</Button>
				{/if}

				{#if visibleCurrentEvent}
					<Button
						color="green"
						size="sm"
						pill
						class="pointer-events-auto h-12 w-12 rounded-full px-0 shadow-lg shadow-green-500/15 lg:w-32 lg:px-3"
						onclick={scrollToCurrentEvent}
						aria-label="Перейти к текущему выступлению"
					>
						<PlaySolid class="h-4 w-4 shrink-0" />
						<span class="sr-only lg:not-sr-only lg:ml-2">Текущее</span>
					</Button>
				{/if}
			</div>
		</div>
	{/if}
</div>
