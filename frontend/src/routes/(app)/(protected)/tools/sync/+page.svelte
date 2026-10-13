<script lang="ts">
	import { createMutation, createQuery, useQueryClient } from '@tanstack/svelte-query';

	import type { SyncRunStatus, SyncSource, SyncSourceStatusDto } from '#lib/api/generated/index.js';

	import { getApiErrorDetail } from '#lib/api/errors.js';
	import {
		getSyncSourcesOptions,
		getSyncSourcesQueryKey,
		requestSyncMutation
	} from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import ErrorState from '#lib/components/ErrorState.svelte';
	import SectionIntro from '#lib/components/SectionIntro.svelte';
	import { Badge } from '#lib/components/ui/badge/index.js';
	import { Button } from '#lib/components/ui/button/index.js';
	import * as Card from '#lib/components/ui/card/index.js';
	import { Spinner } from '#lib/components/ui/spinner/index.js';
	import { getToastService } from '#lib/services/toasts.svelte.js';

	import SectionSpinner from '../../../components/SectionSpinner.svelte';

	const toastService = getToastService();
	const queryClient = useQueryClient();

	// Kept live by sync_run_updated events (see the root layout).
	const sourcesQuery = createQuery(() => getSyncSourcesOptions());
	const syncMutation = createMutation(() => ({
		...requestSyncMutation(),
		onSettled: () => queryClient.invalidateQueries({ queryKey: getSyncSourcesQueryKey() })
	}));

	const SOURCE_LABELS: Record<SyncSource, string> = {
		cosplay2: 'Cosplay2',
		tcloud: 'TicketsCloud'
	};

	const SOURCE_DESCRIPTIONS: Record<SyncSource, string> = {
		cosplay2: 'Номинации и участники косплей-конкурса',
		tcloud: 'Билеты зрителей, участников и волонтёров'
	};

	const STATUS_LABELS: Record<SyncRunStatus, string> = {
		pending: 'В очереди',
		running: 'Выполняется',
		finished: 'Готово',
		failed: 'Ошибка'
	};

	// Sources the user has just triggered, so the button shows a spinner before
	// the first SSE update lands. Cleared once the server reports a state.
	let requesting = $state<SyncSource[]>([]);

	function isActive(source: SyncSourceStatusDto): boolean {
		const status = source.last_run?.status;
		return status === 'pending' || status === 'running';
	}

	function isBusy(source: SyncSourceStatusDto): boolean {
		return requesting.includes(source.source) || isActive(source);
	}

	function formatTimestamp(value: string | null | undefined): string {
		if (!value) {
			return 'ещё не запускалась';
		}
		return new Date(value).toLocaleString('ru-RU', {
			day: 'numeric',
			month: 'long',
			hour: '2-digit',
			minute: '2-digit'
		});
	}

	// `mutateAsync`, not `mutate`: two sources can be requested at once, and
	// `mutate` only calls back for the latest call.
	async function requestSync(source: SyncSource) {
		requesting = [...requesting, source];
		try {
			await syncMutation.mutateAsync({ path: { source } });
			toastService.add('Синхронизация запущена', 'success');
		} catch (error) {
			toastService.error(error);
		} finally {
			requesting = requesting.filter((item) => item !== source);
		}
	}
</script>

<svelte:head>
	<title>Синхронизация · ФАН ФАН</title>
</svelte:head>

<SectionIntro
	description="Данные подтягиваются автоматически по расписанию. Запусти вручную, если нужно увидеть свежие данные прямо сейчас."
/>

{#if sourcesQuery.data === undefined}
	{#if sourcesQuery.isError}
		<ErrorState
			variant="inline"
			onRetry={() => void sourcesQuery.refetch()}
			error={{
				status: 500,
				message:
					getApiErrorDetail(sourcesQuery.error) ?? 'Не удалось загрузить состояние синхронизации'
			}}
		/>
	{:else}
		<SectionSpinner />
	{/if}
{:else}
	<div class="mx-auto flex w-full max-w-2xl flex-col gap-4">
		{#each sourcesQuery.data as source (source.source)}
			<Card.Root class="w-full max-w-none rounded-2xl p-4 sm:p-6">
				<div class="flex flex-wrap items-start justify-between gap-3">
					<div class="min-w-0">
						<h2 class="text-base font-semibold text-foreground sm:text-lg">
							{SOURCE_LABELS[source.source]}
						</h2>
						<p class="mt-1 text-sm text-muted-foreground">
							{SOURCE_DESCRIPTIONS[source.source]}
						</p>
					</div>
					{#if source.last_run}
						<Badge
							variant={source.last_run.status === 'failed' ? 'destructive' : 'outline'}
							class={[
								'shrink-0',
								source.last_run.status === 'finished' &&
									'border-success/30 bg-success/10 text-success',
								(source.last_run.status === 'pending' || source.last_run.status === 'running') &&
									'border-info/30 bg-info/10 text-info'
							]}
						>
							{STATUS_LABELS[source.last_run.status]}
						</Badge>
					{/if}
				</div>

				<div class="mt-4 flex flex-col gap-1 text-sm text-muted-foreground">
					<p>
						Последняя синхронизация: {formatTimestamp(
							source.last_run?.finished_at ?? source.last_run?.started_at
						)}
					</p>
					{#if source.last_run?.result}
						<p class="text-foreground">{source.last_run.result}</p>
					{/if}
					{#if source.last_run?.error}
						<p class="text-destructive">{source.last_run.error}</p>
					{/if}
				</div>

				<div class="mt-5">
					{#if source.available}
						<Button
							type="button"
							class="w-full sm:w-auto"
							disabled={isBusy(source)}
							onclick={() => requestSync(source.source)}
						>
							{#if isBusy(source)}
								<Spinner data-icon="inline-start" />
								Синхронизируем…
							{:else}
								Синхронизировать
							{/if}
						</Button>
					{:else}
						<p class="text-sm text-muted-foreground">Интеграция не настроена на этом сервере.</p>
					{/if}
				</div>
			</Card.Root>
		{/each}
	</div>
{/if}
