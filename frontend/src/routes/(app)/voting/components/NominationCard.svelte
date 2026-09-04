<script lang="ts">
	import type { NominationVotingDTO } from '$lib/types/nominations';

	import { resolve } from '$app/paths';
	import { Badge } from '$lib/components/ui/badge';
	import * as Card from '$lib/components/ui/card';
	import { pluralize } from '$lib/utils/formatters';
	import { ArrowRight, CheckCircle2 } from '@lucide/svelte';

	interface Props {
		nomination: NominationVotingDTO;
	}

	let { nomination }: Props = $props();
</script>

<!--
	Stretched-link card, not a card wrapped in <a>: wrapping the whole card in an
	anchor makes a screen reader announce every scrap of text inside as one giant
	link name and buries the heading. Instead the anchor sits on the title only
	(so its accessible name is just the nomination) and its ::after overlay covers
	the card to keep the whole surface tappable. `relative` here anchors that
	overlay; `has-[a:focus-visible]` lifts the keyboard ring back onto the card.
-->
<Card.Root
	as="article"
	class={[
		'relative flex w-full max-w-none flex-col p-4 shadow-sm transition-[box-shadow,border-color,background-color] hover:shadow-md has-[a:focus-visible]:ring-2 has-[a:focus-visible]:ring-ring',
		nomination.user_vote ? 'ring-2 ring-success' : ''
	]}
>
	<!-- Header row mirrors ParticipantCard: reserved min-h keeps the title fixed whether voted or not. -->
	<div class="mb-2 flex min-h-6 items-center justify-between gap-2">
		<span class="text-xs font-semibold tracking-wide text-muted-foreground">
			{nomination.participants_count}
			{pluralize(nomination.participants_count, 'участник', 'участника', 'участников')}
		</span>

		{#if nomination.user_vote}
			<Badge variant="outline" class="shrink-0 border-success/30 bg-success/10 text-success">
				<span class="flex items-center gap-1">
					<CheckCircle2 class="size-3.5" />
					Голос учтён
				</span>
			</Badge>
		{/if}
	</div>

	<h3 class="flex-1 text-base leading-snug font-bold break-words text-foreground">
		<a
			href={resolve(`/voting/${nomination.code}`)}
			class="after:absolute after:inset-0 after:content-[''] focus-visible:outline-none"
		>
			{nomination.title}
		</a>
	</h3>

	<!-- Footer row: navigation cue. Arrow signals this navigates, not votes directly. -->
	<div
		class="mt-3 flex items-center justify-end gap-1.5 border-t border-border pt-3 text-sm font-medium text-primary"
	>
		{nomination.user_vote ? 'Перейти' : 'Голосовать'}
		<ArrowRight class="size-3.5" />
	</div>
</Card.Root>
