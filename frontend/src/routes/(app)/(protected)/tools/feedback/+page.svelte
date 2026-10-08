<script lang="ts">
	import SectionIntro from '#lib/components/SectionIntro.svelte';
	import { feedSnapshotKey } from '#lib/utils/feed.js';

	import type { PageProps } from './$types';

	import FeedbackFeed from './components/FeedbackFeed.svelte';

	let { data }: PageProps = $props();

	// Re-seed the feed with the fresh first page whenever route data changes.
	let feedbackKey = $derived(
		feedSnapshotKey(
			data.hasMore,
			data.feedback.map((item) => item.id)
		)
	);
</script>

<svelte:head>
	<title>Отзывы · ФАН ФАН</title>
</svelte:head>

<div class="mx-auto w-full max-w-2xl">
	<SectionIntro description="Отзывы участников о приложении. Свежие — сверху." />

	{#key feedbackKey}
		<FeedbackFeed initialFeedback={data.feedback} initialHasMore={data.hasMore} />
	{/key}
</div>
