<script lang="ts">
	import { Alert } from 'flowbite-svelte';
	import { ExclamationCircleSolid } from 'flowbite-svelte-icons';
	import type { GetVotingStateResult, VotingStatus } from '$lib/types/voting';

	interface Props {
		votingState?: GetVotingStateResult;
		class?: string;
	}

	let { votingState, class: className = '' }: Props = $props();

	// Centralize banner copy so list and nomination pages stay consistent.
	function getStatusMessage(status: VotingStatus): string {
		switch (status) {
			case 'open':
				return 'Голосование открыто. Ты можешь голосовать за участников.';
			case 'not_authenticated':
				return 'Войди в аккаунт, чтобы участвовать в голосовании.';
			case 'no_ticket':
				return 'Для участия в голосовании необходим билет.';
			case 'disabled':
				return 'Голосование сейчас закрыто.';
			default:
				return '';
		}
	}

	// Keep the banner color tied to the same backend status enum everywhere.
	function getStatusColor(status: VotingStatus): 'green' | 'yellow' | 'red' {
		switch (status) {
			case 'open':
				return 'green';
			case 'not_authenticated':
			case 'no_ticket':
				return 'yellow';
			case 'disabled':
				return 'red';
			default:
				return 'yellow';
		}
	}
</script>

{#if votingState && votingState.status !== 'open'}
	<Alert color={getStatusColor(votingState.status)} class={className}>
		<div class="flex items-center gap-2">
			<ExclamationCircleSolid class="h-5 w-5" />
			<span>{getStatusMessage(votingState.status)}</span>
		</div>
	</Alert>
{/if}
