<script lang="ts">
	import { Activity } from '@lucide/svelte';
	import { createQuery } from '@tanstack/svelte-query';

	import { countOnlineUsersOptions } from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import { m } from '#lib/paraglide/messages.js';

	// Coarse on purpose: the figure is a rough "how many are here now", and a
	// user's presence marker ages out server-side within ~45s, so a tighter poll
	// would add load without adding meaning.
	const REFRESH_MS = 20_000;

	// TanStack's interval skips its tick while the window is in the background
	// (refetchIntervalInBackground is off), and a failed poll keeps the last count
	// standing: this is a glanceable stat, not critical data. A copy older than one
	// poll refetches on mount instead of waiting out the client's 60s staleTime.
	const onlineQuery = createQuery(() => ({
		...countOnlineUsersOptions(),
		refetchInterval: REFRESH_MS,
		staleTime: REFRESH_MS
	}));
	// Undefined until the first response lands, so the card shows a placeholder
	// instead of a misleading "0" while loading.
	let count = $derived(onlineQuery.data?.count);
</script>

<div class="flex items-center gap-3 rounded-lg border border-border bg-card p-4">
	<div class="flex size-10 shrink-0 items-center justify-center rounded-full bg-muted">
		<Activity class="size-5 text-muted-foreground" aria-hidden="true" />
	</div>
	<div>
		<p class="text-xl font-semibold tabular-nums" aria-live="polite">
			{#if count === undefined}
				<span class="text-muted-foreground">…</span>
			{:else}
				{m.online_now_people({ count })}
			{/if}
		</p>
		<p class="text-xs text-muted-foreground">{m.online_now_label()}</p>
	</div>
</div>
