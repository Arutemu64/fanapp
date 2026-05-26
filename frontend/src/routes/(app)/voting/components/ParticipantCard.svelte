<script lang="ts">
	import { Card, Badge, Button } from 'flowbite-svelte';
	import { CheckCircleSolid, HeartSolid } from 'flowbite-svelte-icons';
	import { pluralize } from '$lib/utils/formatters';
	import { createApiClient } from '$lib/api';
	const client = createApiClient();
	import { getToastService } from '$lib/services/toasts.svelte';
	import type { ParticipantFullDTO } from '$lib/types/participant';

	interface Props {
		participant: ParticipantFullDTO;
		nominationId: string;
		hasVoted: boolean;
		canVote: boolean;
		onVoted?: () => void;
	}

	let { participant, nominationId, hasVoted, canVote, onVoted }: Props = $props();
	const toastService = getToastService();

	let isLoading = $state(false);
	let areActionsDisabled = $derived(isLoading || !canVote);

	async function handleVote() {
		if (areActionsDisabled || participant.user_vote !== null) return;

		isLoading = true;
		try {
			const { data, error, response } = await client.PUT(
				'/voting/nominations/{nomination_id}/vote',
				{
					params: {
						path: { nomination_id: nominationId }
					},
					body: {
						participant_id: participant.id
					}
				}
			);

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
		if (areActionsDisabled || participant.user_vote === null) return;

		isLoading = true;
		try {
			const { error, response } = await client.DELETE('/voting/nominations/{nomination_id}/vote', {
				params: {
					path: { nomination_id: nominationId }
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
		'relative flex w-full max-w-none flex-col py-3 ps-4 pe-3 transition-[box-shadow,border-color]',
		participant.user_vote !== null && 'ring-2 ring-green-400 dark:ring-green-500'
	]}
>
	{#if participant.user_vote !== null}
		<Badge color="green" border class="absolute top-2 right-2 shrink-0 text-sm">
			<span class="flex items-center gap-1">
				<CheckCircleSolid class="h-4 w-4" />
				<span class="hidden sm:inline">Твой голос</span>
			</span>
		</Badge>
	{/if}

	<div class="min-w-0 flex-1">
		{#if participant.voting_number}
			<div class="mb-0.5 text-xs font-medium text-gray-500 sm:mb-1 sm:text-sm dark:text-gray-400">
				№{participant.voting_number}
			</div>
		{/if}

		<h3 class="text-lg font-bold text-gray-900 dark:text-white">
			{participant.title}
		</h3>
	</div>

	<div class="mt-auto flex items-center justify-between pt-2 sm:pt-3">
		<div class="flex items-center gap-1 text-xs text-gray-500 sm:text-sm dark:text-gray-400">
			<HeartSolid class="h-3.5 w-3.5 text-red-500" />
			<span>
				{participant.votes_count}
				{pluralize(participant.votes_count, 'голос', 'голоса', 'голосов')}
			</span>
		</div>

		<div class="flex min-h-11 min-w-24 items-center">
			{#if participant.user_vote !== null}
				<Button
					size="md"
					color="red"
					outline
					loading={isLoading}
					disabled={areActionsDisabled}
					onclick={handleCancelVote}
					aria-label="Отменить голос"
				>
					Отменить
				</Button>
			{:else if !hasVoted}
				<Button
					size="md"
					color="primary"
					loading={isLoading}
					disabled={areActionsDisabled}
					onclick={handleVote}
					aria-label={`Голосовать за ${participant.title}`}>Голосовать</Button
				>
			{/if}
		</div>
	</div>
</Card>
