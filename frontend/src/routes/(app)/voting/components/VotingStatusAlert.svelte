<script lang="ts">
	import type { GetVotingStateResult, VotingStatus } from '$lib/types/voting';

	import { resolve } from '$app/paths';
	import * as Alert from '$lib/components/ui/alert';
	import { AlertCircle } from '@lucide/svelte';

	interface Props {
		votingState?: GetVotingStateResult;
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
				return 'Голосование открыто. Ты можешь голосовать за участников.';
			case 'not_authenticated':
				return 'Войди в аккаунт, чтобы участвовать в голосовании.';
			case 'no_ticket':
				return 'Чтобы голосовать, привяжи билет.';
			case 'disabled':
				return 'Голосование сейчас закрыто.';
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
				<a href={resolve('/profile')} class="font-medium underline">Привязать билет</a>
			{/if}
		</Alert.Description>
	</Alert.Root>
{/if}
