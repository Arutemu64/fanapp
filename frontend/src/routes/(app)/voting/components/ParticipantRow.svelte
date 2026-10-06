<script lang="ts">
	import type { ParticipantFullDto } from '$lib/api/generated';

	import { createApiClient } from '$lib/api';
	import { addVote } from '$lib/api/generated';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import { Spinner } from '$lib/components/ui/spinner';
	import { getToastService } from '$lib/services/toasts.svelte';
	import { pluralize } from '$lib/utils/formatters';
	import { Check, CheckCircle2 } from '@lucide/svelte';

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

<!-- A row, not a card: participants are same-shaped text entries (number + title),
     which scan faster as one divided list than as a stack of boxes (DESIGN.md §5).
     Only the button casts a vote — a whole-row tap target would turn a scroll-stop
     into a ballot. Cancelling lives in UserVoteNotice, above the search, so a
     filter can never hide the only way to take a vote back. -->
<li class={['flex items-center gap-3 p-3 sm:p-4', isVotedFor && 'bg-success/10']}>
	<span class="w-11 shrink-0 text-sm font-semibold text-muted-foreground tabular-nums">
		{#if participant.voting_number}
			№{participant.voting_number}
		{/if}
	</span>

	<div class="min-w-0 flex-1">
		<h3 class="text-base leading-snug font-semibold break-words text-foreground">
			{participant.title}
		</h3>
		<p class="mt-0.5 text-xs text-muted-foreground" aria-live="polite">
			{votesCount}
			{pluralize(votesCount, 'голос', 'голоса', 'голосов')}
		</p>
	</div>

	<!-- min-h reserves the 44px action slot so a row keeps its height whether it
	     shows the button, the badge, or nothing (after a vote elsewhere in the
	     nomination) — otherwise the whole list shifts when a vote lands. -->
	<div class="flex min-h-11 shrink-0 items-center">
		{#if isVotedFor}
			<Badge variant="outline" class="border-success/30 bg-success/10 text-success">
				<span class="flex items-center gap-1">
					<CheckCircle2 class="size-3.5" />
					Твой голос
				</span>
			</Badge>
		{:else if !hasVoted}
			<Button
				size="sm"
				class="min-h-11"
				disabled={areActionsDisabled}
				onclick={handleVote}
				aria-label={`Голосовать за ${participant.title}`}
			>
				{#if isLoading}
					<Spinner data-icon="inline-start" />
				{:else}
					<Check data-icon="inline-start" />
				{/if}
				Голосовать
			</Button>
		{/if}
	</div>
</li>
