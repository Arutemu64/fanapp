<script lang="ts">
	import type { ParticipantFullDTO } from '$lib/types/participant';

	import { createApiClient } from '$lib/api';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import * as Card from '$lib/components/ui/card';
	import { Spinner } from '$lib/components/ui/spinner';
	import { getToastService } from '$lib/services/toasts.svelte';
	import { pluralize } from '$lib/utils/formatters';
	import { Check, CheckCircle2, Heart, X } from '@lucide/svelte';

	const client = createApiClient();

	interface Props {
		participant: ParticipantFullDTO;
		hasVoted: boolean;
		canVote: boolean;
		onVoted?: () => void;
	}

	let { participant, hasVoted, canVote, onVoted }: Props = $props();
	const toastService = getToastService();

	let isLoading = $state(false);
	let areActionsDisabled = $derived(isLoading || !canVote);

	let optimisticDelta = $state(0);
	let votesCount = $derived(participant.votes_count + optimisticDelta);

	async function handleVote() {
		if (areActionsDisabled || participant.user_vote !== null) return;

		isLoading = true;
		optimisticDelta += 1;
		try {
			const { data, error, response } = await client.POST('/voting/votes', {
				body: {
					participant_id: participant.id
				}
			});

			if (error || !response.ok) {
				optimisticDelta -= 1;
				toastService.error(error);
				return;
			}

			if (data) {
				toastService.add('Голос учтён', 'success');
				optimisticDelta = 0;
				onVoted?.();
			}
		} catch (err) {
			optimisticDelta -= 1;
			toastService.error(err);
		} finally {
			isLoading = false;
		}
	}

	async function handleCancelVote() {
		const vote = participant.user_vote;
		if (areActionsDisabled || vote === null) return;

		isLoading = true;
		optimisticDelta -= 1;
		try {
			const { error, response } = await client.DELETE('/voting/votes/{vote_id}', {
				params: {
					path: { vote_id: vote.id }
				}
			});

			if (error || !response.ok) {
				optimisticDelta += 1;
				toastService.error(error);
				return;
			}

			toastService.add('Голос отменён', 'success');
			optimisticDelta = 0;
			onVoted?.();
		} catch (err) {
			optimisticDelta += 1;
			toastService.error(err);
		} finally {
			isLoading = false;
		}
	}
</script>

<Card.Root
	as="article"
	class={[
		'flex w-full max-w-none flex-col p-4 transition-[box-shadow,border-color,background-color]',
		participant.user_vote !== null ? 'ring-2 ring-success' : ''
	]}
>
	<div class="mb-2 flex min-h-6 items-center justify-between gap-2">
		{#if participant.voting_number}
			<span class="text-xs font-semibold tracking-wide text-primary">
				№{participant.voting_number}
			</span>
		{:else}
			<span></span>
		{/if}

		{#if participant.user_vote !== null}
			<Badge variant="outline" class="shrink-0 border-success/30 bg-success/10 text-success">
				<span class="flex items-center gap-1">
					<CheckCircle2 class="size-3.5" />
					Твой голос
				</span>
			</Badge>
		{/if}
	</div>

	<h3 class="flex-1 text-base leading-snug font-bold break-words text-foreground">
		{participant.title}
	</h3>

	<!-- Footer row: vote count + action button.
	     min-h reserves the action area height (pt-3 12px + 44px button = 56px) so the vote
	     count stays vertically anchored when no button is shown — e.g. after voting elsewhere
	     in the nomination, other cards drop the button and the row would otherwise collapse
	     and make the count jump. Both buttons share the same 44px height below so toggling
	     vote<->cancel doesn't shift either. -->
	<div class="mt-3 flex min-h-14 items-center justify-between gap-2 border-t border-border pt-3">
		<div class="flex items-center gap-1.5 text-sm text-muted-foreground">
			<Heart class="size-3.5 shrink-0 fill-current text-muted-foreground/60" aria-hidden="true" />
			<span aria-live="polite">
				{votesCount}
				{pluralize(votesCount, 'голос', 'голоса', 'голосов')}
			</span>
		</div>

		{#if participant.user_vote !== null}
			<Button
				size="sm"
				variant="outline"
				class="min-h-11"
				disabled={areActionsDisabled}
				onclick={handleCancelVote}
				aria-label="Отменить голос"
			>
				{#if isLoading}
					<Spinner data-icon="inline-start" />
				{:else}
					<X data-icon="inline-start" />
				{/if}
				Отменить
			</Button>
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
</Card.Root>
