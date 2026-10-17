<script lang="ts">
	import type { QuestAwardItemDto } from '#lib/api/generated/index.js';

	import { Badge } from '#lib/components/ui/badge/index.js';
	import { Button } from '#lib/components/ui/button/index.js';
	import { m } from '#lib/paraglide/messages.js';
	import { formatRelativeTime } from '#lib/utils/formatters.js';
	import { offlineWriteGate } from '#lib/utils/offlineAction.js';

	interface Props {
		award: QuestAwardItemDto;
		/** Show who gave the award: only a manager's list mixes volunteers. */
		showAwarder: boolean;
		/** Any cancel in flight blocks every row: the list shares one mutation. */
		cancelling: boolean;
		onCancel: (award: QuestAwardItemDto) => void;
	}

	let { award, showAwarder, cancelling, onCancel }: Props = $props();

	const offlineGate = offlineWriteGate();

	let points = $derived(m.quest_points({ count: award.amount }));
	let cancelled = $derived(award.cancelled_at !== null);
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
			disabled={cancelling}
			aria-disabled={offlineGate.blocked}
			onclick={offlineGate.guard(() => onCancel(award))}
		>
			{m.quest_tool_cancel()}
		</Button>
	{/if}
</li>
