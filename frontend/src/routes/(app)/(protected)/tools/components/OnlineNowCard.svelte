<script lang="ts">
	import { createApiClient } from '$lib/api';
	import { pluralize } from '$lib/utils/formatters';
	import { Activity } from '@lucide/svelte';

	// Coarse on purpose: the figure is a rough "how many are here now", and a
	// user's presence marker ages out server-side within ~45s, so a tighter poll
	// would add load without adding meaning.
	const REFRESH_MS = 20_000;

	const client = createApiClient();

	// null until the first response lands, so the card shows a placeholder
	// instead of a misleading "0" while loading.
	let count = $state<number | null>(null);

	async function refresh(): Promise<void> {
		const { data, error, response } = await client.GET('/users/online-count');
		if (!error && response.ok && data) {
			count = data.count;
		}
	}

	// Poll only on the client: an $effect never runs during SSR, and its cleanup
	// clears the timer when the card unmounts (leaving the tools section).
	$effect(() => {
		void refresh();
		const id = setInterval(() => void refresh(), REFRESH_MS);
		return () => clearInterval(id);
	});
</script>

<div class="flex items-center gap-3 rounded-lg border border-border bg-card p-4">
	<div class="flex size-10 shrink-0 items-center justify-center rounded-full bg-muted">
		<Activity class="size-5 text-muted-foreground" aria-hidden="true" />
	</div>
	<div>
		<p class="text-xl font-semibold tabular-nums" aria-live="polite">
			{#if count === null}
				<span class="text-muted-foreground">…</span>
			{:else}
				{count}
				{pluralize(count, 'человек', 'человека', 'человек')}
			{/if}
		</p>
		<p class="text-xs text-muted-foreground">сейчас в приложении</p>
	</div>
</div>
