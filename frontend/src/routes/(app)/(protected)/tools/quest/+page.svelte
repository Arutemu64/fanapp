<script lang="ts">
	import { createQuery } from '@tanstack/svelte-query';

	import type { QuestPlayerDto } from '#lib/api/generated/index.js';

	import { getPublicConfigOptions } from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import SectionIntro from '#lib/components/SectionIntro.svelte';
	import * as Card from '#lib/components/ui/card/index.js';
	import { FALLBACK_CONFIG } from '#lib/constants/festival.js';
	import { m } from '#lib/paraglide/messages.js';
	import { canAwardQuest, canManageQuest } from '#lib/utils/permissions.js';

	import type { PageProps } from './$types';

	import AwardForm from './components/AwardForm.svelte';
	import PlayerPicker from './components/PlayerPicker.svelte';
	import QuestAwardsFeed from './components/QuestAwardsFeed.svelte';

	let { data }: PageProps = $props();
	let canAward = $derived(canAwardQuest(data.user));
	let canManage = $derived(canManageQuest(data.user));

	const configQuery = createQuery(() => getPublicConfigOptions());
	let maxAward = $derived((configQuery.data ?? FALLBACK_CONFIG).quest_max_award);

	let player = $state.raw<QuestPlayerDto | null>(null);

	function handlePick(picked: QuestPlayerDto) {
		player = picked;
	}
</script>

<svelte:head>
	<title>{m.document_title({ title: m.tool_quest() })}</title>
</svelte:head>

<div class="mx-auto flex w-full max-w-2xl flex-col gap-5">
	{#if canAward}
		<SectionIntro description={m.tool_quest_description()} />

		<Card.Root class="w-full max-w-none gap-4 rounded-2xl p-4 sm:p-6">
			{#if player}
				<!-- Keyed so a second player starts from an empty form and a fresh award ID. -->
				{#key player.id}
					<AwardForm {player} {maxAward} onDone={() => (player = null)} />
				{/key}
			{:else}
				<PlayerPicker onPick={handlePick} />
			{/if}
		</Card.Root>
	{/if}

	<section class="flex flex-col gap-3" aria-labelledby="quest-history-title">
		<h2 id="quest-history-title" class="text-section text-foreground">
			{#if canManage}
				{m.quest_tool_history_all_title()}
			{:else}
				{m.quest_tool_history_title()}
			{/if}
		</h2>
		<QuestAwardsFeed showAwarder={canManage} />
	</section>
</div>
