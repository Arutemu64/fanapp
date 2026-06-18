<script lang="ts">
	import type { NominationVotingDTO } from '$lib/types/nominations';
	import { Card, Badge } from 'flowbite-svelte';
	import { ArrowRightOutline, CheckCircleSolid } from 'flowbite-svelte-icons';

	interface Props {
		nomination: NominationVotingDTO;
	}

	let { nomination }: Props = $props();
</script>

<!-- Whole card is the link: bigger tap target on mobile, single clear action. -->
<Card
	href="/voting/{nomination.code}"
	class={[
		'flex w-full max-w-none flex-col p-4 transition-[box-shadow,border-color,background-color] hover:shadow-md',
		nomination.user_vote ? 'ring-2 ring-green-600 dark:ring-green-500' : ''
	]}
>
	<!-- Header row: badge only when voted; omit entirely when unvoted to avoid empty space. -->
	{#if nomination.user_vote}
		<div class="mb-2 flex items-center justify-end">
			<Badge color="green" border class="shrink-0">
				<span class="flex items-center gap-1">
					<CheckCircleSolid class="h-3.5 w-3.5" />
					Голос учтён
				</span>
			</Badge>
		</div>
	{/if}

	<!-- Title -->
	<h3 class="flex-1 text-base leading-snug font-bold text-gray-900 dark:text-white">
		{nomination.title}
	</h3>

	<!-- Footer row: navigation cue. Arrow signals this navigates, not votes directly. -->
	<div
		class="mt-3 flex items-center justify-end gap-1.5 border-t border-gray-100 pt-3 text-sm font-medium text-primary-600 dark:border-gray-700 dark:text-primary-400"
	>
		{nomination.user_vote ? 'Перейти' : 'Голосовать'}
		<ArrowRightOutline class="h-3.5 w-3.5" />
	</div>
</Card>
