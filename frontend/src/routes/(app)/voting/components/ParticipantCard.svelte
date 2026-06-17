<script lang="ts">
	import { Card, Badge, Button } from 'flowbite-svelte';
	import { CheckCircleSolid, CheckOutline, CloseOutline, HeartSolid } from 'flowbite-svelte-icons';
	import { pluralize } from '$lib/utils/formatters';
	import { createApiClient } from '$lib/api';
	const client = createApiClient();
	import { getToastService } from '$lib/services/toasts.svelte';
	import type { ParticipantFullDTO } from '$lib/types/participant';

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

	async function handleVote() {
		if (areActionsDisabled || participant.user_vote !== null) return;

		isLoading = true;
		try {
			const { data, error, response } = await client.POST('/voting/votes', {
				body: {
					participant_id: participant.id
				}
			});

			if (error || !response.ok) {
				toastService.error(error);
				return;
			}

			if (data) {
				toastService.add('Голос успешно отдан!', 'success');
				onVoted?.();
			}
		} catch (err) {
			toastService.error(err);
		} finally {
			isLoading = false;
		}
	}

	async function handleCancelVote() {
		const vote = participant.user_vote;
		if (areActionsDisabled || vote === null) return;

		isLoading = true;
		try {
			const { error, response } = await client.DELETE('/voting/votes/{vote_id}', {
				params: {
					path: { vote_id: vote.id }
				}
			});

			if (error || !response.ok) {
				toastService.error(error);
				return;
			}

			toastService.add('Голос отменён', 'success');
			onVoted?.();
		} catch (err) {
			toastService.error(err);
		} finally {
			isLoading = false;
		}
	}
</script>

<Card
	class={[
		'relative flex w-full max-w-none flex-col overflow-hidden p-4 transition-[box-shadow,border-color,background-color] hover:shadow-md',
		participant.user_vote !== null ? 'ring-2 ring-green-600 dark:ring-green-500' : ''
	]}
>
	<!-- Watermark number -->
	{#if participant.voting_number}
		<div
			class="pointer-events-none absolute right-2 bottom-0 text-8xl leading-none font-black text-gray-900/[0.04] select-none dark:text-white/[0.06]"
			aria-hidden="true"
		>
			{participant.voting_number}
		</div>
	{/if}

	<!-- Header row: number + badge -->
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

	<!-- Title -->
	<h3 class="relative z-10 flex-1 text-base leading-snug font-bold text-gray-900 dark:text-white">
		{participant.title}
	</h3>

	<!-- Footer row: vote count + action button -->
	<div
		class="relative z-10 mt-3 flex items-center justify-between gap-2 border-t border-gray-100 pt-3 dark:border-gray-700"
	>
		<div class="flex items-center gap-1.5 text-sm text-gray-500 dark:text-gray-400">
			<HeartSolid class="h-3.5 w-3.5 shrink-0 text-red-400" />
			<span>
				{participant.votes_count}
				{pluralize(participant.votes_count, 'голос', 'голоса', 'голосов')}
			</span>
		</div>

		{#if participant.user_vote !== null}
			<Button
				size="sm"
				color="red"
				outline
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
