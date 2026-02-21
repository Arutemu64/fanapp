<script lang="ts">
	import { Card, Badge } from 'flowbite-svelte';
	import { CheckCircleSolid, ClockOutline, ChevronRightOutline } from 'flowbite-svelte-icons';
	import type { VotingNominationUserDTO } from '$lib/types/voting';

	interface Props {
		nomination: VotingNominationUserDTO;
	}

	let { nomination }: Props = $props();
</script>

<a href="/voting/{nomination.id}">
	<Card
		class="h-full py-3 ps-4 pe-3 transition-all hover:border-gray-400 hover:shadow-md dark:hover:border-gray-500"
	>
		<div class="flex items-start justify-between gap-2 sm:gap-3">
			<div class="min-w-0 flex-1">
				<h3 class="text-sm font-semibold text-gray-900 sm:text-base dark:text-white">
					{nomination.title}
				</h3>
			</div>

			{#if nomination.vote_id !== null}
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

		<div class="mt-2 flex items-center text-xs text-gray-500 sm:mt-3 sm:text-sm dark:text-gray-400">
			<span class="flex items-center gap-1">
				<ChevronRightOutline class="h-3.5 w-3.5" />
				Перейти к голосованию
			</span>
		</div>
	</Card>
</a>
