<script lang="ts">
	import type { NominationVotingDTO } from '$lib/types/nominations';
	import { Card, Badge, Button } from 'flowbite-svelte';
	import { CheckCircleSolid, ClockOutline } from 'flowbite-svelte-icons';

	interface Props {
		nomination: NominationVotingDTO;
	}

	let { nomination }: Props = $props();
</script>

<Card class="flex flex-col p-4 sm:p-5">
	<div class="flex items-start justify-between gap-2">
		<h3 class="text-lg font-bold text-gray-900 dark:text-white">
			{nomination.title}
		</h3>
		{#if nomination.user_vote}
			<Badge color="green" class="shrink-0 text-sm">
				<span class="flex items-center gap-1">
					<CheckCircleSolid class="h-4 w-4" />
					<span class="hidden sm:inline">Проголосовано</span>
				</span>
			</Badge>
		{:else}
			<Badge color="gray" class="shrink-0 text-sm">
				<span class="flex items-center gap-1">
					<ClockOutline class="h-4 w-4" />
					<span class="hidden sm:inline">Ожидает</span>
				</span>
			</Badge>
		{/if}
	</div>

	<div class="mt-auto pt-3 sm:pt-4">
		<Button color="primary" href="/voting/{nomination.code}" size="md">
			{nomination.user_vote ? 'Перейти' : 'Проголосовать'}
		</Button>
	</div>
</Card>
