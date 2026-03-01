<script lang="ts">
	import { Badge, Button, Spinner, type BadgeProps } from 'flowbite-svelte';
	import { UndoOutline } from 'flowbite-svelte-icons';
	import { client } from '$lib/api/index.js';
	import SectionHeader from '$lib/components/SectionHeader.svelte';
	import { getToastService } from '$lib/stores/toasts.svelte';
	import { invalidateAll } from '$app/navigation';
	import type { ScheduleChangeEventDTO, ScheduleChangeType } from '$lib/types/schedule';

	let { data } = $props();
	const toastService = getToastService();
	let scheduleChanges = $derived(data.schedule_changes);
	let undoingId: number | null = $state(null);

	async function undoChange(changeId: number) {
		undoingId = changeId;
		try {
			const {
				data: responseData,
				error,
				response
			} = await client.DELETE('/schedule/changes/{schedule_change_id}', {
				params: { path: { schedule_change_id: changeId } }
			});

			if (error) {
				console.error('Error undoing change:', error);
				toastService.error(error);
				return;
			}

			toastService.add('Изменение отменено', 'success');
			await invalidateAll();
		} catch (err) {
			toastService.error('Не удалось отменить изменение');
			console.error('Undo error:', err);
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

	function formatEvent(event: ScheduleChangeEventDTO): string {
		return `#${event.public_number} ${event.title}`;
	}
</script>

<svelte:head>
	<title>Изменения расписания</title>
</svelte:head>

<SectionHeader title="Изменения расписания" description="История изменений событий в расписании" />

{#if scheduleChanges.length === 0}
	<div
		class="rounded-lg border border-gray-200 bg-white p-6 text-center dark:border-gray-700 dark:bg-gray-800"
	>
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
							<Badge color={changeTypeColors[change.type]} class="text-sm">
								{changeTypeLabels[change.type]}
							</Badge>
							{#if change.send_global_announcement}
								<Badge color="red" class="text-sm">Объявление</Badge>
							{/if}
						</div>

						<div class="space-y-1 text-sm">
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
						<Button
							color="light"
							size="xs"
							onclick={() => undoChange(change.id)}
							disabled={undoingId === change.id}
						>
							{#if undoingId === change.id}
								<Spinner size="4" />
							{:else}
								<UndoOutline class="h-4 w-4" />
							{/if}
							Отменить
						</Button>
					</div>
				</div>
			</div>
		{/each}
	</div>
{/if}
