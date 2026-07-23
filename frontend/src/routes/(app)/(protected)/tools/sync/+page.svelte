<script lang="ts">
	import type { components } from '$lib/api/v1';

	import { invalidate } from '$app/navigation';
	import { createApiClient } from '$lib/api';
	import { getApiErrorDetail } from '$lib/api/errors';
	import SectionIntro from '$lib/components/SectionIntro.svelte';
	import { formatRelativeTime } from '$lib/utils/formatters';
	import { Alert, Badge, Button, Card, Spinner } from 'flowbite-svelte';

	import type { PageProps } from './$types';

	type SyncSource = components['schemas']['SyncSource'];
	type SyncRunDTO = components['schemas']['SyncRunDTO'];

	let { data }: PageProps = $props();

	const client = createApiClient();

	// External source names are product names, so they stay untranslated; the
	// description says what each sync actually brings in.
	const SOURCE_LABELS: Record<SyncSource, { title: string; description: string }> = {
		cosplay2: {
			title: 'Cosplay2',
			description: 'Номинации и участники конкурсной программы'
		},
		ticketscloud: {
			title: 'TicketsCloud',
			description: 'Купленные билеты'
		}
	};

	const TRIGGER_LABELS: Record<SyncRunDTO['trigger'], string> = {
		manual: 'вручную',
		schedule: 'по расписанию',
		cli: 'из консоли'
	};

	// Only one manual run at a time: a run in flight disables both buttons so
	// the vendor APIs aren't hit with parallel full syncs from one screen.
	let runningSource = $state<SyncSource | null>(null);
	let inlineError = $state('');
	let successMessage = $state('');

	async function runSync(source: SyncSource) {
		inlineError = '';
		successMessage = '';
		runningSource = source;

		try {
			const { error, response } = await client.POST('/sync/run', {
				body: { source }
			});

			if (error || !response.ok) {
				inlineError =
					getApiErrorDetail(error) ??
					(response.status === 401
						? 'Нужно войти в аккаунт заново'
						: response.status === 403
							? 'У тебя нет доступа к синхронизации'
							: 'Не удалось выполнить синхронизацию');
				return;
			}

			successMessage = `Синхронизация с ${SOURCE_LABELS[source].title} завершена`;
		} catch (submitError) {
			console.error('Manual sync failed:', submitError);
			inlineError = 'Не удалось выполнить синхронизацию';
		} finally {
			runningSource = null;
			// Refresh statuses in both outcomes: a failed run also lands in the log.
			await invalidate('app:sync');
		}
	}
</script>

<svelte:head>
	<title>Синхронизация · ФАН ФАН</title>
</svelte:head>

<SectionIntro
	description="Загрузи свежие данные из внешних сервисов и проверь, когда синхронизация выполнялась в последний раз."
/>

{#if inlineError}
	<Alert color="red" class="mx-auto mb-4 w-full max-w-2xl">
		{inlineError}
	</Alert>
{/if}

{#if successMessage}
	<Alert color="green" class="mx-auto mb-4 w-full max-w-2xl">
		{successMessage}
	</Alert>
{/if}

<div class="mx-auto flex w-full max-w-2xl flex-col gap-4">
	{#each data.sources as sourceStatus (sourceStatus.source)}
		{@const labels = SOURCE_LABELS[sourceStatus.source]}
		<Card class="w-full max-w-none rounded-2xl p-4 sm:p-6">
			<div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
				<div class="min-w-0">
					<h2 class="text-lg font-semibold text-gray-900 dark:text-white">{labels.title}</h2>
					<p class="text-sm text-gray-500 dark:text-gray-400">{labels.description}</p>
					<p class="mt-2 text-sm text-gray-700 dark:text-gray-300">
						{#if sourceStatus.last_success_at}
							Последняя успешная синхронизация: {formatRelativeTime(sourceStatus.last_success_at)}
						{:else}
							Синхронизация ещё не выполнялась
						{/if}
					</p>
				</div>
				<Button
					color="primary"
					class="min-h-11 shrink-0 justify-center rounded-xl"
					disabled={runningSource !== null}
					onclick={() => runSync(sourceStatus.source)}
				>
					{#if runningSource === sourceStatus.source}
						<Spinner size="4" class="mr-2" color="primary" />
						Синхронизируем…
					{:else}
						Синхронизировать
					{/if}
				</Button>
			</div>

			{#if sourceStatus.recent_runs.length > 0}
				<h3 class="mt-4 text-sm font-medium text-gray-900 dark:text-white">Последние запуски</h3>
				<ul class="mt-2 divide-y divide-gray-200 dark:divide-gray-700">
					{#each sourceStatus.recent_runs as run (run.id)}
						<li class="flex flex-col gap-1 py-2">
							<div class="flex flex-wrap items-center gap-2 text-sm">
								{#if run.status === 'completed'}
									<Badge color="green">Успешно</Badge>
								{:else}
									<Badge color="red">Ошибка</Badge>
								{/if}
								<span class="text-gray-700 dark:text-gray-300">
									{formatRelativeTime(run.started_at)}
								</span>
								<span class="text-gray-500 dark:text-gray-400">
									{TRIGGER_LABELS[run.trigger]}{run.started_by
										? ` · ${run.started_by.username}`
										: ''}
								</span>
							</div>
							{#if run.error_message}
								<p class="text-sm break-words text-red-600 dark:text-red-400">
									{run.error_message}
								</p>
							{/if}
						</li>
					{/each}
				</ul>
			{/if}
		</Card>
	{/each}
</div>
