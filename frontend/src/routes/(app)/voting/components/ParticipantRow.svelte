<script lang="ts">
	import { CheckCircle2, ThumbsUp } from '@lucide/svelte';

	import type { ParticipantFullDto } from '#lib/api/generated/index.js';

	import { addVote } from '#lib/api/generated/index.js';
	import { createApiClient } from '#lib/api/index.js';
	import NumberBadge from '#lib/components/NumberBadge.svelte';
	import { Badge } from '#lib/components/ui/badge/index.js';
	import { Button } from '#lib/components/ui/button/index.js';
	import { Spinner } from '#lib/components/ui/spinner/index.js';
	import { getToastService } from '#lib/services/toasts.svelte.js';
	import { pluralize } from '#lib/utils/formatters.js';

	const client = createApiClient();

	interface Props {
		participant: ParticipantFullDto;
		hasVoted: boolean;
		canVote: boolean;
		onVoted?: () => void;
	}

	let { participant, hasVoted, canVote, onVoted }: Props = $props();
	const toastService = getToastService();

	let isLoading = $state(false);
	let areActionsDisabled = $derived(isLoading || !canVote);
	let isVotedFor = $derived(participant.user_vote !== null);

	let optimisticDelta = $state(0);
	let votesCount = $derived(participant.votes_count + optimisticDelta);

	async function handleVote() {
		if (areActionsDisabled || isVotedFor) return;

		isLoading = true;
		optimisticDelta += 1;
		try {
			const { data, error, response } = await addVote({
				client,
				body: {
					participant_id: participant.id
				}
			});

			if (error || !response?.ok) {
				optimisticDelta -= 1;
				toastService.error(error);
				return;
			}

			if (data) {
				toastService.add('Голос учтён', 'success');
				optimisticDelta = 0;
				onVoted?.();
			}
		} finally {
			isLoading = false;
		}
	}
</script>

<!-- A row, not a card: participants are same-shaped text entries, which scan
     faster as one divided list than as a stack of boxes (DESIGN.md §5). Shaped like
     the schedule's EventCard so the two lists read as one app. Only the button
     casts a vote — a whole-row tap target would turn a scroll-stop into a ballot.
     Cancelling lives in UserVoteNotice, above the search, so a filter can never
     hide the only way to take a vote back. -->
<li class={['flex items-start gap-3 px-3 py-4 sm:px-4', isVotedFor && 'bg-success/10']}>
	{#if participant.voting_number}
		<NumberBadge number={participant.voting_number} highlighted={isVotedFor} />
	{:else}
		<!-- Keeps the title in the column every other row shares. -->
		<div class="w-12 shrink-0" aria-hidden="true"></div>
	{/if}

	<div class="min-w-0 flex-1">
		<h3 class="text-base leading-snug font-semibold break-words text-foreground">
			{participant.title}
		</h3>

		{#if isVotedFor}
			<div class="mt-1.5">
				<Badge
					variant="outline"
					class="inline-flex items-center gap-1 border-success/30 bg-success/10 px-2 py-0.5 text-xs font-medium text-success"
				>
					<CheckCircle2 class="size-3.5" />
					Твой голос
				</Badge>
			</div>
		{/if}

		<p
			class="mt-1.5 inline-flex items-start gap-1 text-xs font-medium text-muted-foreground"
			aria-live="polite"
		>
			<ThumbsUp class="mt-px size-3.5 shrink-0" aria-hidden="true" />
			{votesCount}
			{pluralize(votesCount, 'голос', 'голоса', 'голосов')}
		</p>
	</div>

	<!-- A labelled button, not an icon: no icon reads as "vote" without its label
	     (NN/g, Icon Usability). Tonal rather than filled, because a solid button on
	     every row would bury the page's real primary action. -->
	{#if !hasVoted}
		<Button
			variant="tonal"
			class="shrink-0"
			disabled={areActionsDisabled}
			onclick={handleVote}
			aria-label={`Голосовать за ${participant.title}`}
		>
			{#if isLoading}
				<Spinner data-icon="inline-start" />
			{/if}
			Голосовать
		</Button>
	{/if}
</li>
