<script lang="ts">
	import type { NominationFullDTO } from '$lib/types/nominations';
	import { Card, Badge, Button } from 'flowbite-svelte';
	import { CheckCircleSolid, ClockOutline } from 'flowbite-svelte-icons';

	interface Props {
		nomination: NominationFullDTO;
	}

	let { nomination }: Props = $props();
</script>

<Card class="flex flex-col p-4 sm:p-5">
	<div class="flex items-start justify-between gap-2">
		<h3 class="text-lg font-bold text-gray-900 dark:text-white">
			{nomination.title}
		</h3>
		{#if nomination.vote}
			<Badge color="green" class="shrink-0">
				<span class="flex items-center gap-1">
					<CheckCircleSolid class="h-3.5 w-3.5" />
					<span class="hidden sm:inline">Проголосовано</span>
				</span>
			</Badge>
		{:else}
			<Badge color="gray" class="shrink-0">
				<span class="flex items-center gap-1">
					<ClockOutline class="h-3.5 w-3.5" />
					<span class="hidden sm:inline">Ожидает</span>
				</span>
			</Badge>
		{/if}
	</div>

	<div class="mt-auto pt-3 sm:pt-4">
		<Button color="primary" href="/voting/{nomination.code}" size="md">Проголосовать</Button>
	</div>
</Card>
