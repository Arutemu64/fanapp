<script lang="ts">
	import { createMutation, useQueryClient } from '@tanstack/svelte-query';

	import type { SyncRunStatus, SyncSource, SyncSourceStatusDto } from '#lib/api/generated/index.js';

	import {
		getSyncSourcesQueryKey,
		requestSyncMutation
	} from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import { Badge } from '#lib/components/ui/badge/index.js';
	import { Button } from '#lib/components/ui/button/index.js';
	import * as Card from '#lib/components/ui/card/index.js';
	import { Spinner } from '#lib/components/ui/spinner/index.js';
	import { m } from '#lib/paraglide/messages.js';
	import { getToastService } from '#lib/services/toasts.svelte.js';

	interface Props {
		source: SyncSourceStatusDto;
	}

	let { source }: Props = $props();

	const toastService = getToastService();
	const queryClient = useQueryClient();

	const syncMutation = createMutation(() => ({
		...requestSyncMutation(),
		onSettled: () => queryClient.invalidateQueries({ queryKey: getSyncSourcesQueryKey() })
	}));

	const SOURCE_LABELS: Record<SyncSource, string> = {
		cosplay2: 'Cosplay2',
		tcloud: 'TicketsCloud'
	};

	const SOURCE_DESCRIPTIONS: Record<SyncSource, string> = {
		cosplay2: m.sync_source_cosplay(),
		tcloud: m.sync_source_tickets()
	};

	const STATUS_LABELS: Record<SyncRunStatus, string> = {
		pending: m.status_queued(),
		running: m.status_running(),
		finished: m.status_done(),
		failed: m.status_error()
	};

	let lastRun = $derived(source.last_run);
	let active = $derived(lastRun?.status === 'pending' || lastRun?.status === 'running');
	// The mutation covers the gap before the first SSE update reports the run
	// (sync_run_updated, see the root layout).
	let busy = $derived(syncMutation.isPending || active);

	function formatTimestamp(value: string | null | undefined): string {
		if (!value) {
			return m.sync_never_run();
		}
		return new Date(value).toLocaleString('ru-RU', {
			day: 'numeric',
			month: 'long',
			hour: '2-digit',
			minute: '2-digit'
		});
	}

	function requestSync() {
		syncMutation.mutate(
			{ path: { source: source.source } },
			{
				onSuccess: () => toastService.add(m.sync_started(), 'success'),
				onError: (error) => toastService.error(error)
			}
		);
	}
</script>

<Card.Root class="w-full max-w-none p-4 sm:p-6">
	<div class="flex flex-wrap items-start justify-between gap-3">
		<div class="min-w-0">
			<h2 class="text-section text-foreground">
				{SOURCE_LABELS[source.source]}
			</h2>
			<p class="mt-1 text-sm text-muted-foreground">
				{SOURCE_DESCRIPTIONS[source.source]}
			</p>
		</div>
		{#if lastRun}
			<Badge
				variant={lastRun.status === 'failed' ? 'destructive' : 'outline'}
				class={[
					'shrink-0',
					lastRun.status === 'finished' && 'border-success/30 bg-success/10 text-success',
					active && 'border-info/30 bg-info/10 text-info'
				]}
			>
				{STATUS_LABELS[lastRun.status]}
			</Badge>
		{/if}
	</div>

	<div class="mt-4 flex flex-col gap-1 text-sm text-muted-foreground">
		<p>
			{m.sync_last_run({ when: formatTimestamp(lastRun?.finished_at ?? lastRun?.started_at) })}
		</p>
		{#if lastRun?.result}
			<p class="text-foreground">{lastRun.result}</p>
		{/if}
		{#if lastRun?.error}
			<p class="text-destructive">{lastRun.error}</p>
		{/if}
	</div>

	<div class="mt-5">
		{#if source.available}
			<Button type="button" class="w-full sm:w-auto" disabled={busy} onclick={requestSync}>
				{#if busy}
					<Spinner data-icon="inline-start" />
					{m.sync_running()}
				{:else}
					{m.sync_action()}
				{/if}
			</Button>
		{:else}
			<p class="text-sm text-muted-foreground">{m.sync_not_configured()}</p>
		{/if}
	</div>
</Card.Root>
