<script lang="ts">
	import { createApiClient } from '$lib/api';
	import { Badge, type BadgeProps, Button, Spinner } from 'flowbite-svelte';
	import { UndoOutline } from 'flowbite-svelte-icons';
	const client = createApiClient();
	import type {
		ScheduleChangeEventDTO,
		ScheduleChangeFullDTO,
		ScheduleChangeType
	} from '$lib/types/schedule';

	import { invalidate } from '$app/navigation';
	import { getToastService } from '$lib/services/toasts.svelte';

	let { change }: { change: ScheduleChangeFullDTO } = $props();

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

	// Map change types to Russian labels
	const changeTypeLabels: Record<ScheduleChangeType, string> = {
		set_as_current: 'Установлено текущим',
		moved: 'Перенесено',
		skipped: 'Пропущено',
		unskipped: 'Восстановлено'
	};

	// Map change types to badge colors
	const changeTypeColors: Record<ScheduleChangeType, BadgeProps['color']> = {
		set_as_current: 'green',
		moved: 'blue',
		skipped: 'yellow',
		unskipped: 'purple'
	};

	function formatEvent(event: ScheduleChangeEventDTO | null | undefined): string {
		if (!event) return '';
		return `#${event.number} ${event.title}`;
	}
</script>

<div class="rounded-2xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
	<div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
		<div class="flex-1">
			<div class="mb-2 flex flex-wrap items-center gap-2">
				<Badge color={changeTypeColors[change.type]} border class="text-sm">
					{changeTypeLabels[change.type]}
				</Badge>
				<!-- The backend broadcasts a global announcement exactly when the
				     next event changed, so use that flag to flag the change here. -->
				{#if change.next_event_changed}
					<Badge color="red" border class="text-sm">Объявление</Badge>
				{/if}
			</div>

			<div class="space-y-1 text-sm">
				{#if change.changed_event}
					<p>
						<span class="font-bold text-gray-700 dark:text-gray-300">Выступление:</span>
						<span class="text-gray-900 dark:text-white">
							{formatEvent(change.changed_event)}
						</span>
					</p>
				{/if}

				{#if change.argument_event}
					<p>
						<span class="font-bold text-gray-700 dark:text-gray-300">
							{change.type === 'moved' ? 'После:' : 'Связанное выступление:'}
						</span>
						<span class="text-gray-900 dark:text-white">
							{formatEvent(change.argument_event)}
						</span>
					</p>
				{/if}

				{#if change.user}
					<p>
						<span class="font-bold text-gray-700 dark:text-gray-300">Пользователь:</span>
						<span class="text-gray-900 dark:text-white">
							{change.user.username}
						</span>
					</p>
				{/if}

				{#if change.mailing_id}
					<p>
						<span class="font-bold text-gray-700 dark:text-gray-300">ID рассылки:</span>
						<span class="text-gray-900 dark:text-white">
							{change.mailing_id}
						</span>
					</p>
				{/if}
			</div>
		</div>

		<div class="flex items-center gap-2 sm:shrink-0">
			<span class="text-xs text-gray-500 dark:text-gray-400">
				ID: {change.id}
			</span>
			<Button color="light" size="xs" onclick={undoChange} disabled={isUndoing}>
				{#if isUndoing}
					<Spinner size="4" />
				{:else}
					<UndoOutline class="h-4 w-4" />
				{/if}
				Отменить
			</Button>
		</div>
	</div>
</div>
