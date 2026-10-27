<script lang="ts">
	import CircleCheck from '@lucide/svelte/icons/circle-check';
	import X from '@lucide/svelte/icons/x';
	import { createMutation } from '@tanstack/svelte-query';

	import type { ParticipantFullDto, ParticipantVoteDto } from '#lib/api/generated/index.js';

	import { cancelVoteMutation } from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import * as Alert from '#lib/components/ui/alert/index.js';
	import { Button } from '#lib/components/ui/button/index.js';
	import { Spinner } from '#lib/components/ui/spinner/index.js';
	import { m } from '#lib/paraglide/messages.js';
	import { getToastService } from '#lib/services/toasts.svelte.js';

	interface Props {
		participant: ParticipantFullDto;
		vote: ParticipantVoteDto;
		canVote: boolean;
		onCancelled?: () => Promise<void> | void;
	}

	let { participant, vote, canVote, onCancelled }: Props = $props();
	const toastService = getToastService();

	const cancelMutation = createMutation(() => ({
		...cancelVoteMutation(),
		onSuccess: async () => {
			await onCancelled?.();
			toastService.add(m.voting_vote_cancelled(), 'success');
		}
	}));

	let participantLabel = $derived(
		participant.voting_number === null
			? participant.title
			: `№${participant.voting_number} · ${participant.title}`
	);

	function handleCancelVote() {
		if (cancelMutation.isPending || !canVote) return;

		cancelMutation.mutate(
			{ path: { vote_id: vote.id } },
			{ onError: (error) => toastService.error(error) }
		);
	}
</script>

<Alert.Root variant="success" role="status" class="flex items-center gap-3">
	<CircleCheck class="shrink-0" />
	<div class="min-w-0 flex-1">
		<Alert.Title>{m.voting_your_choice()}</Alert.Title>
		<Alert.Description class="wrap-break-word">{participantLabel}</Alert.Description>
	</div>
	{#if canVote}
		<Button
			variant="outline"
			size="sm"
			class="min-h-11 shrink-0"
			disabled={cancelMutation.isPending}
			onclick={handleCancelVote}
			aria-label={m.voting_cancel_vote()}
		>
			{#if cancelMutation.isPending}
				<Spinner data-icon="inline-start" />
			{:else}
				<X data-icon="inline-start" />
			{/if}
			{m.common_revert()}
		</Button>
	{/if}
</Alert.Root>
