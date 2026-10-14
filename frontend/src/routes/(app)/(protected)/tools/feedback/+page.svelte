<script lang="ts">
	import SectionIntro from '#lib/components/SectionIntro.svelte';
	import { m } from '#lib/paraglide/messages.js';

	import FeedbackFeed from './components/FeedbackFeed.svelte';
</script>

<svelte:head>
	<title>{m.tool_feedback_title()} · {m.brand_name()}</title>
</svelte:head>

<div class="mx-auto w-full max-w-2xl">
	<SectionIntro description={m.feedback_admin_intro()} />

	<FeedbackFeed />
</div>
