<script lang="ts">
	import type { NominationFullDTO } from '$lib/types/nominations';
	import { Alert } from 'flowbite-svelte';
	import { CheckCircleSolid, ExclamationCircleSolid } from 'flowbite-svelte-icons';
	import SectionHeader from '$lib/components/SectionHeader.svelte';
	import NominationCard from '$lib/components/voting/NominationCard.svelte';
	import type { PageProps } from './$types';
	import type { VotingStatus } from '$lib/types/voting';

	let { data }: PageProps = $props();
	let nominations: NominationFullDTO[] = $derived(data.nominations);
	let votingStatus = $derived(data.votingStatus);

	function getStatusMessage(status: VotingStatus): string {
		switch (status) {
			case 'open':
				return 'Голосование открыто. Вы можете голосовать за участников.';
			case 'not_authenticated':
				return 'Войдите в аккаунт, чтобы участвовать в голосовании.';
			case 'no_ticket':
				return 'Для участия в голосовании необходим билет.';
			case 'disabled':
				return 'Голосование сейчас закрыто.';
			default:
				return '';
		}
	}

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

<svelte:head>
	<title>Голосование</title>
</svelte:head>

<SectionHeader title="Голосование" description="Выберите номинацию для голосования" />

{#if votingStatus}
	<Alert color={getStatusColor(votingStatus.status)} class="mb-4">
		<div class="flex items-center gap-2">
			{#if votingStatus.status === 'open'}
				<CheckCircleSolid class="h-5 w-5" />
			{:else}
				<ExclamationCircleSolid class="h-5 w-5" />
			{/if}
			<span>{getStatusMessage(votingStatus.status)}</span>
		</div>
	</Alert>
{/if}

{#if nominations.length === 0}
	<p class="text-gray-500 dark:text-gray-400">Нет доступных номинаций</p>
{:else}
	<div class="grid grid-cols-1 gap-3 sm:grid-cols-2 sm:gap-4 lg:grid-cols-3">
		{#each nominations as nomination (nomination.id)}
			<NominationCard {nomination} />
		{/each}
	</div>
{/if}
