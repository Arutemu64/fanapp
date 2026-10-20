<script lang="ts">
	import Ticket from '@lucide/svelte/icons/ticket';

	import MenuGroup from '#lib/components/MenuGroup.svelte';
	import MenuRow from '#lib/components/MenuRow.svelte';
	import { guideArticles } from '#lib/data/guideArticles.js';
	import { m } from '#lib/paraglide/messages.js';

	import type { FestivalPhase } from './festivalPhase';

	interface Props {
		phase: FestivalPhase;
	}

	let { phase }: Props = $props();

	const importantArticles = guideArticles.filter((article) => article.section === 'important');
	const activityArticles = guideArticles.filter((article) => article.section === 'activities');

	// Once the festival runs, a ticket is something a guest already holds, not something to buy.
	let showTickets = $derived(phase === 'before');
</script>

{#snippet articleRows(articles: typeof guideArticles)}
	{#each articles as article (article.slug)}
		<MenuRow
			href={`guide/${article.slug}`}
			label={article.title}
			description={article.description}
			icon={article.icon}
		/>
	{/each}
{/snippet}

<!-- The festival guide under Home's live cards: grouped rows that each lead somewhere,
     the phone-settings shape for "drill in"
     (https://developer.apple.com/design/human-interface-guidelines/lists-and-tables),
     so every target is a full-width tap. Each head sits over three times nearer its list than the block before it, so it
     reads as that list's title (https://practicaltypography.com/space-above-and-below.html).
     The date, times and address are the hero's, so they aren't repeated here. -->
<div class="flex flex-col gap-10">
	<section aria-labelledby="guide-important" class="flex flex-col gap-3">
		<h2 id="guide-important" class="px-1 text-section text-foreground">
			{m.guide_important_heading()}
		</h2>
		<MenuGroup>
			{@render articleRows(importantArticles)}
			{#if showTickets}
				<MenuRow
					externalHref="https://fancom.info/pages/Tickets"
					newTab
					label={m.guide_tickets()}
					description={m.guide_tickets_description()}
					icon={Ticket}
				/>
			{/if}
		</MenuGroup>
	</section>

	<section aria-labelledby="guide-activities" class="flex flex-col gap-3">
		<h2 id="guide-activities" class="px-1 text-section text-foreground">
			{m.guide_activities_heading()}
		</h2>
		<MenuGroup>
			{@render articleRows(activityArticles)}
		</MenuGroup>
	</section>
</div>
