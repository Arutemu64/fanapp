<script lang="ts">
	import type { LeaderboardEntryDto } from '#lib/api/generated/index.js';

	import UserAvatar from '#lib/components/UserAvatar.svelte';
	import { m } from '#lib/paraglide/messages.js';

	interface Props {
		entry: LeaderboardEntryDto;
		isOwn: boolean;
	}

	let { entry, isOwn }: Props = $props();

	const MEDAL_FILLS: Partial<Record<number, string>> = {
		1: 'bg-medal-gold',
		2: 'bg-medal-silver',
		3: 'bg-medal-bronze'
	};
	let medalFill = $derived(MEDAL_FILLS[entry.rank]);
</script>

<li
	class={['flex items-center gap-3 px-3 py-2.5 sm:px-4', isOwn && 'bg-primary/10']}
	aria-current={isOwn ? 'true' : undefined}
>
	<!-- min-w, not a fixed size: a four-digit rank still fits the pill. -->
	<span
		class={[
			'inline-flex h-7 min-w-7 shrink-0 items-center justify-center rounded-full px-1 text-sm font-semibold tabular-nums',
			medalFill
				? [medalFill, 'text-medal-foreground ring-1 ring-foreground/10 ring-inset']
				: 'text-muted-foreground'
		]}
	>
		{entry.rank}
	</span>
	<UserAvatar seed={entry.player.avatar_seed} class="size-8" />
	<!-- Only the name truncates: «(ты)» is what marks the row besides its tint. -->
	<span class="flex min-w-0 flex-1 items-baseline gap-1 text-base">
		<span class="truncate text-foreground">@{entry.player.username}</span>
		{#if isOwn}
			<span class="shrink-0 text-muted-foreground">({m.quest_leaderboard_you()})</span>
		{/if}
	</span>
	<span class="shrink-0 text-sm font-medium text-foreground tabular-nums">
		{m.quest_points({ count: entry.player.points })}
	</span>
</li>
