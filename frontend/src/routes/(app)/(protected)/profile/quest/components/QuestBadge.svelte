<script lang="ts">
	import type { CurrentUserDto, GetQuestOutput } from '#lib/api/generated/index.js';

	import QrCode from '#lib/components/QrCode.svelte';
	import * as Card from '#lib/components/ui/card/index.js';
	import UserAvatar from '#lib/components/UserAvatar.svelte';
	import Username from '#lib/components/Username.svelte';
	import { m } from '#lib/paraglide/messages.js';
	import { formatSyncedAt } from '#lib/utils/formatters.js';
	import { questCodeFor } from '#lib/utils/questCode.js';

	interface Props {
		user: CurrentUserDto;
		quest: GetQuestOutput | undefined;
		syncedAt?: number;
	}

	let { user, quest, syncedAt }: Props = $props();
</script>

<Card.Root class="mx-auto w-full max-w-sm gap-0 overflow-hidden p-0">
	<div class="relative flex items-end justify-between gap-3 bg-primary px-4 pt-7 pb-3">
		<span
			aria-hidden="true"
			class="absolute top-2.5 left-1/2 h-2 w-14 -translate-x-1/2 rounded-full bg-background"
		></span>
		<span class="font-display text-base font-bold text-primary-foreground">{m.app_name()}</span>
		<span class="text-xs font-semibold tracking-wide text-primary-foreground uppercase">
			{m.quest_title()}
		</span>
	</div>

	<div class="flex flex-col items-center gap-3 px-4 pt-5 pb-4 text-center sm:px-6">
		<div class="flex max-w-full items-center gap-3">
			<UserAvatar seed={user.avatar_seed} class="size-12" />
			<p class="min-w-0 text-start font-sans text-section text-foreground">
				<Username username={user.username} />
			</p>
		</div>
		<QrCode
			value={questCodeFor(user.number)}
			label={m.quest_code_label({ username: user.username })}
			class="w-full max-w-64 rounded-lg"
		/>
		<p class="flex flex-col items-center">
			<span class="text-sm text-muted-foreground">{m.user_number_label()}</span>
			<span class="font-sans text-headline text-foreground tabular-nums">{user.number}</span>
		</p>
		<p class="text-sm text-muted-foreground">{m.quest_code_hint()}</p>
	</div>

	{#if quest}
		<dl
			class="grid auto-cols-fr grid-flow-col gap-4 border-t border-dashed border-border px-4 py-3 text-center"
		>
			<div>
				<dt class="text-sm text-muted-foreground">{m.quest_summary_points()}</dt>
				<dd class="font-sans text-headline text-foreground tabular-nums">{quest.points}</dd>
			</div>
			{#if quest.rank !== null}
				<div>
					<dt class="text-sm text-muted-foreground">{m.quest_summary_rank()}</dt>
					<dd class="font-sans text-headline text-foreground tabular-nums">{quest.rank}</dd>
				</div>
			{/if}
		</dl>
		{#if syncedAt !== undefined}
			<p class="px-4 pb-3 text-center text-xs text-muted-foreground">
				{m.stale_data_synced({ syncedLabel: formatSyncedAt(syncedAt) })}
			</p>
		{/if}
	{/if}
</Card.Root>
