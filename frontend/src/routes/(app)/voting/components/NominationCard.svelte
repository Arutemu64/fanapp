<script lang="ts">
	import type { NominationVotingDTO } from '$lib/types/nominations';
	import { Card, Badge } from 'flowbite-svelte';
	import { ArrowRightOutline, CheckCircleSolid } from 'flowbite-svelte-icons';
	import { pluralize } from '$lib/utils/formatters';

	interface Props {
		nomination: NominationVotingDTO;
	}

	let { nomination }: Props = $props();
</script>

<!-- Whole card is the link: bigger tap target on mobile, single clear action. -->
<Card
	href="/voting/{nomination.code}"
	class={[
		'relative flex w-full max-w-none flex-col overflow-hidden p-4 transition-[box-shadow,border-color,background-color] hover:shadow-md',
		nomination.user_vote ? 'ring-2 ring-green-600 dark:ring-green-500' : ''
	]}
>
	<!-- Watermark code -->
	<div
		class="pointer-events-none absolute right-2 bottom-0 text-7xl leading-none font-black text-gray-900/[0.04] uppercase select-none dark:text-white/[0.06]"
		aria-hidden="true"
	>
		{nomination.code}
	</div>

	<!-- Header row mirrors ParticipantCard: reserved min-h keeps the title fixed whether voted or not. -->
	<div class="relative z-10 mb-2 flex min-h-6 items-center justify-between gap-2">
		<span class="text-xs font-semibold tracking-wide text-gray-500 dark:text-gray-400">
			{nomination.participants_count}
			{pluralize(nomination.participants_count, 'участник', 'участника', 'участников')}
		</span>

		{#if nomination.user_vote}
			<Badge color="green" border class="shrink-0">
				<span class="flex items-center gap-1">
					<CheckCircleSolid class="h-3.5 w-3.5" />
					Голос учтён
				</span>
			</Badge>
		{/if}
	</div>

	<!-- Title -->
	<h3 class="relative z-10 flex-1 text-base leading-snug font-bold text-gray-900 dark:text-white">
		{nomination.title}
	</h3>

	<!-- Footer row: navigation cue. Arrow signals this navigates, not votes directly. -->
	<div
		class="relative z-10 mt-3 flex items-center justify-end gap-1.5 border-t border-gray-100 pt-3 text-sm font-medium text-primary-600 dark:border-gray-700 dark:text-primary-400"
	>
		{nomination.user_vote ? 'Перейти' : 'Голосовать'}
		<ArrowRightOutline class="h-3.5 w-3.5" />
	</div>
</Card>
