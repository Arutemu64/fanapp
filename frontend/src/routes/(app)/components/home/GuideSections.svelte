<script lang="ts">
	import Ticket from '@lucide/svelte/icons/ticket';

	import MenuRow from '#lib/components/MenuRow.svelte';
	import { guideArticles } from '#lib/data/guideArticles.js';
	import { m } from '#lib/paraglide/messages.js';
	import { trackEvent } from '#lib/services/analytics.js';

	import type { FestivalPhase } from './festivalPhase';

	interface Props {
		phase: FestivalPhase;
	}

	let { phase }: Props = $props();

	const importantArticles = guideArticles.filter((article) => article.section === 'important');
	const activityArticles = guideArticles.filter((article) => article.section === 'activities');

	let showTickets = $derived(phase === 'before');
</script>

{#snippet articleCards(articles: typeof guideArticles)}
	{#each articles as article (article.slug)}
		<MenuRow
			href={`guide/${article.slug}`}
			label={article.title}
			description={article.description}
			icon={article.icon}
			variant="card"
			chevron
		/>
	{/each}
{/snippet}

<div class="flex flex-col gap-10">
	<section aria-labelledby="guide-important" class="flex flex-col gap-3">
		<h2 id="guide-important" class="px-1 text-section text-foreground">
			{m.guide_important_heading()}
		</h2>
		<div class="grid gap-2 min-[22rem]:grid-cols-2">
			{@render articleCards(importantArticles)}
			{#if showTickets}
				<MenuRow
					externalHref="https://fancom.info/pages/Tickets"
					newTab
					onclick={() => trackEvent('outbound-link', { target: 'tickets' })}
					label={m.guide_tickets()}
					description={m.guide_tickets_description()}
					icon={Ticket}
					variant="card"
				/>
			{/if}
		</div>
	</section>

	<section aria-labelledby="guide-activities" class="flex flex-col gap-3">
		<h2 id="guide-activities" class="px-1 text-section text-foreground">
			{m.guide_activities_heading()}
		</h2>
		<div class="grid gap-2 min-[22rem]:grid-cols-2 xl:grid-cols-3">
			{@render articleCards(activityArticles)}
		</div>
	</section>
</div>
