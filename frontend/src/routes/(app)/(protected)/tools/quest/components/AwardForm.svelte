<script lang="ts">
	import CloudOff from '@lucide/svelte/icons/cloud-off';
	import { createMutation, useQueryClient } from '@tanstack/svelte-query';
	import { tick } from 'svelte';

	import { getApiErrorCode, getApiErrorDetail, getApiFieldError } from '#lib/api/errors.js';
	import { listQuestAwardsQueryKey } from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import { handOffWhenQueued } from '#lib/api/queuedWrite.svelte.js';
	import { queuedAwardOptions } from '#lib/api/writeQueue.js';
	import FormError from '#lib/components/FormError.svelte';
	import { Button } from '#lib/components/ui/button/index.js';
	import * as Field from '#lib/components/ui/field/index.js';
	import { Input } from '#lib/components/ui/input/index.js';
	import { Spinner } from '#lib/components/ui/spinner/index.js';
	import UserAvatar from '#lib/components/UserAvatar.svelte';
	import Username from '#lib/components/Username.svelte';
	import { m } from '#lib/paraglide/messages.js';
	import { getToastService } from '#lib/services/toasts.svelte.js';
	import { uuidv7 } from '#lib/utils/uuidv7.js';

	import { type AwardTarget, isUnverified } from '../awardTarget.js';

	interface Props {
		player: AwardTarget;
		maxAward: number;
		amount: string;
		message: string;
		onDone: () => void;
	}

	let { player, maxAward, amount = $bindable(), message = $bindable(), onDone }: Props = $props();

	const MESSAGE_MAX_LENGTH = 200;
	const AMOUNT_PRESETS = [5, 10, 20, 50];
	const WHOLE_NUMBER = /^\d+$/;

	let verifiedPlayer = $derived(isUnverified(player) ? null : player);

	let presets = $derived(AMOUNT_PRESETS.filter((preset) => preset <= maxAward));

	let amountInput = $state<HTMLInputElement | null>(null);
	let messageInput = $state<HTMLInputElement | null>(null);

	function focusOnMount(node: HTMLElement) {
		node.focus();
	}

	const toastService = getToastService();
	const queryClient = useQueryClient();

	const awardMutation = createMutation(() => queuedAwardOptions());
	handOffWhenQueued(awardMutation, () => {
		toastService.add(m.quest_tool_award_queued(), 'info');
		onDone();
	});

	let awardId = uuidv7();

	let amountError = $state('');
	let messageError = $state('');
	let submitError = $state('');

	function parseAmount(): number | null {
		const trimmed = amount.trim();
		if (!WHOLE_NUMBER.test(trimmed)) {
			return null;
		}
		const value = Number(trimmed);
		if (value < 1 || value > maxAward) {
			return null;
		}
		return value;
	}

	function validateAmount() {
		const valid = parseAmount() !== null;
		amountError = valid ? '' : m.quest_tool_validation_amount({ max: maxAward });
		return valid;
	}

	function validateMessage() {
		const valid = message.trim() !== '';
		messageError = valid ? '' : m.quest_tool_validation_message();
		return valid;
	}

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

	function pickPreset(preset: number) {
		amount = String(preset);
		handleAmountInput();
	}

	async function focusFirstError() {
		await tick();
		if (amountError) {
			amountInput?.focus();
		} else if (messageError) {
			messageInput?.focus();
		}
	}

	function handleSubmit(event: Event) {
		event.preventDefault();
		submitError = '';
		const isAmountValid = validateAmount();
		const isMessageValid = validateMessage();
		const awardedAmount = parseAmount();
		if (!isAmountValid || !isMessageValid || awardedAmount === null) {
			void focusFirstError();
			return;
		}

		awardMutation.mutate(
			{
				body: {
					award_id: awardId,
					user_number: player.number,
					amount: awardedAmount,
					message: message.trim()
				}
			},
			{
				onSuccess: () => {
					const done = verifiedPlayer
						? m.quest_tool_awarded({
								username: verifiedPlayer.username,
								points: m.quest_points({ count: awardedAmount })
							})
						: m.quest_tool_award_sent();
					toastService.add(done, 'success');
					onDone();
				},
				onError: (error) => {
					amountError = getApiFieldError(error, 'amount') ?? '';
					messageError = getApiFieldError(error, 'message') ?? '';
					if (amountError || messageError) {
						void focusFirstError();
						return;
					}
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

<form novalidate class="flex flex-col gap-4" onsubmit={handleSubmit}>
	<div class="flex flex-wrap items-center gap-3">
		{#if verifiedPlayer}
			<UserAvatar seed={verifiedPlayer.avatar_seed} class="size-12" />
			<div class="min-w-32 flex-1">
				<h2 {@attach focusOnMount} tabindex="-1" class="text-base font-semibold text-foreground">
					<Username username={verifiedPlayer.username} />
				</h2>
				<p class="text-sm text-muted-foreground">
					{m.quest_points({ count: verifiedPlayer.points })}
				</p>
			</div>
		{:else}
			<div
				class="flex size-12 shrink-0 items-center justify-center rounded-full bg-muted text-muted-foreground"
			>
				<CloudOff class="size-5" aria-hidden="true" />
			</div>
			<div class="min-w-32 flex-1">
				<h2 {@attach focusOnMount} tabindex="-1" class="text-base font-semibold text-foreground">
					{m.quest_tool_unverified_player({ number: player.number })}
				</h2>
				<p class="text-sm text-muted-foreground">{m.quest_tool_unverified_hint()}</p>
			</div>
		{/if}
		<Button type="button" variant="outline" size="sm" class="ml-auto" onclick={onDone}>
			{m.quest_tool_change_player()}
		</Button>
	</div>

	<FormError message={submitError} />

	<Field.FieldGroup class="gap-4">
		<Field.Field data-invalid={amountError ? true : undefined}>
			<Field.FieldLabel for="quest-amount">{m.quest_tool_amount_label()}</Field.FieldLabel>
			<Input
				bind:ref={amountInput}
				id="quest-amount"
				name="amount"
				inputmode="numeric"
				autocomplete="off"
				bind:value={amount}
				readonly={awardMutation.isPending}
				oninput={handleAmountInput}
				aria-invalid={amountError ? true : undefined}
				aria-describedby={amountError ? 'quest-amount-error' : 'quest-amount-hint'}
			/>
			{#if presets.length > 0}
				<div class="flex flex-wrap gap-2" role="group" aria-label={m.quest_tool_amount_presets()}>
					{#each presets as preset (preset)}
						{const selected = $derived(amount.trim() === String(preset))}
						<Button
							type="button"
							variant={selected ? 'default' : 'outline'}
							size="sm"
							class="min-w-11 tabular-nums"
							aria-pressed={selected}
							disabled={awardMutation.isPending}
							onclick={() => pickPreset(preset)}
						>
							{preset}
						</Button>
					{/each}
				</div>
			{/if}
			{#if amountError}
				<Field.FieldError id="quest-amount-error">{amountError}</Field.FieldError>
			{:else}
				<Field.FieldDescription id="quest-amount-hint">
					{m.quest_tool_amount_hint({ max: maxAward })}
				</Field.FieldDescription>
			{/if}
		</Field.Field>

		<Field.Field data-invalid={messageError ? true : undefined}>
			<Field.FieldLabel for="quest-message">{m.quest_tool_message_label()}</Field.FieldLabel>
			<Input
				bind:ref={messageInput}
				id="quest-message"
				name="message"
				maxlength={MESSAGE_MAX_LENGTH}
				autocomplete="off"
				placeholder={m.quest_tool_message_placeholder()}
				bind:value={message}
				readonly={awardMutation.isPending}
				oninput={handleMessageInput}
				aria-invalid={messageError ? true : undefined}
				aria-describedby={messageError ? 'quest-message-error' : 'quest-message-hint'}
			/>
			{#if messageError}
				<Field.FieldError id="quest-message-error">{messageError}</Field.FieldError>
			{:else}
				<Field.FieldDescription id="quest-message-hint">
					{m.quest_tool_message_hint()}
				</Field.FieldDescription>
			{/if}
		</Field.Field>
	</Field.FieldGroup>

	<Button type="submit" size="lg" class="w-full" disabled={awardMutation.isPending}>
		{#if awardMutation.isPending}
			<Spinner data-icon="inline-start" />
		{/if}
		{m.quest_tool_submit()}
	</Button>
</form>
