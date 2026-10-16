<script lang="ts">
	import { CircleAlert } from '@lucide/svelte';
	import { createMutation, useQueryClient } from '@tanstack/svelte-query';

	import type { QuestPlayerDto } from '#lib/api/generated/index.js';

	import { getApiErrorCode, getApiErrorDetail, getApiFieldError } from '#lib/api/errors.js';
	import {
		awardQuestPointsMutation,
		listQuestAwardsQueryKey
	} from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import * as Alert from '#lib/components/ui/alert/index.js';
	import { Button } from '#lib/components/ui/button/index.js';
	import * as Field from '#lib/components/ui/field/index.js';
	import { Input } from '#lib/components/ui/input/index.js';
	import { Spinner } from '#lib/components/ui/spinner/index.js';
	import UserAvatar from '#lib/components/UserAvatar.svelte';
	import { m } from '#lib/paraglide/messages.js';
	import { getToastService } from '#lib/services/toasts.svelte.js';
	import { offlineWriteGate } from '#lib/utils/offlineAction.js';
	import { uuidv7 } from '#lib/utils/uuidv7.js';

	interface Props {
		player: QuestPlayerDto;
		maxAward: number;
		onDone: () => void;
	}

	let { player, maxAward, onDone }: Props = $props();

	const MESSAGE_MAX_LENGTH = 200;

	const toastService = getToastService();
	const queryClient = useQueryClient();

	const awardMutation = createMutation(() => ({
		...awardQuestPointsMutation(),
		onSuccess: () => queryClient.invalidateQueries({ queryKey: listQuestAwardsQueryKey() })
	}));

	// One ID per award, kept across submits: if the response is lost on the
	// festival Wi-Fi, pressing again replays the award instead of paying the
	// player twice (docs/adr/0034).
	let awardId = uuidv7();

	let amount = $state<number | undefined>(undefined);
	let message = $state('');
	let amountError = $state('');
	let messageError = $state('');
	let submitError = $state('');

	function validateAmount() {
		const valid =
			amount !== undefined && Number.isInteger(amount) && amount >= 1 && amount <= maxAward;
		amountError = valid ? '' : m.quest_tool_validation_amount({ max: maxAward });
		return valid;
	}

	function validateMessage() {
		const valid = message.trim() !== '';
		messageError = valid ? '' : m.quest_tool_validation_message();
		return valid;
	}

	// Re-validate live only after a field has already shown an error once.
	function handleAmountInput() {
		if (amountError) {
			validateAmount();
		}
	}

	function handleMessageInput() {
		if (messageError) {
			validateMessage();
		}
	}

	const offlineGate = offlineWriteGate();

	function handleSubmit(event: Event) {
		event.preventDefault();
		submitError = '';
		const isAmountValid = validateAmount();
		const isMessageValid = validateMessage();
		if (!isAmountValid || !isMessageValid || amount === undefined) {
			return;
		}
		const awardedAmount = amount;

		awardMutation.mutate(
			{
				body: {
					award_id: awardId,
					user_id: player.id,
					amount: awardedAmount,
					message: message.trim()
				}
			},
			{
				onSuccess: () => {
					toastService.add(
						m.quest_tool_awarded({
							username: player.username,
							points: m.quest_points({ count: awardedAmount })
						}),
						'success'
					);
					onDone();
				},
				onError: (error) => {
					amountError = getApiFieldError(error, 'amount') ?? '';
					messageError = getApiFieldError(error, 'message') ?? '';
					if (amountError || messageError) {
						return;
					}
					// An earlier press went through but its response was lost, and the
					// form changed since. That award stands; the next press is a new one.
					if (getApiErrorCode(error) === 'QUEST_AWARD_ALREADY_EXISTS') {
						awardId = uuidv7();
						void queryClient.invalidateQueries({ queryKey: listQuestAwardsQueryKey() });
					}
					submitError = getApiErrorDetail(error) ?? m.quest_tool_award_failed();
				}
			}
		);
	}
</script>

<form class="flex flex-col gap-4" onsubmit={offlineGate.guard(handleSubmit)}>
	<div class="flex items-center gap-3">
		<UserAvatar seed={player.avatar_seed} class="size-12" />
		<div class="min-w-0 flex-1">
			<p class="truncate text-base font-semibold text-foreground">@{player.username}</p>
			<p class="text-sm text-muted-foreground">{m.quest_points({ count: player.points })}</p>
		</div>
		<Button type="button" variant="outline" size="sm" onclick={onDone}>
			{m.quest_tool_change_player()}
		</Button>
	</div>

	{#if submitError}
		<Alert.Root variant="destructive">
			<CircleAlert class="size-4" />
			<Alert.Description>{submitError}</Alert.Description>
		</Alert.Root>
	{/if}

	<Field.FieldGroup class="gap-4">
		<Field.Field data-invalid={amountError ? true : undefined}>
			<Field.FieldLabel for="quest-amount">{m.quest_tool_amount_label()}</Field.FieldLabel>
			<Input
				id="quest-amount"
				name="amount"
				type="number"
				min="1"
				max={maxAward}
				step="1"
				inputmode="numeric"
				autocomplete="off"
				bind:value={amount}
				disabled={awardMutation.isPending}
				oninput={handleAmountInput}
				aria-invalid={amountError ? true : undefined}
			/>
			{#if amountError}
				<Field.FieldError>{amountError}</Field.FieldError>
			{:else}
				<Field.FieldDescription
					>{m.quest_tool_amount_hint({ max: maxAward })}</Field.FieldDescription
				>
			{/if}
		</Field.Field>

		<Field.Field data-invalid={messageError ? true : undefined}>
			<Field.FieldLabel for="quest-message">{m.quest_tool_message_label()}</Field.FieldLabel>
			<Input
				id="quest-message"
				name="message"
				maxlength={MESSAGE_MAX_LENGTH}
				autocomplete="off"
				placeholder={m.quest_tool_message_placeholder()}
				bind:value={message}
				disabled={awardMutation.isPending}
				oninput={handleMessageInput}
				aria-invalid={messageError ? true : undefined}
			/>
			{#if messageError}
				<Field.FieldError>{messageError}</Field.FieldError>
			{:else}
				<Field.FieldDescription>{m.quest_tool_message_hint()}</Field.FieldDescription>
			{/if}
		</Field.Field>
	</Field.FieldGroup>

	<Button
		type="submit"
		size="lg"
		class="w-full"
		disabled={awardMutation.isPending}
		aria-disabled={offlineGate.blocked}
	>
		{#if awardMutation.isPending}
			<Spinner data-icon="inline-start" />
		{/if}
		{m.quest_tool_submit()}
	</Button>
</form>
