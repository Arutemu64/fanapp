<script lang="ts">
	import { CheckCircle2, X } from '@lucide/svelte';

	import type { ParticipantFullDto, ParticipantVoteDto } from '#lib/api/generated/index.js';

	import { cancelVote } from '#lib/api/generated/index.js';
	import { createApiClient } from '#lib/api/index.js';
	import * as Alert from '#lib/components/ui/alert/index.js';
	import { Button } from '#lib/components/ui/button/index.js';
	import { Spinner } from '#lib/components/ui/spinner/index.js';
	import { getToastService } from '#lib/services/toasts.svelte.js';

	const client = createApiClient();

	interface Props {
		participant: ParticipantFullDto;
		vote: ParticipantVoteDto;
		canVote: boolean;
		onCancelled?: () => Promise<void> | void;
	}

	let { participant, vote, canVote, onCancelled }: Props = $props();
	const toastService = getToastService();

	let isLoading = $state(false);

	let participantLabel = $derived(
		participant.voting_number
			? `№${participant.voting_number} · ${participant.title}`
			: participant.title
	);

	async function handleCancelVote() {
		if (isLoading || !canVote) return;

		isLoading = true;
		try {
			const { error, response } = await cancelVote({
				client,
				path: { vote_id: vote.id }
			});

			if (error || !response?.ok) {
				toastService.error(error);
				return;
			}

			// Wait for the refetch before confirming: the participant's row keeps its
			// old count and «Твой голос» badge until then, and a toast landing first
			// would contradict it on slow con-venue wifi. The spinner covers the gap.
			await onCancelled?.();
			toastService.add('Голос отменён', 'success');
		} finally {
			isLoading = false;
		}
	}
</script>

<!-- role="status", not the Alert default "alert": this is the standing state of
     the ballot, not an urgent interruption to announce on every page load. -->
<Alert.Root variant="success" role="status" class="flex items-center gap-3">
	<CheckCircle2 class="shrink-0" />
	<div class="min-w-0 flex-1">
		<Alert.Title>Твой выбор</Alert.Title>
		<Alert.Description class="break-words">{participantLabel}</Alert.Description>
	</div>
	<!-- A closed ballot is final (CancelVote enforces the same window as casting),
	     so the button goes rather than sitting there disabled. -->
	{#if canVote}
		<Button
			variant="outline"
			size="sm"
			class="min-h-11 shrink-0"
			disabled={isLoading}
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
	{/if}
</Alert.Root>
