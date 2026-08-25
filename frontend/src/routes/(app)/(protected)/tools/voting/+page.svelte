<script lang="ts">
	import type { components } from '$lib/api/schema';

	import { createApiClient } from '$lib/api';
	import BackLink from '$lib/components/BackLink.svelte';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import SectionIntro from '$lib/components/SectionIntro.svelte';
	import { getToastService } from '$lib/services/toasts.svelte';
	import { pluralize } from '$lib/utils/formatters';
	import { Alert, Badge, Button, Card, Spinner, Toggle } from 'flowbite-svelte';
	import { AwardOutline, GiftBoxOutline, UsersGroupOutline } from 'flowbite-svelte-icons';
	import { untrack } from 'svelte';

	import type { PageProps } from './$types';

	type NominationContender = components['schemas']['NominationContenderDTO'];
	type Winner = components['schemas']['UserBaseDTO'];

	let { data }: PageProps = $props();
	const client = createApiClient();
	const toastService = getToastService();

	let nominations = $derived<NominationContender[]>(data.dashboard.nominations);

	// The toggle owns its state locally so it can flip instantly and roll back on a
	// failed save, rather than waiting for a full reload of the dashboard.
	let votingEnabled = $state(untrack(() => data.dashboard.voting_enabled));
	let isTogglingVoting = $state(false);

	// Seeded from the dashboard, then refreshed from each draw's response, so the
	// displayed pool tracks who is currently eligible even as people finish voting.
	let poolSize = $state(untrack(() => data.dashboard.contest_pool_size));
	let isDrawing = $state(false);
	let winner = $state<Winner | null>(null);
	let hasDrawn = $state(false);
	let drawError = $state('');

	let canDraw = $derived(poolSize > 0);

	async function handleVotingToggle(next: boolean) {
		isTogglingVoting = true;
		try {
			const { error, response } = await client.PATCH('/voting/dashboard', {
				body: { enabled: next }
			});

			if (error || !response.ok) {
				// Roll back the optimistic flip so the switch never lies about the
				// real server state.
				votingEnabled = !next;
				if (response.status === 403) {
					toastService.add('У тебя нет доступа к управлению голосованием', 'error');
				} else {
					toastService.add('Не удалось изменить статус голосования', 'error');
				}
				return;
			}

			toastService.add(next ? 'Голосование включено' : 'Голосование выключено', 'success');
		} catch (err) {
			votingEnabled = !next;
			console.error('Voting toggle failed:', err);
			toastService.add('Не удалось изменить статус голосования', 'error');
		} finally {
			isTogglingVoting = false;
		}
	}

	async function handleDraw() {
		isDrawing = true;
		drawError = '';
		try {
			const { data: result, error, response } = await client.POST('/voting/contest/draw', {});

			if (error || !response.ok || !result) {
				if (response.status === 403) {
					drawError = 'У тебя нет доступа к розыгрышу';
				} else {
					drawError = 'Не удалось провести розыгрыш';
				}
				return;
			}

			// The draw is read-only: the server draws from the live pool and returns
			// both the winner and the current pool size, so there is nothing to
			// refetch — trust the response.
			poolSize = result.pool_size;
			winner = result.winner;
			hasDrawn = true;
		} catch (err) {
			console.error('Contest draw failed:', err);
			drawError = 'Не удалось провести розыгрыш';
		} finally {
			isDrawing = false;
		}
	}
</script>

<svelte:head>
	<title>Голосование · ФАН ФАН</title>
</svelte:head>

<BackLink href="/tools" label="Назад к инструментам" />

<SectionIntro
	description="Включай голосование, следи за лидерами номинаций и разыгрывай приз среди тех, кто проголосовал во всех номинациях."
/>

<div class="mx-auto w-full max-w-2xl space-y-5">
	<Card class="w-full max-w-none space-y-3 rounded-2xl p-4 sm:p-6">
		<h2 class="text-lg font-semibold text-gray-900 dark:text-white">Статус</h2>

		<div class="flex items-start justify-between gap-3">
			<div class="min-w-0">
				<h3 class="text-base font-medium text-gray-900 dark:text-white">Голосование активно</h3>
				<p class="mt-1 text-xs leading-5 text-gray-500 dark:text-gray-300">
					Если отключить, посетители временно не смогут голосовать.
				</p>
			</div>
			<div class="flex shrink-0 items-center gap-2">
				{#if isTogglingVoting}
					<Spinner size="4" />
				{/if}
				<Toggle
					bind:checked={votingEnabled}
					color="primary"
					disabled={isTogglingVoting}
					onchange={(event) => handleVotingToggle(event.currentTarget.checked)}
				/>
			</div>
		</div>
	</Card>

	<Card class="w-full max-w-none space-y-4 rounded-2xl p-4 sm:p-6">
		<div class="flex items-center gap-2">
			<GiftBoxOutline class="h-5 w-5 text-primary-600 dark:text-primary-400" aria-hidden="true" />
			<h2 class="text-lg font-semibold text-gray-900 dark:text-white">Розыгрыш приза</h2>
		</div>
		<p class="text-xs leading-5 text-gray-500 dark:text-gray-300">
			Случайный участник среди тех, кто проголосовал во всех номинациях.
		</p>

		<div class="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-300">
			<UsersGroupOutline class="h-4 w-4" aria-hidden="true" />
			<span>
				В розыгрыше: {poolSize}
				{pluralize(poolSize, 'участник', 'участника', 'участников')}
			</span>
		</div>

		{#if drawError}
			<Alert color="red">{drawError}</Alert>
		{/if}

		{#if hasDrawn}
			<!-- aria-live so the drawn name is announced to screen readers, which
			     otherwise get no signal that the button did anything. -->
			<div aria-live="polite" role="status">
				{#if winner}
					<div class="flex items-center gap-3 rounded-xl bg-primary-50 p-3 dark:bg-primary-900/20">
						<AwardOutline
							class="h-6 w-6 shrink-0 text-primary-600 dark:text-primary-400"
							aria-hidden="true"
						/>
						<div class="min-w-0">
							<p class="text-xs text-gray-500 dark:text-gray-400">Победитель</p>
							<p class="truncate text-base font-semibold text-gray-900 dark:text-white">
								{winner.username}
							</p>
						</div>
					</div>
				{:else}
					<p class="text-sm text-gray-500 dark:text-gray-400">
						Пока некого разыгрывать — никто не проголосовал во всех номинациях.
					</p>
				{/if}
			</div>
		{/if}

		<Button
			type="button"
			color="primary"
			class="min-h-11 w-full justify-center sm:w-auto"
			disabled={isDrawing || !canDraw}
			onclick={handleDraw}
		>
			{#if isDrawing}
				<Spinner size="4" class="mr-2 fill-white" />
				Разыгрываем…
			{:else}
				{hasDrawn ? 'Разыграть ещё раз' : 'Разыграть'}
			{/if}
		</Button>
		{#if !canDraw}
			<p class="text-xs text-gray-400 dark:text-gray-500">
				Кнопка станет активной, когда кто-нибудь проголосует во всех номинациях.
			</p>
		{/if}
	</Card>

	<Card class="w-full max-w-none space-y-4 rounded-2xl p-4 sm:p-6">
		<div class="flex items-center gap-2">
			<AwardOutline class="h-5 w-5 text-primary-600 dark:text-primary-400" aria-hidden="true" />
			<h2 class="text-lg font-semibold text-gray-900 dark:text-white">Лидеры номинаций</h2>
		</div>

		{#if nominations.length > 0}
			<ul class="space-y-3">
				{#each nominations as nomination (nomination.id)}
					<li class="border-b border-gray-100 pb-3 last:border-0 last:pb-0 dark:border-gray-800">
						<p class="text-sm font-medium text-gray-900 dark:text-white">{nomination.title}</p>
						{#if nomination.leader}
							<div class="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1">
								<span class="text-sm text-gray-600 dark:text-gray-300">
									{nomination.leader.title}
								</span>
								<Badge color="primary">
									{nomination.leader.votes_count}
									{pluralize(nomination.leader.votes_count, 'голос', 'голоса', 'голосов')}
									из {nomination.total_votes}
								</Badge>
							</div>
						{:else}
							<p class="mt-1 text-xs text-gray-400 dark:text-gray-500">Голосов пока нет</p>
						{/if}
					</li>
				{/each}
			</ul>
		{:else}
			<EmptyState
				icon={UsersGroupOutline}
				title="Нет номинаций для голосования"
				message="Появятся после импорта косплей-конкурса"
			/>
		{/if}
	</Card>
</div>
