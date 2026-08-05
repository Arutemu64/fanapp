<script lang="ts">
	import type { ParticipantFullDTO } from '$lib/types/participant';

	import { createApiClient } from '$lib/api';
	import { getToastService } from '$lib/services/toasts.svelte';
	import { pluralize } from '$lib/utils/formatters';
	import { Badge, Button, Card } from 'flowbite-svelte';
	import { CheckCircleSolid, CheckOutline, CloseOutline, HeartSolid } from 'flowbite-svelte-icons';

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

	// Optimistic count so a vote/cancel moves the number instantly on flaky con-wifi,
	// before the full refetch lands. A writable $derived lets us reassign it on click
	// and snaps it back to the authoritative server value whenever fresh data arrives
	// (after onVoted -> invalidate), so there's no double-counting to reconcile.
	let votesCount = $derived(participant.votes_count);

	async function handleVote() {
		if (areActionsDisabled || participant.user_vote !== null) return;

		isLoading = true;
		votesCount += 1; // optimistic
		try {
			const { data, error, response } = await client.POST('/voting/votes', {
				body: {
					participant_id: participant.id
				}
			});

			if (error || !response.ok) {
				votesCount -= 1; // revert
				toastService.error(error);
				return;
			}

			if (data) {
				toastService.add('Голос успешно отдан!', 'success');
				onVoted?.();
			}
		} catch (err) {
			votesCount -= 1; // revert
			toastService.error(err);
		} finally {
			isLoading = false;
		}
	}

	async function handleCancelVote() {
		const vote = participant.user_vote;
		if (areActionsDisabled || vote === null) return;

		isLoading = true;
		votesCount -= 1; // optimistic
		try {
			const { error, response } = await client.DELETE('/voting/votes/{vote_id}', {
				params: {
					path: { vote_id: vote.id }
				}
			});

			if (error || !response.ok) {
				votesCount += 1; // revert
				toastService.error(error);
				return;
			}

			toastService.add('Голос отменён', 'success');
			onVoted?.();
		} catch (err) {
			votesCount += 1; // revert
			toastService.error(err);
		} finally {
			isLoading = false;
		}
	}
</script>

<Card
	class={[
		'flex w-full max-w-none flex-col rounded-xl p-4 shadow-none transition-[box-shadow,border-color,background-color]',
		participant.user_vote !== null ? 'ring-2 ring-green-600 dark:ring-green-500' : ''
	]}
>
	<div class="mb-2 flex min-h-6 items-center justify-between gap-2">
		{#if participant.voting_number}
			<span class="text-xs font-semibold tracking-wide text-primary-600 dark:text-primary-400">
				№{participant.voting_number}
			</span>
		{:else}
			<span></span>
		{/if}

		{#if participant.user_vote !== null}
			<Badge color="green" border class="shrink-0">
				<span class="flex items-center gap-1">
					<CheckCircleSolid class="h-3.5 w-3.5" />
					Твой голос
				</span>
			</Badge>
		{/if}
	</div>

	<h3 class="flex-1 text-base leading-snug font-bold break-words text-gray-900 dark:text-white">
		{participant.title}
	</h3>

	<!-- Footer row: vote count + action button.
	     min-h reserves the action area height (pt-3 12px + 44px button = 56px) so the vote
	     count stays vertically anchored when no button is shown — e.g. after voting elsewhere
	     in the nomination, other cards drop the button and the row would otherwise collapse
	     and make the count jump. Both buttons share the same 44px height below so toggling
	     vote<->cancel doesn't shift either. -->
	<div
		class="mt-3 flex min-h-14 items-center justify-between gap-2 border-t border-gray-100 pt-3 dark:border-gray-700"
	>
		<div class="flex items-center gap-1.5 text-sm text-gray-500 dark:text-gray-400">
			<HeartSolid
				class="h-3.5 w-3.5 shrink-0 text-gray-400 dark:text-gray-500"
				aria-hidden="true"
			/>
			<span aria-live="polite">
				{votesCount}
				{pluralize(votesCount, 'голос', 'голоса', 'голосов')}
			</span>
		</div>

		{#if participant.user_vote !== null}
			<Button
				size="sm"
				color="alternative"
				class="min-h-11"
				loading={isLoading}
				disabled={areActionsDisabled}
				onclick={handleCancelVote}
				aria-label="Отменить голос"
			>
				<CloseOutline class="me-1.5 h-3.5 w-3.5" />
				Отменить
			</Button>
		{:else if !hasVoted}
			<Button
				size="sm"
				color="primary"
				class="min-h-11"
				loading={isLoading}
				disabled={areActionsDisabled}
				onclick={handleVote}
				aria-label={`Голосовать за ${participant.title}`}
			>
				<CheckOutline class="me-1.5 h-3.5 w-3.5" />
				Голосовать
			</Button>
		{/if}
	</div>
</Card>
