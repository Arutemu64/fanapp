<script lang="ts">
	import HeroCard from './components/home/HeroCard.svelte';
	import GetReadySection from './components/home/GetReadySection.svelte';

	let { data } = $props();
	let user = $derived(data.user);
</script>

<svelte:head>
	<title>ФАН ФАН — главная</title>
</svelte:head>

<div class="mx-auto max-w-6xl space-y-5 sm:space-y-6">
	<HeroCard />
	<GetReadySection {user} />
</div>
