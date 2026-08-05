<script lang="ts">
	import type { components } from '$lib/api/schema';

	import { invalidate } from '$app/navigation';
	import { createApiClient } from '$lib/api';
	import SectionIntro from '$lib/components/SectionIntro.svelte';
	import { getEventsClient } from '$lib/services/events.svelte';
	import { getToastService } from '$lib/services/toasts.svelte';
	import { Badge, Button, Card, Spinner } from 'flowbite-svelte';
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

	const STATUS_COLORS: Record<SyncRunStatus, 'blue' | 'yellow' | 'green' | 'red'> = {
		pending: 'yellow',
		running: 'blue',
		finished: 'green',
		failed: 'red'
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

<SectionIntro
	description="Данные подтягиваются автоматически по расписанию. Запусти вручную, если нужно увидеть свежие данные прямо сейчас."
/>

<div class="mx-auto flex w-full max-w-2xl flex-col gap-4">
	{#each data.sources as source (source.source)}
		<Card class="w-full max-w-none rounded-2xl p-4 sm:p-6">
			<div class="flex flex-wrap items-start justify-between gap-3">
				<div class="min-w-0">
					<h2 class="text-lg font-semibold text-gray-900 dark:text-white">
						{SOURCE_LABELS[source.source]}
					</h2>
					<p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
						{SOURCE_DESCRIPTIONS[source.source]}
					</p>
				</div>
				{#if source.last_run}
					<Badge color={STATUS_COLORS[source.last_run.status]} class="shrink-0 rounded-lg">
						{STATUS_LABELS[source.last_run.status]}
					</Badge>
				{/if}
			</div>

			<div class="mt-4 space-y-1 text-sm text-gray-500 dark:text-gray-400">
				<p>
					Последняя синхронизация: {formatTimestamp(
						source.last_run?.finished_at ?? source.last_run?.started_at
					)}
				</p>
				{#if source.last_run?.result}
					<p class="text-gray-900 dark:text-white">{source.last_run.result}</p>
				{/if}
				{#if source.last_run?.error}
					<p class="text-red-600 dark:text-red-400">{source.last_run.error}</p>
				{/if}
			</div>

			<div class="mt-5">
				{#if source.available}
					<Button
						type="button"
						color="primary"
						class="min-h-11 w-full justify-center sm:w-auto"
						disabled={isBusy(source)}
						onclick={() => requestSync(source.source)}
					>
						{#if isBusy(source)}
							<Spinner size="4" class="mr-2 fill-white" />
							Синхронизируем…
						{:else}
							Синхронизировать
						{/if}
					</Button>
				{:else}
					<p class="text-sm text-gray-500 dark:text-gray-400">
						Интеграция не настроена на этом сервере.
					</p>
				{/if}
			</div>
		</Card>
	{/each}
</div>
