<script lang="ts">
	import type { PageProps } from './$types';

	import GetReadySection from './components/home/GetReadySection.svelte';
	import HeroCard from './components/home/HeroCard.svelte';

	let { data }: PageProps = $props();
	let user = $derived(data.user);
	let config = $derived(data.config);
</script>

<svelte:head>
	<title>ФАН ФАН</title>
</svelte:head>

<div class="space-y-5 sm:space-y-6">
	<HeroCard festivalStart={config.festival_start} festivalEnded={config.festival_ended} />
	<GetReadySection {user} />
</div>
