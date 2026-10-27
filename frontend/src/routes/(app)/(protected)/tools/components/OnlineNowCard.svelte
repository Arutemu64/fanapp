<script lang="ts">
	import Activity from '@lucide/svelte/icons/activity';
	import { createQuery } from '@tanstack/svelte-query';

	import { countOnlineUsersOptions } from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import { m } from '#lib/paraglide/messages.js';

	const REFRESH_MS = 20_000;

	const onlineQuery = createQuery(() => ({
		...countOnlineUsersOptions(),
		refetchInterval: REFRESH_MS,
		staleTime: REFRESH_MS,
		meta: { quietRefetchErrors: true }
	}));
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
				{count}
				{m.unit_people({ count })}
			{/if}
		</p>
		<p class="text-xs text-muted-foreground">{m.online_now_suffix()}</p>
	</div>
</div>
