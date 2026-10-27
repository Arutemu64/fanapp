<script lang="ts">
	import { resolve } from '$app/paths';
	import ArrowRight from '@lucide/svelte/icons/arrow-right';
	import CircleCheck from '@lucide/svelte/icons/circle-check';

	import type { NominationVotingDto } from '#lib/api/generated/index.js';

	import { Badge } from '#lib/components/ui/badge/index.js';
	import * as Card from '#lib/components/ui/card/index.js';
	import { m } from '#lib/paraglide/messages.js';

	interface Props {
		nomination: NominationVotingDto;
	}

	let { nomination }: Props = $props();
</script>

<Card.Root
	as="article"
	class={[
		'relative flex w-full max-w-none flex-col p-4 shadow-sm transition-[box-shadow,border-color,background-color] hover:bg-muted/50 has-[a:focus-visible]:ring-2 has-[a:focus-visible]:ring-ring',
		nomination.user_vote ? 'ring-2 ring-success' : ''
	]}
>
	<div class="mb-2 flex min-h-6 items-center justify-between gap-2">
		<span class="text-xs font-semibold tracking-wide text-muted-foreground">
			{m.participants_count({ count: nomination.participants_count })}
		</span>

		{#if nomination.user_vote}
			<Badge variant="outline" class="shrink-0 border-success/30 bg-success/10 text-success">
				<span class="flex items-center gap-1">
					<CircleCheck class="size-3.5" />
					{m.voting_vote_counted()}
				</span>
			</Badge>
		{/if}
	</div>

	<h3 class="flex-1 text-base leading-snug font-bold wrap-break-word text-foreground">
		<a
			href={resolve(`voting/${nomination.code}`)}
			class="after:absolute after:inset-0 after:content-[''] focus-visible:outline-none"
		>
			{nomination.title}
		</a>
	</h3>

	<div
		class="mt-3 flex items-center justify-end gap-1.5 border-t border-border pt-3 text-sm font-medium text-primary"
	>
		{nomination.user_vote ? m.common_go() : m.voting_action()}
		<ArrowRight class="size-3.5" />
	</div>
</Card.Root>
