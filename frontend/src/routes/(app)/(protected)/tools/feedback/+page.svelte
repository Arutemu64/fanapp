<script lang="ts">
	import BackLink from '$lib/components/BackLink.svelte';
	import SectionIntro from '$lib/components/SectionIntro.svelte';

	import FeedbackFeed from './components/FeedbackFeed.svelte';
</script>

<svelte:head>
	<title>Отзывы · ФАН ФАН</title>
</svelte:head>

<BackLink href="/tools" label="Назад к инструментам" />

<SectionIntro description="Отзывы участников о приложении. Свежие — сверху." />

<FeedbackFeed />
