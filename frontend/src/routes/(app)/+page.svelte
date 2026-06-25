<script lang="ts">
	import type { PageProps } from './$types';

	import GetReadySection from './components/home/GetReadySection.svelte';
	import HeroCard from './components/home/HeroCard.svelte';

	let { data }: PageProps = $props();
	let user = $derived(data.user);
</script>

<svelte:head>
	<title>ФАН ФАН</title>
</svelte:head>

<div class="space-y-5 sm:space-y-6">
	<HeroCard />
	<GetReadySection {user} />
</div>
