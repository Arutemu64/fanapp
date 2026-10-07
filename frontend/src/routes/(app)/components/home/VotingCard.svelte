<script lang="ts">
	import type { VotingStatus } from '$lib/api/generated';

	import { Button } from '$lib/components/ui/button';
	import { LOGIN_NEXT_PARAM } from '$lib/utils/auth';
	import { ThumbsUp } from '@lucide/svelte';

	interface Props {
		status: VotingStatus;
	}

	let { status }: Props = $props();

	interface VotingAction {
		description: string;
		label: string;
		href: string;
	}

	// The card shows only while the window is open, so 'disabled' here means the
	// client clock ran ahead of the server's: send them to voting, whose own
	// banner carries the server's verdict.
	let action = $derived.by<VotingAction>(() => {
		switch (status) {
			case 'not_authenticated':
				return {
					description: 'Чтобы голосовать, войди в аккаунт и привяжи билет.',
					label: 'Войти',
					href: `/login?${LOGIN_NEXT_PARAM}=/voting`
				};
			case 'no_ticket':
				return {
					description: 'Чтобы голосовать, привяжи билет.',
					label: 'Привязать билет',
					href: '/profile/ticket'
				};
			default:
				return {
					description: 'Выбери любимых участников в номинациях.',
					label: 'Голосовать',
					href: '/voting'
				};
		}
	});
</script>

<section
	aria-labelledby="voting-heading"
	class="flex flex-col gap-4 rounded-2xl border border-primary-200 bg-primary-50 p-4 shadow-sm sm:flex-row sm:items-center sm:p-5 dark:border-primary-800/50 dark:bg-primary-900/20"
>
	<div class="flex min-w-0 flex-1 items-center gap-4">
		<span
			class="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-primary/15 text-primary"
		>
			<ThumbsUp class="size-6" aria-hidden="true" />
		</span>
		<div class="min-w-0 flex-1">
			<h2 id="voting-heading" class="text-base font-bold text-foreground sm:text-lg">
				Голосование открыто
			</h2>
			<p class="mt-1 text-sm leading-relaxed text-muted-foreground">{action.description}</p>
		</div>
	</div>
	<Button href={action.href} class="shrink-0">{action.label}</Button>
</section>
