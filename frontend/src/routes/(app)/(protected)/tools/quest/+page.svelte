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
	// Kept across players: a station awards the same task over and over.
	let amount = $state('');
	let message = $state('');
	// Only a return from the form moves focus; the first visit leaves it alone.
	let returnedFromForm = $state(false);

	function handlePick(picked: QuestPlayerDto) {
		player = picked;
	}

	function handleDone() {
		player = null;
		returnedFromForm = true;
	}
</script>

<svelte:head>
	<title>{m.document_title({ title: m.tool_quest() })}</title>
</svelte:head>

<div class="mx-auto flex w-full max-w-2xl flex-col gap-5">
	{#if canAward}
		<SectionIntro description={m.tool_quest_description()} />

		<Card.Root class="w-full max-w-none gap-4 p-4 sm:p-6">
			{#if player}
				<!-- Keyed so a second player gets a fresh award ID and cleared errors. -->
				{#key player.id}
					<AwardForm {player} {maxAward} bind:amount bind:message onDone={handleDone} />
				{/key}
			{:else}
				<PlayerPicker onPick={handlePick} focusOnMount={returnedFromForm} />
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
