<script lang="ts">
	import CircleCheck from '@lucide/svelte/icons/circle-check';
	import ThumbsUp from '@lucide/svelte/icons/thumbs-up';
	import { createMutation, useIsMutating } from '@tanstack/svelte-query';

	import type { ParticipantFullDto } from '#lib/api/generated/index.js';

	import { addVoteMutation } from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import NumberBadge from '#lib/components/NumberBadge.svelte';
	import { Badge } from '#lib/components/ui/badge/index.js';
	import { Button } from '#lib/components/ui/button/index.js';
	import { Spinner } from '#lib/components/ui/spinner/index.js';
	import { m } from '#lib/paraglide/messages.js';
	import { getToastService } from '#lib/services/toasts.svelte.js';

	interface Props {
		participant: ParticipantFullDto;
		hasVoted: boolean;
		canVote: boolean;
		onVoted?: () => Promise<void> | void;
	}

	let { participant, hasVoted, canVote, onVoted }: Props = $props();
	const toastService = getToastService();

	const VOTE_MUTATION_KEY = ['addVote'];

	const voteMutation = createMutation(() => ({
		...addVoteMutation(),
		mutationKey: VOTE_MUTATION_KEY,
		onSuccess: async () => {
			await onVoted?.();
		}
	}));

	const votesInFlight = useIsMutating({ mutationKey: VOTE_MUTATION_KEY });

	let areActionsDisabled = $derived(votesInFlight.current > 0 || !canVote);
	let isVotedFor = $derived(participant.user_vote !== null);

	let isVoteUnconfirmed = $derived(voteMutation.isPending && !isVotedFor);
	let votesCount = $derived(participant.votes_count + (isVoteUnconfirmed ? 1 : 0));

	function handleVote() {
		if (areActionsDisabled || isVotedFor) return;

		voteMutation.mutate(
			{ body: { participant_id: participant.id } },
			{
				onSuccess: () => toastService.add(m.voting_vote_counted(), 'success'),
				onError: (error) => toastService.error(error)
			}
		);
	}
</script>

<li class={['flex items-start gap-3 px-3 py-4 sm:px-4', isVotedFor && 'bg-success/10']}>
	{#if participant.voting_number}
		<NumberBadge number={participant.voting_number} highlighted={isVotedFor} />
	{:else}
		<div class="w-12 shrink-0" aria-hidden="true"></div>
	{/if}

	<div class="min-w-0 flex-1">
		<h3 class="text-base leading-snug font-semibold wrap-break-word text-foreground">
			{participant.title}
		</h3>

		{#if isVotedFor}
			<div class="mt-1.5">
				<Badge
					variant="outline"
					class="inline-flex items-center gap-1 border-success/30 bg-success/10 px-2 py-0.5 text-xs font-medium text-success"
				>
					<CircleCheck class="size-3.5" />
					{m.voting_your_vote()}
				</Badge>
			</div>
		{/if}

		<p
			class="mt-1.5 inline-flex items-start gap-1 text-xs font-medium text-muted-foreground"
			aria-live="polite"
		>
			<ThumbsUp class="mt-px size-3.5 shrink-0" aria-hidden="true" />
			{m.votes_count({ count: votesCount })}
		</p>
	</div>

	{#if !hasVoted}
		<Button
			variant="tonal"
			class="shrink-0"
			disabled={areActionsDisabled}
			onclick={handleVote}
			aria-label={m.voting_vote_for({ title: participant.title })}
		>
			{#if voteMutation.isPending}
				<Spinner data-icon="inline-start" />
			{/if}
			{m.voting_action()}
		</Button>
	{/if}
</li>
