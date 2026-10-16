<script lang="ts">
	import { createMutation, useQueryClient } from '@tanstack/svelte-query';

	import type { QuestAwardItemDto } from '#lib/api/generated/index.js';

	import { getApiErrorDetail } from '#lib/api/errors.js';
	import {
		cancelQuestAwardMutation,
		listQuestAwardsQueryKey
	} from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import * as AlertDialog from '#lib/components/ui/alert-dialog/index.js';
	import { Badge } from '#lib/components/ui/badge/index.js';
	import { Button } from '#lib/components/ui/button/index.js';
	import { m } from '#lib/paraglide/messages.js';
	import { getToastService } from '#lib/services/toasts.svelte.js';
	import { formatRelativeTime } from '#lib/utils/formatters.js';
	import { offlineWriteGate } from '#lib/utils/offlineAction.js';

	interface Props {
		award: QuestAwardItemDto;
		/** Show who gave the award: only a manager's list mixes volunteers. */
		showAwarder: boolean;
	}

	let { award, showAwarder }: Props = $props();

	const toastService = getToastService();
	const queryClient = useQueryClient();
	const offlineGate = offlineWriteGate();

	let confirmOpen = $state(false);
	let points = $derived(m.quest_points({ count: award.amount }));
	let cancelled = $derived(award.cancelled_at !== null);

	const cancelMutation = createMutation(() => ({
		...cancelQuestAwardMutation(),
		// Refetch whichever way it went: a refusal (window expired, cancelled
		// elsewhere) also means this row's button is out of date.
		onSettled: () => queryClient.invalidateQueries({ queryKey: listQuestAwardsQueryKey() })
	}));

	function handleConfirm() {
		cancelMutation.mutate(
			{ path: { award_id: award.id } },
			{
				onSuccess: () => toastService.add(m.quest_tool_cancelled(), 'success'),
				onError: (error) =>
					toastService.add(getApiErrorDetail(error) ?? m.quest_tool_cancel_failed(), 'error')
			}
		);
	}
</script>

<li class="flex items-start gap-3 p-3 sm:px-4">
	<div class="min-w-0 flex-1">
		<p class={['text-base text-foreground', cancelled && 'text-muted-foreground line-through']}>
			<span class="font-semibold tabular-nums">+{points}</span>
			<span class="break-all">@{award.user.username}</span>
		</p>
		<p class="text-sm wrap-break-word text-muted-foreground">{award.message}</p>
		<p class="text-xs text-muted-foreground">
			{formatRelativeTime(award.created_at)}
			{#if showAwarder && award.awarded_by}
				· {m.quest_tool_awarded_by({ username: award.awarded_by.username })}
			{/if}
		</p>
	</div>
	{#if cancelled}
		<Badge variant="secondary">{m.quest_tool_cancelled_badge()}</Badge>
	{:else if award.can_cancel}
		<Button
			type="button"
			variant="outline"
			size="sm"
			disabled={cancelMutation.isPending}
			aria-disabled={offlineGate.blocked}
			onclick={offlineGate.guard(() => (confirmOpen = true))}
		>
			{m.quest_tool_cancel()}
		</Button>
	{/if}
</li>

<AlertDialog.Root bind:open={confirmOpen}>
	<AlertDialog.Content>
		<AlertDialog.Header>
			<AlertDialog.Title>{m.quest_tool_cancel_title()}</AlertDialog.Title>
			<AlertDialog.Description>
				{m.quest_tool_cancel_description({ username: award.user.username, points })}
			</AlertDialog.Description>
		</AlertDialog.Header>
		<AlertDialog.Footer>
			<AlertDialog.Cancel>{m.common_cancel()}</AlertDialog.Cancel>
			<AlertDialog.Action variant="destructive" onclick={handleConfirm}>
				{m.quest_tool_cancel_confirm()}
			</AlertDialog.Action>
		</AlertDialog.Footer>
	</AlertDialog.Content>
</AlertDialog.Root>
