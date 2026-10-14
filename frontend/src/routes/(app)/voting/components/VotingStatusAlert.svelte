<script lang="ts">
	import { resolve } from '$app/paths';
	import { AlertCircle } from '@lucide/svelte';

	import type { GetVotingStateOutput, VotingStatus } from '#lib/api/generated/index.js';

	import * as Alert from '#lib/components/ui/alert/index.js';
	import { m } from '#lib/paraglide/messages.js';

	interface Props {
		votingState?: GetVotingStateOutput;
		class?: string;
	}

	let { votingState, class: className = '' }: Props = $props();

	// Closed voting reads as an error; a missing login/ticket is a warning the user
	// can act on. Both map to Alert's semantic variants (tinting lives there now).
	let variant: Alert.AlertVariant = $derived(
		votingState?.status === 'disabled' ? 'destructive' : 'warning'
	);

	// Centralize banner copy so list and nomination pages stay consistent.
	function getStatusMessage(status: VotingStatus): string {
		switch (status) {
			case 'open':
				return m.voting_status_open();
			case 'not_authenticated':
				return m.voting_status_login();
			case 'no_ticket':
				return m.voting_status_link_ticket();
			case 'disabled':
				return m.voting_status_closed();
			default:
				return '';
		}
	}
</script>

{#if votingState && votingState.status !== 'open'}
	<Alert.Root {variant} class={className}>
		<AlertCircle class="shrink-0" />
		<Alert.Description class="flex items-center gap-1">
			<span>{getStatusMessage(votingState.status)}</span>
			{#if votingState.status === 'no_ticket'}
				<a href={resolve('profile/ticket')} class="font-medium underline"
					>{m.voting_link_ticket_link()}</a
				>
			{/if}
		</Alert.Description>
	</Alert.Root>
{/if}
