<script lang="ts">
	import { invalidate, invalidateAll } from '$app/navigation';
	import { page } from '$app/state';
	import EventCard from '$lib/components/schedule/EventCard.svelte';
	import SectionHeader from '$lib/components/SectionHeader.svelte';
	import { getEventsClient } from '$lib/events.svelte';
	import type { ScheduleEventFullDTO } from '$lib/types/schedule';
	import type { UserFullDTO } from '$lib/types/user';
	import { Button, Search, Toggle } from 'flowbite-svelte';
	import { PlaySolid } from 'flowbite-svelte-icons';

	// Schedule
	let { data } = $props();
	let schedule: ScheduleEventFullDTO[] = $derived(data.schedule);

	// Filtering
	let searchQuery: string = $state('');
	let showOnlySubscribed: boolean = $state(false);
	let filtered: ScheduleEventFullDTO[] = $derived(
		schedule.filter((ev) => {
			const q = searchQuery.toLowerCase();
			const searchMatch =
				ev.public_number.toString().toLowerCase().includes(q) ||
				ev.title.toLowerCase().includes(q) ||
				ev.block_title?.toLowerCase().includes(q) ||
				ev.nomination_title?.toLowerCase().includes(q);
			const subscriptionMatch = !showOnlySubscribed || ev.user_subscription !== null;
			return searchMatch && subscriptionMatch;
		})
	);

	let currentEvent = $derived(schedule.find((ev) => ev.is_current));
	let user: UserFullDTO | null = $derived(page.data.user);

	// Scroll to current event
	// TODO scroll-margin-top
	function scrollToCurrentEvent() {
		if (!currentEvent) return;
		const element = document.querySelector(`[data-event-id="${currentEvent.id}"]`);
		if (element) {
			element.scrollIntoView({ behavior: 'smooth', block: 'center' });
		}
	}

	$effect(() => {
		const client = getEventsClient();
		if (!client) return;

		const updateSchedule = async () => {
			await invalidate('app:schedule');
		};
		client.source?.addEventListener('update_schedule', updateSchedule);
		return () => {
			client.source?.removeEventListener('update_schedule', updateSchedule);
		};
	});
</script>

<svelte:head>
	<title>Расписание</title>
</svelte:head>

<SectionHeader title="Расписание" description="Следите за ходом мероприятия" />

<!-- Floating Control Center -->
<div class="sticky top-4 z-30 mx-auto mb-6 max-w-2xl px-2 sm:px-0">
	<div
		class="rounded-2xl border border-gray-200/50 bg-white/80 p-3 shadow-lg backdrop-blur-lg transition-all duration-300 hover:shadow-xl dark:border-gray-700/50 dark:bg-gray-800/80"
	>
		<div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
			<div class="flex-1">
				<Search
					bind:value={searchQuery}
					placeholder="Поиск по выступлениям, номинациям, блокам..."
					clearable
					size="sm"
					class="rounded-xl border-gray-300/50 transition-colors focus:border-primary-500 dark:border-gray-600/50"
				/>
			</div>

			<div class="flex items-center gap-3">
				{#if currentEvent}
					<Button
						color="green"
						size="sm"
						class="rounded-xl font-medium shadow-sm transition-all hover:-translate-y-0.5 hover:shadow-md"
						onclick={scrollToCurrentEvent}
					>
						<PlaySolid class="mr-1 h-3.5 w-3.5" />
						Текущее
					</Button>
				{/if}
				<Toggle
					bind:checked={showOnlySubscribed}
					size="small"
					color="primary"
					class="rounded-xl p-1"
				>
					<span class="text-sm font-medium whitespace-nowrap text-gray-700 dark:text-gray-200"
						>Только подписки</span
					>
				</Toggle>
			</div>
		</div>
	</div>
</div>

<div class="space-y-4">
	{#each filtered as event, i (event.id)}
		{#if i === 0 || filtered[i]?.block_title !== filtered[i - 1]?.block_title}
			<h2
				class="mt-4 mb-1.5 border-b-2 border-gray-200 pb-1.5 text-base font-bold text-gray-900 first:mt-2 sm:mt-6 sm:mb-2 sm:pb-2 sm:text-lg dark:border-gray-700 dark:text-white"
			>
				{event.block_title ?? 'Без блока'}
			</h2>
		{/if}

		{#if i === 0 || filtered[i]?.nomination_title !== filtered[i - 1]?.nomination_title}
			<h3
				class="mb-1.5 ml-1 text-sm font-semibold text-gray-700 sm:mb-2 sm:ml-2 sm:text-base dark:text-gray-300"
			>
				{event.nomination_title ?? 'Без номинации'}
			</h3>
		{/if}

		<div data-event-id={event.id} class="scroll-mt-32 sm:scroll-mt-40">
			<EventCard {event} {schedule} {user} />
		</div>
	{:else}
		<div class="py-8 text-center text-sm text-gray-500 dark:text-gray-400 sm:py-12">
			<p>События не найдены</p>
		</div>
	{/each}
</div>
