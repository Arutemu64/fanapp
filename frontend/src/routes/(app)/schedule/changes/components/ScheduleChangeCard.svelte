<script lang="ts">
	import type {
		ScheduleChangeEventDTO,
		ScheduleChangeFullDTO,
		ScheduleChangeType
	} from '$lib/types/schedule';

	import { invalidate } from '$app/navigation';
	import { createApiClient } from '$lib/api';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import * as Card from '$lib/components/ui/card';
	import { Spinner } from '$lib/components/ui/spinner';
	import { getToastService } from '$lib/services/toasts.svelte';
	import { Undo2 } from '@lucide/svelte';

	const client = createApiClient();

	interface Props {
		change: ScheduleChangeFullDTO;
	}

	let { change }: Props = $props();

	const toastService = getToastService();
	let isUndoing = $state(false);

	async function undoChange() {
		isUndoing = true;
		try {
			const { error, response } = await client.DELETE('/schedule/changes/{schedule_change_id}', {
				params: { path: { schedule_change_id: change.id } }
			});

			if (error || !response.ok) {
				console.error('Error undoing change:', error);
				toastService.error(error);
				return;
			}

			toastService.add('Изменение отменено', 'success');
			await invalidate('app:schedule:changes');
		} catch (err) {
			toastService.error('Не удалось отменить изменение');
			console.error('Undo error:', err);
		} finally {
			isUndoing = false;
		}
	}

	const changeTypeLabels: Record<ScheduleChangeType, string> = {
		set_as_current: 'Установлено текущим',
		moved: 'Перенесено',
		skipped: 'Пропущено',
		unskipped: 'Восстановлено'
	};

	const changeTypeBadgeClasses: Record<ScheduleChangeType, string> = {
		set_as_current: 'border-success/30 bg-success/10 text-success',
		moved: 'border-info/30 bg-info/10 text-info',
		skipped: 'border-warning/30 bg-warning/10 text-warning',
		// "Восстановлено" = back to normal, a neutral reset rather than a semantic state.
		unskipped: 'border-border bg-muted text-muted-foreground'
	};

	function formatEvent(event: ScheduleChangeEventDTO | null | undefined): string {
		if (!event) return '';
		// Breaks carry no public number — the title is all there is to show.
		if (event.number === null) return event.title;
		return `#${event.number} ${event.title}`;
	}
</script>

<Card.Root as="article" class="w-full max-w-none p-4">
	<div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
		<div class="flex-1">
			<div class="mb-2 flex flex-wrap items-center gap-2">
				<Badge variant="outline" class={['text-sm', changeTypeBadgeClasses[change.type]]}>
					{changeTypeLabels[change.type]}
				</Badge>
				{#if change.next_event_changed}
					<Badge variant="destructive" class="text-sm">Объявление</Badge>
				{/if}
			</div>

			<div class="flex flex-col gap-1 text-sm">
				{#if change.changed_event}
					<p>
						<span class="font-bold text-muted-foreground">Выступление:</span>
						<span class="text-foreground">
							{formatEvent(change.changed_event)}
						</span>
					</p>
				{/if}

				{#if change.argument_event}
					<p>
						<span class="font-bold text-muted-foreground">
							{change.type === 'moved' ? 'После:' : 'Связанное выступление:'}
						</span>
						<span class="text-foreground">
							{formatEvent(change.argument_event)}
						</span>
					</p>
				{/if}

				{#if change.user}
					<p>
						<span class="font-bold text-muted-foreground">Пользователь:</span>
						<span class="text-foreground">
							{change.user.username}
						</span>
					</p>
				{/if}

				{#if change.mailing_id}
					<p>
						<span class="font-bold text-muted-foreground">ID рассылки:</span>
						<span class="text-foreground">
							{change.mailing_id}
						</span>
					</p>
				{/if}
			</div>
		</div>

		<div class="flex items-center gap-2 sm:shrink-0">
			<span class="text-xs text-muted-foreground">
				ID: {change.id}
			</span>
			<Button variant="outline" size="sm" onclick={undoChange} disabled={isUndoing}>
				{#if isUndoing}
					<Spinner data-icon="inline-start" />
				{:else}
					<Undo2 data-icon="inline-start" />
				{/if}
				Отменить
			</Button>
		</div>
	</div>
</Card.Root>
