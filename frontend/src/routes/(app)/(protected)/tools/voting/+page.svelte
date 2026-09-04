<script lang="ts">
	import type { components } from '$lib/api/schema';

	import { createApiClient } from '$lib/api';
	import BackLink from '$lib/components/BackLink.svelte';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import SectionIntro from '$lib/components/SectionIntro.svelte';
	import * as Alert from '$lib/components/ui/alert';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import * as Card from '$lib/components/ui/card';
	import * as Field from '$lib/components/ui/field';
	import { Input } from '$lib/components/ui/input';
	import { Spinner } from '$lib/components/ui/spinner';
	import { getToastService } from '$lib/services/toasts.svelte';
	import { pluralize } from '$lib/utils/formatters';
	import { AlertCircle, Award, Gift, Users } from '@lucide/svelte';
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

<div class="mx-auto flex w-full max-w-2xl flex-col gap-5">
	<Card.Root class="flex w-full max-w-none flex-col gap-4 rounded-2xl p-4 sm:p-6">
		<h2 class="text-lg font-semibold text-foreground">Период голосования</h2>

		<p class="text-xs leading-5 text-muted-foreground">
			Посетители смогут голосовать только в указанный период.
		</p>

		<Field.FieldGroup class="grid gap-4 sm:grid-cols-2">
			<Field.Field>
				<Field.FieldLabel for="voting-start">Начало</Field.FieldLabel>
				<Input
					id="voting-start"
					type="datetime-local"
					bind:value={votingStart}
					disabled={isSaving}
				/>
			</Field.Field>
			<Field.Field>
				<Field.FieldLabel for="voting-end">Конец</Field.FieldLabel>
				<Input id="voting-end" type="datetime-local" bind:value={votingEnd} disabled={isSaving} />
			</Field.Field>
		</Field.FieldGroup>

		<div class="flex flex-wrap gap-2">
			<Button
				type="button"
				class="min-h-11 justify-center"
				disabled={isSaving}
				onclick={handleSave}
			>
				{#if isSaving}
					<Spinner data-icon="inline-start" />
				{/if}
				Сохранить
			</Button>
			<Button
				type="button"
				variant="outline"
				class="min-h-11 justify-center"
				disabled={isSaving || (!votingStart && !votingEnd)}
				onclick={handleClear}
			>
				Сбросить
			</Button>
		</div>
	</Card.Root>

	<Card.Root class="flex w-full max-w-none flex-col gap-4 rounded-2xl p-4 sm:p-6">
		<div class="flex items-center gap-2">
			<Gift class="size-5 text-primary" aria-hidden="true" />
			<h2 class="text-lg font-semibold text-foreground">Розыгрыш приза</h2>
		</div>
		<p class="text-xs leading-5 text-muted-foreground">
			Случайный участник среди тех, кто проголосовал во всех номинациях.
		</p>

		<div class="flex items-center gap-2 text-sm text-muted-foreground">
			<Users class="size-4" aria-hidden="true" />
			<span>
				В розыгрыше: {poolSize}
				{pluralize(poolSize, 'участник', 'участника', 'участников')}
			</span>
		</div>

		{#if drawError}
			<Alert.Root variant="destructive">
				<AlertCircle class="size-4" />
				<Alert.Description>{drawError}</Alert.Description>
			</Alert.Root>
		{/if}

		{#if hasDrawn}
			<!-- aria-live so the drawn name is announced to screen readers, which
			     otherwise get no signal that the button did anything. -->
			<div aria-live="polite" role="status">
				{#if winner}
					<div class="flex items-center gap-3 rounded-xl bg-primary/10 p-3">
						<Award class="size-6 shrink-0 text-primary" aria-hidden="true" />
						<div class="min-w-0">
							<p class="text-xs text-muted-foreground">Победитель</p>
							<p class="truncate text-base font-semibold text-foreground">
								{winner.username}
							</p>
						</div>
					</div>
				{:else}
					<p class="text-sm text-muted-foreground">
						Пока некого разыгрывать — никто не проголосовал во всех номинациях.
					</p>
				{/if}
			</div>
		{/if}

		<Button
			type="button"
			class="min-h-11 w-full justify-center sm:w-auto"
			disabled={isDrawing || !canDraw}
			onclick={handleDraw}
		>
			{#if isDrawing}
				<Spinner data-icon="inline-start" />
				Разыгрываем…
			{:else}
				{hasDrawn ? 'Разыграть ещё раз' : 'Разыграть'}
			{/if}
		</Button>
		{#if !canDraw}
			<p class="text-xs text-muted-foreground">
				Кнопка станет активной, когда кто-нибудь проголосует во всех номинациях.
			</p>
		{/if}
	</Card.Root>

	<Card.Root class="flex w-full max-w-none flex-col gap-4 rounded-2xl p-4 sm:p-6">
		<div class="flex items-center gap-2">
			<Award class="size-5 text-primary" aria-hidden="true" />
			<h2 class="text-lg font-semibold text-foreground">Лидеры номинаций</h2>
		</div>

		{#if nominations.length > 0}
			<ul class="flex flex-col gap-3">
				{#each nominations as nomination (nomination.id)}
					<li class="border-b border-border pb-3 last:border-0 last:pb-0">
						<p class="text-sm font-medium text-foreground">{nomination.title}</p>
						{#if nomination.leader}
							<div class="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1">
								<span class="text-sm text-muted-foreground">
									{nomination.leader.title}
								</span>
								<Badge>
									{nomination.leader.votes_count}
									{pluralize(nomination.leader.votes_count, 'голос', 'голоса', 'голосов')}
									из {nomination.total_votes}
								</Badge>
							</div>
						{:else}
							<p class="mt-1 text-xs text-muted-foreground">Голосов пока нет</p>
						{/if}
					</li>
				{/each}
			</ul>
		{:else}
			<EmptyState
				icon={Users}
				title="Нет номинаций для голосования"
				message="Появятся после импорта косплей-конкурса"
			/>
		{/if}
	</Card.Root>
</div>
