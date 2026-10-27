<script lang="ts">
	import type { LeaderboardEntryDto } from '#lib/api/generated/index.js';

	import UserAvatar from '#lib/components/UserAvatar.svelte';
	import Username from '#lib/components/Username.svelte';
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
	<span class="min-w-0 flex-1 text-base">
		<Username username={entry.player.username} class="text-foreground" />
		{#if isOwn}
			<span class="whitespace-nowrap text-muted-foreground">({m.quest_leaderboard_you()})</span>
		{/if}
	</span>
	<span class="shrink-0 text-sm font-medium text-foreground tabular-nums">
		{m.quest_points({ count: entry.player.points })}
	</span>
</li>
