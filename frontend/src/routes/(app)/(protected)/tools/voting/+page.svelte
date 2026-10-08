<script lang="ts">
	import { AlertCircle, Award, Users } from '@lucide/svelte';
	import { untrack } from 'svelte';

	import type { NominationContenderDto, UserBaseDto } from '#lib/api/generated/index.js';

	import { getApiErrorDetail } from '#lib/api/errors.js';
	import { drawVotingContestWinner, setVotingTimeRange } from '#lib/api/generated/index.js';
	import { createApiClient } from '#lib/api/index.js';
	import EmptyState from '#lib/components/EmptyState.svelte';
	import MenuGroup from '#lib/components/MenuGroup.svelte';
	import SectionIntro from '#lib/components/SectionIntro.svelte';
	import SettingsSection from '#lib/components/SettingsSection.svelte';
	import * as Alert from '#lib/components/ui/alert/index.js';
	import { Button } from '#lib/components/ui/button/index.js';
	import * as Field from '#lib/components/ui/field/index.js';
	import { Input } from '#lib/components/ui/input/index.js';
	import { Spinner } from '#lib/components/ui/spinner/index.js';
	import { getToastService } from '#lib/services/toasts.svelte.js';
	import {
		fromEventDateTimeLocal,
		pluralize,
		toEventDateTimeLocal
	} from '#lib/utils/formatters.js';

	import type { PageProps } from './$types';

	import ConfirmDialog from '../components/ConfirmDialog.svelte';

	let { data }: PageProps = $props();
	const client = createApiClient();
	const toastService = getToastService();

	let nominations = $derived<NominationContenderDto[]>(data.dashboard.nominations);

	// Edited on the venue clock like the festival dates in /tools/settings, so an
	// organiser in another timezone sets the window the visitors actually see.
	let votingStart = $state(untrack(() => toVenueInput(data.dashboard.voting_start)));
	let votingEnd = $state(untrack(() => toVenueInput(data.dashboard.voting_end)));
	let votingStartError = $state('');
	let votingEndError = $state('');
	let saveError = $state('');
	let isSaving = $state(false);
	// Whether a window is stored right now, so «Отключить» only offers itself when
	// there is something to switch off.
	let hasSavedRange = $state(untrack(() => data.dashboard.voting_start !== null));
	let clearConfirmOpen = $state(false);

	// Seeded from the dashboard, then refreshed from each draw's response, so the
	// displayed pool tracks who is currently eligible even as people finish voting.
	let poolSize = $state(untrack(() => data.dashboard.contest_pool_size));
	let isDrawing = $state(false);
	let winner = $state<UserBaseDto | null>(null);
	let hasDrawn = $state(false);
	let drawError = $state('');

	let canDraw = $derived(poolSize > 0);

	function toVenueInput(iso: string | null): string {
		if (!iso) return '';
		return toEventDateTimeLocal(iso);
	}

	function fromVenueInput(value: string): string | null {
		if (!value) return null;
		return fromEventDateTimeLocal(value);
	}

	// Mirrors the domain rule (AppSettings.set_voting_time_range): both bounds or
	// neither, and the end after the start. Checked here so the message lands
	// under the field instead of in a toast.
	function validateRange(): boolean {
		votingStartError = '';
		votingEndError = '';

		if (!votingStart && votingEnd) {
			votingStartError = 'Укажи начало голосования';
		}
		if (votingStart && !votingEnd) {
			votingEndError = 'Укажи конец голосования';
		}
		if (votingStart && votingEnd && votingEnd <= votingStart) {
			votingEndError = 'Конец должен быть позже начала';
		}

		return !votingStartError && !votingEndError;
	}

	function handleRangeInput() {
		saveError = '';
		// Re-check live only once an error is showing, so it clears as soon as the
		// field is fixed without nagging while the first value is typed.
		if (votingStartError || votingEndError) {
			validateRange();
		}
	}

	async function saveRange(): Promise<boolean> {
		isSaving = true;
		saveError = '';
		try {
			const { error, response } = await setVotingTimeRange({
				client,
				body: {
					voting_start: fromVenueInput(votingStart),
					voting_end: fromVenueInput(votingEnd)
				}
			});

			if (error || !response?.ok) {
				saveError = getApiErrorDetail(error) ?? 'Не удалось сохранить период голосования';
				return false;
			}

			hasSavedRange = votingStart !== '';
			return true;
		} finally {
			isSaving = false;
		}
	}

	async function handleSubmit(event: Event) {
		event.preventDefault();
		if (isSaving) return;
		if (!validateRange()) return;

		const saved = await saveRange();
		if (saved) {
			toastService.add('Период голосования сохранён', 'success');
		}
	}

	// Clearing closes voting for everyone at once, so it is confirmed first and
	// saved from the dialog rather than left as an edit to submit later.
	async function handleClear() {
		const previousStart = votingStart;
		const previousEnd = votingEnd;
		votingStart = '';
		votingEnd = '';
		votingStartError = '';
		votingEndError = '';

		const saved = await saveRange();
		if (saved) {
			toastService.add('Голосование отключено', 'success');
			return;
		}

		votingStart = previousStart;
		votingEnd = previousEnd;
	}

	async function handleDraw() {
		isDrawing = true;
		drawError = '';
		try {
			const { data: result, error, response } = await drawVotingContestWinner({ client });

			if (error || !response?.ok || !result) {
				drawError = getApiErrorDetail(error) ?? 'Не удалось провести розыгрыш';
				return;
			}

			// The draw is read-only: the server draws from the live pool and returns
			// both the winner and the current pool size, so there is nothing to
			// refetch — trust the response.
			poolSize = result.pool_size;
			winner = result.winner;
			hasDrawn = true;
		} finally {
			isDrawing = false;
		}
	}
</script>

<svelte:head>
	<title>Голосование · ФАН ФАН</title>
</svelte:head>

<SectionIntro
	description="Задавай период голосования, следи за лидерами номинаций и разыгрывай приз среди тех, кто проголосовал во всех номинациях."
/>

<div class="flex flex-col gap-8">
	<SettingsSection title="Период голосования" description="Голосовать можно только в этот период.">
		<!-- novalidate + read-only while saving: the same form rules as the festival
		     settings, so errors are ours and in Russian, and the keyboard stays up. -->
		<form novalidate class="flex flex-col gap-4" onsubmit={handleSubmit}>
			<Field.FieldGroup class="grid gap-4 sm:grid-cols-2">
				<Field.Field data-invalid={votingStartError ? true : undefined}>
					<Field.FieldLabel for="voting-start">Начало (МСК)</Field.FieldLabel>
					<Input
						id="voting-start"
						type="datetime-local"
						bind:value={votingStart}
						readonly={isSaving}
						oninput={handleRangeInput}
						aria-invalid={votingStartError ? true : undefined}
					/>
					{#if votingStartError}
						<Field.FieldError>{votingStartError}</Field.FieldError>
					{/if}
				</Field.Field>
				<Field.Field data-invalid={votingEndError ? true : undefined}>
					<Field.FieldLabel for="voting-end">Конец (МСК)</Field.FieldLabel>
					<Input
						id="voting-end"
						type="datetime-local"
						bind:value={votingEnd}
						readonly={isSaving}
						oninput={handleRangeInput}
						aria-invalid={votingEndError ? true : undefined}
					/>
					{#if votingEndError}
						<Field.FieldError>{votingEndError}</Field.FieldError>
					{/if}
				</Field.Field>
			</Field.FieldGroup>

			{#if saveError}
				<Alert.Root variant="destructive">
					<AlertCircle />
					<Alert.Description>{saveError}</Alert.Description>
				</Alert.Root>
			{/if}

			<div class="flex flex-col gap-2 sm:flex-row">
				<Button type="submit" disabled={isSaving}>
					{#if isSaving}
						<Spinner data-icon="inline-start" />
						Сохраняем…
					{:else}
						Сохранить
					{/if}
				</Button>
				{#if hasSavedRange}
					<Button
						type="button"
						variant="outline"
						disabled={isSaving}
						onclick={() => (clearConfirmOpen = true)}
					>
						Отключить голосование
					</Button>
				{/if}
			</div>
		</form>
	</SettingsSection>

	<SettingsSection
		title="Розыгрыш приза"
		description="Случайный участник среди тех, кто проголосовал во всех номинациях."
	>
		<p class="flex items-center gap-2 text-sm text-muted-foreground">
			<Users class="size-4 shrink-0" aria-hidden="true" />
			В розыгрыше: {poolSize}
			{pluralize(poolSize, 'участник', 'участника', 'участников')}
		</p>

		{#if drawError}
			<Alert.Root variant="destructive">
				<AlertCircle />
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
			class="w-full sm:w-auto sm:self-start"
			disabled={isDrawing || !canDraw}
			onclick={handleDraw}
		>
			{#if isDrawing}
				<Spinner data-icon="inline-start" />
				Разыгрываем…
			{:else if hasDrawn}
				Разыграть ещё раз
			{:else}
				Разыграть
			{/if}
		</Button>
		{#if !canDraw}
			<p class="text-xs text-muted-foreground">
				Кнопка станет активной, когда кто-нибудь проголосует во всех номинациях.
			</p>
		{/if}
	</SettingsSection>

	<SettingsSection title="Лидеры номинаций">
		{#if nominations.length > 0}
			<MenuGroup>
				<ul class="divide-y divide-border">
					{#each nominations as nomination (nomination.id)}
						<li class="flex flex-col gap-1 p-4">
							<p class="text-sm text-muted-foreground">{nomination.title}</p>
							{#if nomination.leader}
								<div class="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
									<span class="font-medium text-foreground">{nomination.leader.title}</span>
									<span class="text-sm text-muted-foreground tabular-nums">
										{nomination.leader.votes_count}
										{pluralize(nomination.leader.votes_count, 'голос', 'голоса', 'голосов')}
										из {nomination.total_votes}
									</span>
								</div>
							{:else}
								<p class="text-sm text-muted-foreground">Голосов пока нет</p>
							{/if}
						</li>
					{/each}
				</ul>
			</MenuGroup>
		{:else}
			<EmptyState
				icon={Users}
				title="Нет номинаций для голосования"
				message="Появятся после импорта косплей-конкурса"
			/>
		{/if}
	</SettingsSection>
</div>

<ConfirmDialog
	bind:open={clearConfirmOpen}
	title="Отключить голосование?"
	description="Период сотрётся, и голосовать станет нельзя, пока не задашь новый. Уже отданные голоса останутся."
	confirmLabel="Отключить"
	destructive
	onconfirm={handleClear}
/>
