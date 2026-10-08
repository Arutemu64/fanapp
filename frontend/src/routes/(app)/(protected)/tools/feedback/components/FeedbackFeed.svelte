<script lang="ts">
	import { MessageSquare } from '@lucide/svelte';

	import type { FeedbackDto } from '#lib/api/generated/index.js';

	import { listFeedback } from '#lib/api/generated/index.js';
	import { createApiClient } from '#lib/api/index.js';
	import EmptyState from '#lib/components/EmptyState.svelte';
	import LoadMoreButton from '#lib/components/LoadMoreButton.svelte';
	import MenuGroup from '#lib/components/MenuGroup.svelte';
	import { FEEDBACK_PAGE_REQUEST_LIMIT, FEEDBACK_PAGE_SIZE } from '#lib/constants/feedback.js';
	import { PaginatedFeed } from '#lib/services/feed.svelte.js';
	import { minuteClock } from '#lib/services/minuteClock.js';
	import { getToastService } from '#lib/services/toasts.svelte.js';
	import { groupByDay } from '#lib/utils/groupByDay.js';

	import FeedbackItem from './FeedbackItem.svelte';

	interface Props {
		initialFeedback: Array<FeedbackDto>;
		initialHasMore: boolean;
	}

	let { initialFeedback, initialHasMore }: Props = $props();

	const client = createApiClient();
	const toastService = getToastService();

	const feed = new PaginatedFeed<FeedbackDto>({
		pageSize: FEEDBACK_PAGE_SIZE,
		requestLimit: FEEDBACK_PAGE_REQUEST_LIMIT,
		getInitialItems: () => initialFeedback,
		getInitialHasMore: () => initialHasMore,
		fetchPage: async (limit, offset) => {
			const { data, error } = await listFeedback({
				client,
				query: { limit, offset }
			});
			return error || !data ? null : data.feedback;
		},
		onError: () => toastService.add('Не удалось загрузить отзывы', 'error')
	});

	// Day sections, the shape of the notifications feed.
	let dayGroups = $derived(groupByDay(feed.items, minuteClock.now));
</script>

{#if feed.items.length === 0}
	<EmptyState
		icon={MessageSquare}
		title="Отзывов пока нет"
		message="Здесь появится то, что участники напишут в&nbsp;форме обратной связи."
	/>
{:else}
	<div class="flex flex-col gap-6">
		{#each dayGroups as group (group.key)}
			<section aria-labelledby="feedback-day-{group.key}">
				<h2 id="feedback-day-{group.key}" class="mb-2 text-sm font-semibold text-muted-foreground">
					{group.heading}
				</h2>
				<!-- One divided list, not a card per item: the entries are all the same
				     shape, so a list scans faster and fits more on a phone screen. -->
				<MenuGroup>
					<ul class="divide-y divide-border">
						{#each group.items as item (item.id)}
							<li>
								<FeedbackItem feedback={item} />
							</li>
						{/each}
					</ul>
				</MenuGroup>
			</section>
		{/each}
	</div>

	{#if feed.hasMore}
		<LoadMoreButton loading={feed.isLoadingMore} onclick={feed.loadMore} />
	{/if}
{/if}
