<script lang="ts">
	import ThumbsUp from '@lucide/svelte/icons/thumbs-up';

	import type { VotingStatus } from '#lib/api/generated/index.js';

	import { Button } from '#lib/components/ui/button/index.js';
	import { m } from '#lib/paraglide/messages.js';
	import { LOGIN_NEXT_PARAM } from '#lib/utils/auth.js';

	interface Props {
		status: VotingStatus;
	}

	let { status }: Props = $props();

	interface VotingAction {
		description: string;
		label: string;
		href: string;
	}

	let action = $derived.by<VotingAction>(() => {
		switch (status) {
			case 'not_authenticated':
				return {
					description: m.voting_card_login_and_ticket(),
					label: m.common_login(),
					href: `/login?${LOGIN_NEXT_PARAM}=/voting`
				};
			case 'no_ticket':
				return {
					description: m.voting_card_link_ticket(),
					label: m.ticket_link_action(),
					href: '/profile/ticket'
				};
			default:
				return {
					description: m.voting_card_ready(),
					label: m.voting_action(),
					href: '/voting'
				};
		}
	});
</script>

<section
	aria-labelledby="voting-heading"
	class="@container rounded-2xl border border-primary-200 bg-primary-50 p-4 shadow-sm sm:p-5 dark:border-primary-800/50 dark:bg-primary-900/20"
>
	<div class="flex flex-col gap-4 @md:flex-row @md:items-center">
		<div class="flex min-w-0 flex-1 items-center gap-4">
			<span
				class="flex size-12 shrink-0 items-center justify-center rounded-xl bg-primary/15 text-primary"
			>
				<ThumbsUp class="size-6" aria-hidden="true" />
			</span>
			<div class="min-w-0 flex-1">
				<h2 id="voting-heading" class="text-section font-bold text-foreground">
					{m.voting_open_title()}
				</h2>
				<p class="mt-1 text-sm leading-relaxed text-muted-foreground">{action.description}</p>
			</div>
		</div>
		<Button href={action.href} class="shrink-0">{action.label}</Button>
	</div>
</section>
