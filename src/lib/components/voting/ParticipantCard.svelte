<script lang="ts">
	import { Card, Badge } from 'flowbite-svelte';
	import { CheckCircleSolid, HeartSolid, ThumbsUpOutline } from 'flowbite-svelte-icons';
	import type { VotingParticipantUserDTO } from '$lib/types/voting';
	import { pluralize } from '$lib/utils';

	interface Props {
		participant: VotingParticipantUserDTO;
		onVote: (participantId: number) => void;
	}

	let { participant, onVote }: Props = $props();

	function handleClick() {
		if (participant.vote_id === null) {
			onVote(participant.id);
		}
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter' && participant.vote_id === null) {
			onVote(participant.id);
		}
	}
</script>

<Card
	class="cursor-pointer py-3 ps-4 pe-3 transition-all {participant.vote_id !== null
		? 'ring-2 ring-green-400 dark:ring-green-500'
		: 'hover:border-gray-400 hover:shadow-md dark:hover:border-gray-500'}"
	role="button"
	tabindex={0}
	onclick={handleClick}
	onkeydown={handleKeydown}
>
	<div class="flex items-start justify-between gap-2 sm:gap-3">
		<div class="min-w-0 flex-1">
			{#if participant.voting_number}
				<div class="mb-0.5 text-xs font-medium text-gray-500 sm:mb-1 sm:text-sm dark:text-gray-400">
					№{participant.voting_number}
				</div>
			{/if}

			<h3 class="text-sm font-semibold text-gray-900 sm:text-base dark:text-white">
				{participant.title}
			</h3>
		</div>

		{#if participant.vote_id !== null}
			<Badge color="green" class="shrink-0">
				<span class="flex items-center gap-1">
					<CheckCircleSolid class="h-3.5 w-3.5" />
					<span class="hidden sm:inline">Ваш голос</span>
				</span>
			</Badge>
		{/if}
	</div>

	<div class="mt-2 flex items-center justify-between sm:mt-3">
		<div class="flex items-center gap-1 text-xs text-gray-500 sm:text-sm dark:text-gray-400">
			<HeartSolid class="h-3.5 w-3.5 text-red-500" />
			<span>
				{participant.votes_count}
				{pluralize(participant.votes_count, 'голос', 'голоса', 'голосов')}
			</span>
		</div>

		{#if participant.vote_id === null}
			<span class="flex items-center gap-1 text-xs text-gray-600 sm:text-sm dark:text-gray-300">
				<ThumbsUpOutline class="h-3.5 w-3.5" />
				<span class="hidden sm:inline">Проголосовать</span>
			</span>
		{/if}
	</div>
</Card>
