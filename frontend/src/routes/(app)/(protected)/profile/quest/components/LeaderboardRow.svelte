<script lang="ts">
	import type { LeaderboardEntryDto } from '#lib/api/generated/index.js';

	import UserAvatar from '#lib/components/UserAvatar.svelte';
	import { m } from '#lib/paraglide/messages.js';

	interface Props {
		entry: LeaderboardEntryDto;
		isOwn: boolean;
	}

	let { entry, isOwn }: Props = $props();
</script>

<li
	class={['flex items-center gap-3 px-3 py-2.5 sm:px-4', isOwn && 'bg-primary/10']}
	aria-current={isOwn ? 'true' : undefined}
>
	<span class="w-7 shrink-0 text-right text-sm font-semibold text-muted-foreground tabular-nums">
		{entry.rank}
	</span>
	<UserAvatar seed={entry.player.avatar_seed} class="size-8" />
	<span class="min-w-0 flex-1 truncate text-base text-foreground">
		@{entry.player.username}
		{#if isOwn}
			<span class="text-muted-foreground">({m.quest_leaderboard_you()})</span>
		{/if}
	</span>
	<span class="shrink-0 text-sm font-medium text-foreground tabular-nums">
		{m.quest_points({ count: entry.player.points })}
	</span>
</li>
