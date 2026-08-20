<script lang="ts">
	import BackLink from '$lib/components/BackLink.svelte';
	import SectionIntro from '$lib/components/SectionIntro.svelte';
	import { feedSnapshotKey } from '$lib/utils/feed';

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

<BackLink href="/tools" label="Назад к инструментам" />

<SectionIntro description="Отзывы участников о приложении. Свежие — сверху." />

{#key feedbackKey}
	<FeedbackFeed initialFeedback={data.feedback} initialHasMore={data.hasMore} />
{/key}
