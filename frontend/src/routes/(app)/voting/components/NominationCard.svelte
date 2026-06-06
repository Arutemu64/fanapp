<script lang="ts">
	import type { NominationVotingDTO } from '$lib/types/nominations';
	import { Card, Badge, Button } from 'flowbite-svelte';
	import {
		ArrowRightOutline,
		CheckCircleSolid,
		CheckOutline,
		ClockOutline
	} from 'flowbite-svelte-icons';

	interface Props {
		nomination: NominationVotingDTO;
	}

	let { nomination }: Props = $props();
</script>

<Card
	class={[
		'flex w-full max-w-none flex-col p-4 transition-[box-shadow,border-color,background-color]',
		nomination.user_vote
			? 'bg-green-50 ring-2 ring-green-400 dark:bg-green-950/20 dark:ring-green-500'
			: ''
	]}
>
	<!-- Header row: status badge -->
	<div class="mb-2 flex min-h-6 items-center justify-end">
		{#if nomination.user_vote}
			<Badge color="green" border class="shrink-0">
				<span class="flex items-center gap-1">
					<CheckCircleSolid class="h-3.5 w-3.5" />
					Голос учтён
				</span>
			</Badge>
		{:else}
			<Badge color="gray" border class="shrink-0">
				<span class="flex items-center gap-1">
					<ClockOutline class="h-3.5 w-3.5" />
					Ожидает
				</span>
			</Badge>
		{/if}
	</div>

	<!-- Title -->
	<h3 class="flex-1 text-base leading-snug font-bold text-gray-900 dark:text-white">
		{nomination.title}
	</h3>

	<!-- Footer row: CTA button -->
	<div
		class="mt-3 flex items-center justify-end border-t border-gray-100 pt-3 dark:border-gray-700"
	>
		<Button color="primary" href="/voting/{nomination.code}" size="sm">
			{#if nomination.user_vote}
				<ArrowRightOutline class="me-1.5 h-3.5 w-3.5" />
				Перейти
			{:else}
				<CheckOutline class="me-1.5 h-3.5 w-3.5" />
				Проголосовать
			{/if}
		</Button>
	</div>
</Card>
