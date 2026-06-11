<script lang="ts">
	import ScheduleChangeCard from './components/ScheduleChangeCard.svelte';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();
	let scheduleChanges = $derived(data.schedule_changes);
</script>

<svelte:head>
	<title>Изменения расписания</title>
</svelte:head>

{#if scheduleChanges.length === 0}
	<div
		class="rounded-lg border border-gray-200 bg-white p-6 text-center dark:border-gray-700 dark:bg-gray-800"
	>
		<p class="text-gray-500 dark:text-gray-400">Изменений пока нет</p>
	</div>
{:else}
	<div class="space-y-3">
		{#each scheduleChanges as change (change.id)}
			<ScheduleChangeCard {change} />
		{/each}
	</div>
{/if}
