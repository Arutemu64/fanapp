<script lang="ts">
	import { CheckCircle2, X } from '@lucide/svelte';
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
		// Wait for the refetch before confirming: the participant's row keeps its
		// old count and «Твой голос» badge until then, and a toast landing first
		// would contradict it on slow con-venue wifi. The spinner covers the gap.
		// The toast lives here, not in a `mutate` callback: the refetch removes this
		// notice, and TanStack drops a call's callbacks once its component unmounts.
		onSuccess: async () => {
			await onCancelled?.();
			toastService.add(m.voting_vote_cancelled(), 'success');
		}
	}));

	let participantLabel = $derived(
		participant.voting_number
			? `№${participant.voting_number} · ${participant.title}`
			: participant.title
	);

	function handleCancelVote() {
		if (cancelMutation.isPending || !canVote) return;

		cancelMutation.mutate(
			{ path: { vote_id: vote.id } },
			{ onError: (error) => toastService.error(error) }
		);
	}
</script>

<!-- role="status", not the Alert default "alert": this is the standing state of
     the ballot, not an urgent interruption to announce on every page load. -->
<Alert.Root variant="success" role="status" class="flex items-center gap-3">
	<CheckCircle2 class="shrink-0" />
	<div class="min-w-0 flex-1">
		<Alert.Title>{m.voting_your_choice()}</Alert.Title>
		<Alert.Description class="break-words">{participantLabel}</Alert.Description>
	</div>
	<!-- A closed ballot is final (CancelVote enforces the same window as casting),
	     so the button goes rather than sitting there disabled. -->
	{#if canVote}
		<Button
			variant="outline"
			size="sm"
			class="min-h-11 shrink-0"
			disabled={cancelMutation.isPending}
			onclick={handleCancelVote}
			aria-label={m.voting_cancel_vote_label()}
		>
			{#if cancelMutation.isPending}
				<Spinner data-icon="inline-start" />
			{:else}
				<X data-icon="inline-start" />
			{/if}
			{m.voting_cancel_vote()}
		</Button>
	{/if}
</Alert.Root>
