<script lang="ts">
	import SectionIntro from '#lib/components/SectionIntro.svelte';

	import FeedbackFeed from './components/FeedbackFeed.svelte';
</script>

<svelte:head>
	<title>Отзывы · ФАН ФАН</title>
</svelte:head>

<div class="mx-auto w-full max-w-2xl">
	<SectionIntro description="Отзывы участников о приложении. Свежие — сверху." />

	<FeedbackFeed />
</div>
