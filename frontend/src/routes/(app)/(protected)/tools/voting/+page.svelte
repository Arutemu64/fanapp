<script lang="ts">
	import type { components } from '$lib/api/schema';

	import { createApiClient } from '$lib/api';
	import BackLink from '$lib/components/BackLink.svelte';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import SectionIntro from '$lib/components/SectionIntro.svelte';
	import { getToastService } from '$lib/services/toasts.svelte';
	import { pluralize } from '$lib/utils/formatters';
	import { Alert, Badge, Button, Card, Label, Spinner } from 'flowbite-svelte';
	import { AwardOutline, GiftBoxOutline, UsersGroupOutline } from 'flowbite-svelte-icons';
	import { untrack } from 'svelte';

	import type { PageProps } from './$types';

	type NominationContender = components['schemas']['NominationContenderDTO'];
	type Winner = components['schemas']['UserBaseDTO'];

	let { data }: PageProps = $props();
	const client = createApiClient();
	const toastService = getToastService();

	let nominations = $derived<NominationContender[]>(data.dashboard.nominations);

	let votingStart = $state(untrack(() => toLocalInput(data.dashboard.voting_start)));
	let votingEnd = $state(untrack(() => toLocalInput(data.dashboard.voting_end)));
	let isSaving = $state(false);

	// Seeded from the dashboard, then refreshed from each draw's response, so the
	// displayed pool tracks who is currently eligible even as people finish voting.
	let poolSize = $state(untrack(() => data.dashboard.contest_pool_size));
	let isDrawing = $state(false);
	let winner = $state<Winner | null>(null);
	let hasDrawn = $state(false);
	let drawError = $state('');

	let canDraw = $derived(poolSize > 0);

	function toLocalInput(iso: string | null): string {
		if (!iso) return '';
		const d = new Date(iso);
		const offset = d.getTimezoneOffset();
		const local = new Date(d.getTime() - offset * 60_000);
		return local.toISOString().slice(0, 16);
	}

	function fromLocalInput(value: string): string | null {
		if (!value) return null;
		return new Date(value).toISOString();
	}

	async function handleSave() {
		isSaving = true;
		try {
			const { error, response } = await client.PATCH('/voting/dashboard', {
				body: {
					voting_start: fromLocalInput(votingStart),
					voting_end: fromLocalInput(votingEnd)
				}
			});

			if (error || !response.ok) {
				if (response.status === 403) {
					toastService.add('У тебя нет доступа к управлению голосованием', 'error');
				} else {
					toastService.add('Не удалось сохранить время голосования', 'error');
				}
				return;
			}

			toastService.add('Время голосования обновлено', 'success');
		} catch (err) {
			console.error('Voting time range save failed:', err);
			toastService.add('Не удалось сохранить время голосования', 'error');
		} finally {
			isSaving = false;
		}
	}

	async function handleClear() {
		votingStart = '';
		votingEnd = '';
		await handleSave();
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
	description="Задавай период голосования, следи за лидерами номинаций и разыгрывай приз среди тех, кто проголосовал во всех номинациях."
/>

<div class="mx-auto w-full max-w-2xl space-y-5">
	<Card class="w-full max-w-none space-y-4 rounded-2xl p-4 sm:p-6">
		<h2 class="text-lg font-semibold text-gray-900 dark:text-white">Период голосования</h2>

		<p class="text-xs leading-5 text-gray-500 dark:text-gray-300">
			Посетители смогут голосовать только в указанный период.
		</p>

		<div class="grid gap-4 sm:grid-cols-2">
			<div>
				<Label for="voting-start" class="mb-1.5">Начало</Label>
				<input
					id="voting-start"
					type="datetime-local"
					bind:value={votingStart}
					disabled={isSaving}
					class="block w-full rounded-lg border border-gray-300 bg-gray-50 p-2.5 text-sm text-gray-900 focus:border-primary-500 focus:ring-primary-500 disabled:opacity-50 dark:border-gray-600 dark:bg-gray-700 dark:text-white dark:placeholder-gray-400 dark:focus:border-primary-500 dark:focus:ring-primary-500"
				/>
			</div>
			<div>
				<Label for="voting-end" class="mb-1.5">Конец</Label>
				<input
					id="voting-end"
					type="datetime-local"
					bind:value={votingEnd}
					disabled={isSaving}
					class="block w-full rounded-lg border border-gray-300 bg-gray-50 p-2.5 text-sm text-gray-900 focus:border-primary-500 focus:ring-primary-500 disabled:opacity-50 dark:border-gray-600 dark:bg-gray-700 dark:text-white dark:placeholder-gray-400 dark:focus:border-primary-500 dark:focus:ring-primary-500"
				/>
			</div>
		</div>

		<div class="flex flex-wrap gap-2">
			<Button
				type="button"
				color="primary"
				class="min-h-11 justify-center"
				disabled={isSaving}
				onclick={handleSave}
			>
				{#if isSaving}
					<Spinner size="4" class="mr-2 fill-white" />
				{/if}
				Сохранить
			</Button>
			<Button
				type="button"
				color="alternative"
				class="min-h-11 justify-center"
				disabled={isSaving || (!votingStart && !votingEnd)}
				onclick={handleClear}
			>
				Сбросить
			</Button>
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
