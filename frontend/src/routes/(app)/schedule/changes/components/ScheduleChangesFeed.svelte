<script lang="ts">
	import { Button, Spinner } from 'flowbite-svelte';
	import { createApiClient } from '$lib/api';
	import { getToastService } from '$lib/services/toasts.svelte';
	import {
		SCHEDULE_CHANGES_PAGE_REQUEST_LIMIT,
		SCHEDULE_CHANGES_PAGE_SIZE
	} from '$lib/constants/schedule_changes';
	import type { ScheduleChangeFullDTO } from '$lib/types/schedule';
	import ScheduleChangeCard from './ScheduleChangeCard.svelte';

	type ScheduleChange = ScheduleChangeFullDTO;

	interface Props {
		initialChanges: Array<ScheduleChange>;
		initialHasMore: boolean;
	}

	let { initialChanges, initialHasMore }: Props = $props();

	const client = createApiClient();
	const toastService = getToastService();

	// Server provides the first page; state holds only pages loaded afterwards.
	let extraChanges = $state.raw<Array<ScheduleChange>>([]);
	let extraHasMore = $state<boolean | null>(null);
	let extraOffset = $state(0);
	let isLoadingMore = $state(false);

	let changes = $derived(appendUniqueChanges(initialChanges, extraChanges));
	let hasMore = $derived(extraHasMore ?? initialHasMore);
	let nextOffset = $derived(initialChanges.length + extraOffset);

	function appendUniqueChanges(
		existingChanges: Array<ScheduleChange>,
		nextChanges: Array<ScheduleChange>
	) {
		// Guard against duplicates if the list shifted between requests.
		const existingIds = new Set(existingChanges.map((change) => change.id));

		return [...existingChanges, ...nextChanges.filter((change) => !existingIds.has(change.id))];
	}

	async function loadMoreChanges() {
		if (!hasMore || isLoadingMore) {
			return;
		}

		isLoadingMore = true;

		try {
			const { data: result, error } = await client.GET('/schedule/changes/', {
				params: {
					query: {
						limit: SCHEDULE_CHANGES_PAGE_REQUEST_LIMIT,
						offset: nextOffset
					}
				}
			});

			if (error || !result) {
				toastService.error('Не удалось загрузить изменения программы');
				return;
			}

			const nextChanges = result.schedule_changes.slice(0, SCHEDULE_CHANGES_PAGE_SIZE);

			extraChanges = appendUniqueChanges(extraChanges, nextChanges);
			extraHasMore = result.schedule_changes.length > SCHEDULE_CHANGES_PAGE_SIZE;
			extraOffset += nextChanges.length;
		} catch (error) {
			console.error('Failed to load more schedule changes', error);
			toastService.error('Не удалось загрузить изменения программы');
		} finally {
			isLoadingMore = false;
		}
	}
</script>

{#if changes.length === 0}
	<div
		class="rounded-lg border border-gray-200 bg-white p-6 text-center dark:border-gray-700 dark:bg-gray-800"
	>
		<p class="text-gray-500 dark:text-gray-400">Изменений пока нет</p>
	</div>
{:else}
	<div class="space-y-3">
		{#each changes as change (change.id)}
			<ScheduleChangeCard {change} />
		{/each}
	</div>

	{#if hasMore}
		<div class="mt-4 flex justify-center">
			<Button
				color="light"
				class="w-full sm:w-auto"
				onclick={loadMoreChanges}
				disabled={isLoadingMore}
			>
				{#if isLoadingMore}
					<Spinner size="4" class="me-2" />
				{/if}
				{isLoadingMore ? 'Загрузка…' : 'Показать ещё'}
			</Button>
		</div>
	{/if}
{/if}
