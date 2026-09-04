<script lang="ts">
	import type { components } from '$lib/api/schema';

	import { invalidate } from '$app/navigation';
	import { createApiClient } from '$lib/api';
	import BackLink from '$lib/components/BackLink.svelte';
	import SectionIntro from '$lib/components/SectionIntro.svelte';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import * as Card from '$lib/components/ui/card';
	import { Spinner } from '$lib/components/ui/spinner';
	import { getEventsClient } from '$lib/services/events.svelte';
	import { getToastService } from '$lib/services/toasts.svelte';
	import { onMount } from 'svelte';

	import type { PageProps } from './$types';

	type SyncSourceStatus = components['schemas']['SyncSourceStatusDTO'];
	type SyncSource = components['schemas']['SyncSource'];
	type SyncRunStatus = components['schemas']['SyncRunStatus'];

	const { data }: PageProps = $props();

	const client = createApiClient();
	const toastService = getToastService();
	const eventsClient = getEventsClient();

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

	function isActive(source: SyncSourceStatus): boolean {
		const status = source.last_run?.status;
		return status === 'pending' || status === 'running';
	}

	function isBusy(source: SyncSourceStatus): boolean {
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

	async function requestSync(source: SyncSource) {
		requesting = [...requesting, source];
		try {
			const { error: apiError, response } = await client.POST('/sync/{source}', {
				params: { path: { source } }
			});
			if (apiError || !response.ok) {
				toastService.error(apiError);
				return;
			}
			toastService.add('Синхронизация запущена', 'success');
		} catch (err) {
			toastService.error(err);
		} finally {
			requesting = requesting.filter((item) => item !== source);
			await invalidate('app:sync-sources');
		}
	}

	onMount(() => {
		// Refetch on every run update and on every (re)connect, so an update
		// missed while the stream was down (or while the tab was backgrounded
		// past the pause grace) doesn't leave a stale "Выполняется" on screen.
		const reloadSources = () => {
			void invalidate('app:sync-sources');
		};

		eventsClient.on('sync_run_updated', reloadSources);
		eventsClient.on('connection_established', reloadSources);

		return () => {
			eventsClient.off('sync_run_updated', reloadSources);
			eventsClient.off('connection_established', reloadSources);
		};
	});
</script>

<svelte:head>
	<title>Синхронизация · ФАН ФАН</title>
</svelte:head>

<BackLink href="/tools" label="Назад к инструментам" />

<SectionIntro
	description="Данные подтягиваются автоматически по расписанию. Запусти вручную, если нужно увидеть свежие данные прямо сейчас."
/>

<div class="mx-auto flex w-full max-w-2xl flex-col gap-4">
	{#each data.sources as source (source.source)}
		<Card.Root class="w-full max-w-none rounded-2xl p-4 sm:p-6">
			<div class="flex flex-wrap items-start justify-between gap-3">
				<div class="min-w-0">
					<h2 class="text-lg font-semibold text-foreground">
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
						class="min-h-11 w-full justify-center sm:w-auto"
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
