<script lang="ts">
	import { invalidate } from '$app/navigation';
	import { page } from '$app/state';
	import EventCard from '$lib/components/schedule/EventCard.svelte';
	import SectionHeader from '$lib/components/SectionHeader.svelte';
	import { getEventsClient } from '$lib/events.svelte';
	import type { ScheduleEventFullDTO } from '$lib/types/schedule';
	import type { CurrentUserDTO } from '$lib/types/user';
	import { Button, Search, Toggle } from 'flowbite-svelte';
	import { ChevronUpOutline, PlaySolid } from 'flowbite-svelte-icons';
	import { onMount } from 'svelte';

	type ScheduleNominationGroup = {
		title: string;
		eventCount: number;
		events: ScheduleEventFullDTO[];
	};

	type ScheduleBlockGroup = {
		title: string;
		eventCount: number;
		nominations: ScheduleNominationGroup[];
	};

	// Keep the schedule source close to the page data so it stays SSR-friendly.
	let { data } = $props();
	let schedule: ScheduleEventFullDTO[] = $derived(data.schedule);

	// Store filter state locally because it only affects this page view.
	let searchQuery: string = $state('');
	let showOnlySubscribed: boolean = $state(false);

	// We use the full schedule current event for countdown labels inside every row.
	let currentEvent = $derived(schedule.find((event) => event.is_current) ?? null);
	let user: CurrentUserDTO | null = $derived(page.data.user);

	let filtered: ScheduleEventFullDTO[] = $derived(
		schedule.filter((event) => {
			const query = searchQuery.trim().toLowerCase();
			const searchMatch =
				query.length === 0 ||
				event.public_number.toString().toLowerCase().includes(query) ||
				event.title.toLowerCase().includes(query) ||
				event.block_title?.toLowerCase().includes(query) ||
				event.nomination_title?.toLowerCase().includes(query);

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
			? `Всего событий: ${schedule.length}`
			: `Показано ${filtered.length} из ${schedule.length}`
	);

	let hasActiveFilters = $derived(showOnlySubscribed || searchQuery.trim().length > 0);

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

		element?.scrollIntoView({ behavior: 'smooth', block: 'center' });
	}

	function scrollToTop() {
		const scrollContainer = getScrollContainer();
		if (!scrollContainer) return;

		scrollContainer.scrollTo({ top: 0, behavior: 'smooth' });
	}

	onMount(() => {
		const scrollContainer = getScrollContainer();
		const eventsClient = getEventsClient();

		const updateScrollState = () => {
			showScrollTopButton = (scrollContainer?.scrollTop ?? 0) > 320;
		};

		const updateSchedule = async () => {
			await invalidate('app:schedule');
		};

		updateScrollState();
		scrollContainer?.addEventListener('scroll', updateScrollState, { passive: true });
		eventsClient?.on('update_schedule', updateSchedule);

		return () => {
			scrollContainer?.removeEventListener('scroll', updateScrollState);
			eventsClient?.off('update_schedule', updateSchedule);
		};
	});
</script>

<svelte:head>
	<title>Расписание</title>
</svelte:head>

<SectionHeader title="Расписание" description="Следите за ходом мероприятия" />

<div {@attach capturePageRoot} class="space-y-4">
	<!-- Keep filters compact and static so the schedule itself can use sticky headers. -->
	<div class="rounded-2xl border border-gray-200 bg-white p-3 shadow-sm dark:border-gray-700 dark:bg-gray-800">
		<div class="flex flex-col gap-3">
			<Search
				bind:value={searchQuery}
				placeholder="Поиск по номеру, выступлению, блоку или номинации"
				clearable
				size="sm"
				class="rounded-xl border-gray-300 dark:border-gray-600"
			/>

			<div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
				<Toggle bind:checked={showOnlySubscribed} size="small" color="primary" class="w-fit">
					<span class="text-sm font-medium text-gray-700 dark:text-gray-200">Только подписки</span>
				</Toggle>

				<p class="text-xs text-gray-500 dark:text-gray-400">
					{resultsSummary}
					{#if hasActiveFilters}
						<span class="ml-1">• фильтр включён</span>
					{/if}
				</p>
			</div>
		</div>
	</div>

	<div class="space-y-4">
		{#each groupedSchedule as block, blockIndex (`${block.title}-${blockIndex}`)}
			<section class="space-y-2">
				<!-- Keep the active block visible while the user scrolls through dense rows. -->
				<div class="sticky top-0 z-20">
					<div
						class="flex min-h-11 items-center justify-between rounded-xl border border-gray-200 bg-gray-50/95 px-3 py-2 shadow-sm backdrop-blur dark:border-gray-700 dark:bg-gray-900/95"
					>
						<h2 class="text-sm font-semibold text-gray-900 sm:text-base dark:text-white">
							{block.title}
						</h2>
						<span class="text-xs font-medium text-gray-500 dark:text-gray-400">
							{block.eventCount}
						</span>
					</div>
				</div>

				{#each block.nominations as nomination, nominationIndex (`${block.title}-${nomination.title}-${nominationIndex}`)}
					<!-- Clip the card edges without creating a new scroll container, so sticky headers keep working. -->
					<div
						class="relative overflow-clip rounded-xl border border-gray-200 bg-white shadow-sm dark:border-gray-700 dark:bg-gray-800/80"
					>
						<!-- Stick the nomination header below the block header for better context. -->
						<div
							class="sticky top-12 z-10 rounded-t-xl border-b border-gray-100 bg-white/95 px-3 py-2 backdrop-blur dark:border-gray-700 dark:bg-gray-800/95"
						>
							<div class="flex items-center justify-between gap-3">
								<h3
									class="text-xs font-semibold tracking-wide text-gray-700 uppercase sm:text-sm dark:text-gray-300"
								>
									{nomination.title}
								</h3>
								<span class="text-xs text-gray-500 dark:text-gray-400">
									{nomination.eventCount}
								</span>
							</div>
						</div>

						<div class="divide-y divide-gray-100 dark:divide-gray-700/80">
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
				class="rounded-xl border border-dashed border-gray-300 bg-white px-4 py-8 text-center text-sm text-gray-500 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-400 sm:py-10"
			>
				<p>События не найдены</p>
			</div>
		{/each}
	</div>

	{#if visibleCurrentEvent || showScrollTopButton}
		<!-- Lift FAB actions above the bottom mobile navigation so they stay tappable. -->
		<div class="pointer-events-none fixed right-4 bottom-24 z-30 md:bottom-6">
			<div class="flex flex-col items-end gap-2">
				{#if visibleCurrentEvent}
					<Button
						color="green"
						size="sm"
						pill
						class="pointer-events-auto h-12 w-12 rounded-full px-0 shadow-lg shadow-green-500/15 lg:w-32 lg:px-3"
						onclick={scrollToCurrentEvent}
						aria-label="Перейти к текущему событию"
					>
						<PlaySolid class="h-4 w-4 shrink-0" />
						<span class="sr-only lg:not-sr-only lg:ml-2">Текущее</span>
					</Button>
				{/if}

				{#if showScrollTopButton}
					<Button
						color="light"
						size="sm"
						pill
						class="pointer-events-auto h-12 w-12 rounded-full px-0 shadow-lg dark:border-gray-700 dark:bg-gray-800 dark:text-white lg:w-32 lg:px-3"
						onclick={scrollToTop}
						aria-label="Подняться наверх"
					>
						<ChevronUpOutline class="h-4 w-4 shrink-0" />
						<span class="sr-only lg:not-sr-only lg:ml-2">Наверх</span>
					</Button>
				{/if}
			</div>
		</div>
	{/if}
</div>
