<script lang="ts">
	import { resolve } from '$app/paths';
	import CircleAlert from '@lucide/svelte/icons/circle-alert';

	import type { GetVotingStatusOutput, VotingStatus } from '#lib/api/generated/index.js';

	import * as Alert from '#lib/components/ui/alert/index.js';
	import { m } from '#lib/paraglide/messages.js';

	interface Props {
		votingState?: GetVotingStatusOutput;
		class?: string;
	}

	let { votingState, class: className = '' }: Props = $props();

	let variant: Alert.AlertVariant = $derived(
		votingState?.status === 'disabled' ? 'destructive' : 'warning'
	);

	function getStatusMessage(status: VotingStatus): string {
		switch (status) {
			case 'open':
				return m.voting_status_open();
			case 'not_authenticated':
				return m.voting_status_login();
			case 'no_ticket':
				return m.voting_card_link_ticket();
			case 'disabled':
				return m.error_voting_closed();
			default:
				return '';
		}
	}
</script>

{#if votingState && votingState.status !== 'open'}
	<Alert.Root {variant} class={className}>
		<CircleAlert class="shrink-0" />
		<Alert.Description class="flex items-center gap-1">
			<span>{getStatusMessage(votingState.status)}</span>
			{#if votingState.status === 'no_ticket'}
				<a href={resolve('profile/ticket')} class="font-medium underline"
					>{m.ticket_link_action()}</a
				>
			{/if}
		</Alert.Description>
	</Alert.Root>
{/if}
