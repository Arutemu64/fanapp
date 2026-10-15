<script lang="ts">
	import SectionIntro from '#lib/components/SectionIntro.svelte';
	import { m } from '#lib/paraglide/messages.js';

	import FeedbackFeed from './components/FeedbackFeed.svelte';
</script>

<svelte:head>
	<title>{m.document_title({ title: m.tool_feedback() })}</title>
</svelte:head>

<div class="mx-auto w-full max-w-2xl">
	<SectionIntro description={m.tool_feedback_page_description()} />

	<FeedbackFeed />
</div>
