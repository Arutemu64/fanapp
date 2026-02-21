<script lang="ts">
	import { Badge, Button, type BadgeProps } from 'flowbite-svelte';
	import { UndoOutline } from 'flowbite-svelte-icons';
	import type { ScheduleChangeDTO, ScheduleChangeType } from '$lib/types/schedule';
	import { api } from '$lib/api';
	import { toastService } from '$lib/stores/toasts.svelte';
	import { invalidateAll } from '$app/navigation';

	let { data } = $props();
	let scheduleChanges: ScheduleChangeDTO[] = $derived(data.schedule_changes);
	let undoingId: number | null = $state(null);

	async function undoChange(changeId: number) {
		undoingId = changeId;
		try {
			await api.delete(`/schedule/changes/${changeId}`);
			toastService.add('Изменение отменено', 'success');
			await invalidateAll();
		} catch (error) {
			toastService.error('Не удалось отменить изменение');
			console.error('Undo error:', error);
		} finally {
			undoingId = null;
		}
	}

	// Map change types to Russian labels
	const changeTypeLabels: Record<ScheduleChangeType, string> = {
		set_as_current: 'Установлено текущим',
		moved: 'Перемещено',
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

	function formatEvent(event: { public_id: number; title: string } | null): string {
		if (!event) return '—';
		return `#${event.public_id} ${event.title}`;
	}
</script>

<svelte:head>
	<title>Изменения расписания</title>
</svelte:head>

<div class="mb-4">
	<h1 class="text-xl font-bold text-gray-900 dark:text-white sm:text-2xl">Изменения расписания</h1>
	<p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
		История изменений событий в расписании
	</p>
</div>

{#if scheduleChanges.length === 0}
	<div class="rounded-lg border border-gray-200 bg-white p-6 text-center dark:border-gray-700 dark:bg-gray-800">
		<p class="text-gray-500 dark:text-gray-400">Изменений пока нет</p>
	</div>
{:else}
	<div class="space-y-3">
		{#each scheduleChanges as change (change.id)}
			<div
				class="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800"
			>
				<div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
					<div class="flex-1">
						<div class="mb-2 flex flex-wrap items-center gap-2">
							<Badge color={changeTypeColors[change.type]}>
								{changeTypeLabels[change.type]}
							</Badge>
							{#if change.send_global_announcement}
								<Badge color="red">Объявление</Badge>
							{/if}
						</div>

						<div class="space-y-1 text-sm">
							{#if change.mailing_id}
								<p>
									<span class="font-bold text-gray-700 dark:text-gray-300">Mailing ID:</span>
									<span class="text-gray-900 dark:text-white">
										{change.mailing_id}
									</span>
								</p>
							{/if}

							{#if change.changed_event}
								<p>
									<span class="font-bold text-gray-700 dark:text-gray-300">Событие:</span>
									<span class="text-gray-900 dark:text-white">
										{formatEvent(change.changed_event)}
									</span>
								</p>
							{/if}

							{#if change.argument_event}
								<p>
									<span class="font-bold text-gray-700 dark:text-gray-300">
										{change.type === 'moved' ? 'После:' : 'Связанное событие:'}
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
										{change.user.username ?? `ID: ${change.user.id}`}
									</span>
								</p>
							{/if}
						</div>
					</div>

					<div class="flex items-center gap-2 sm:shrink-0">
						<span class="text-xs text-gray-500 dark:text-gray-400">
							ID: {change.id}
						</span>
						<Button
							color="light"
							size="xs"
							onclick={() => undoChange(change.id)}
							disabled={undoingId === change.id}
						>
							<UndoOutline class="h-4 w-4" />
							Отменить
						</Button>
					</div>
				</div>
			</div>
		{/each}
	</div>
{/if}
