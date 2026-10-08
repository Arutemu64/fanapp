<script lang="ts">
	import { Activity } from '@lucide/svelte';

	import { countOnlineUsers } from '#lib/api/generated/index.js';
	import { createApiClient } from '#lib/api/index.js';
	import MenuGroup from '#lib/components/MenuGroup.svelte';
	import * as Item from '#lib/components/ui/item/index.js';
	import { pluralize } from '#lib/utils/formatters.js';

	// Coarse on purpose: the figure is a rough "how many are here now", and a
	// user's presence marker ages out server-side within ~45s, so a tighter poll
	// would add load without adding meaning.
	const REFRESH_MS = 20_000;

	const client = createApiClient();

	// null until the first response lands, so the card shows a placeholder
	// instead of a misleading "0" while loading.
	let count = $state<number | null>(null);

	async function refresh(): Promise<void> {
		// A failed poll — a dropped connection included, which the client returns
		// as `error` rather than throwing — leaves the stale count standing until
		// the next successful one: this is a glanceable stat, not critical data.
		const { data, error, response } = await countOnlineUsers({ client });
		if (!error && response?.ok && data) {
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

<!-- A row in the toolbox's own shape (icon tile, title, description) so the stat
     reads as part of the menu below rather than a dashboard widget. No aria-live:
     the count repaints every poll, and a live region would interrupt a screen
     reader user every 20 seconds with a figure they didn't ask for. -->
<MenuGroup>
	<Item.Root class="rounded-none">
		<Item.Media class="size-9 rounded-lg bg-muted text-muted-foreground">
			<Activity class="size-5" aria-hidden="true" />
		</Item.Media>
		<Item.Content>
			<Item.Title class="text-base tabular-nums">
				{#if count === null}
					<span class="text-muted-foreground">…</span>
				{:else}
					{count}
					{pluralize(count, 'человек', 'человека', 'человек')}
				{/if}
			</Item.Title>
			<Item.Description>сейчас в приложении</Item.Description>
		</Item.Content>
	</Item.Root>
</MenuGroup>
