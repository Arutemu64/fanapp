<script lang="ts">
	import { CircleCheck, ThumbsUp } from '@lucide/svelte';
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

	// hey-api generates no mutation keys; this one lets every row see the others' votes.
	const VOTE_MUTATION_KEY = ['addVote'];

	// Stays pending until the page has refetched the ballot, so the button stays
	// disabled and the optimistic count holds until the server's own count and
	// «Твой голос» replace them — no round-trip where the count drops back.
	const voteMutation = createMutation(() => ({
		...addVoteMutation(),
		mutationKey: VOTE_MUTATION_KEY,
		onSuccess: async () => {
			await onVoted?.();
		}
	}));

	// A vote in flight on any row disables every row: the backend takes one vote
	// per nomination, so a second tap before the ballot refetch lands would fail
	// with VoteAlreadyExists and toast an error beside the success.
	const votesInFlight = useIsMutating({ mutationKey: VOTE_MUTATION_KEY });

	let areActionsDisabled = $derived(votesInFlight.current > 0 || !canVote);
	let isVotedFor = $derived(participant.user_vote !== null);

	// Counted until the refetched row carries the vote itself, not until the
	// mutation settles: the two land in separate notifications, and keying on
	// isPending alone could count the vote twice for a frame.
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
		<h2 class="text-base leading-snug font-semibold wrap-break-word text-foreground">
			{participant.title}
		</h2>

		{#if isVotedFor}
			<div class="mt-1.5">
				<!-- Card fill, not a success tint: a /10 tint on the row's own /10 tint
					stacks to ~4.2:1, under AA for the badge's 12px text. -->
				<Badge
					variant="outline"
					class="inline-flex items-center gap-1 border-success/30 bg-card px-2 py-0.5 text-xs font-medium text-success"
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

	<!-- A labelled button, not an icon: no icon reads as "vote" without its label
	     (NN/g, Icon Usability). Tonal rather than filled, because a solid button on
	     every row would bury the page's real primary action. -->
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
