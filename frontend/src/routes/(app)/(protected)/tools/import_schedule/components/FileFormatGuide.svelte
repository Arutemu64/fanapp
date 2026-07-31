<script lang="ts">
	import { base } from '$app/paths';
	import { Alert, Button, Card } from 'flowbite-svelte';
	import {
		DownloadOutline,
		ExclamationCircleOutline,
		InfoCircleOutline
	} from 'flowbite-svelte-icons';

	// The header names are literal file content, not UI copy — they must stay
	// exactly as the parser expects them (REQUIRED_COLUMNS in
	// backend/src/fanfan/adapters/parsers/schedule.py).
	const columns = [
		{
			name: 'number',
			description:
				'Номер выступления. Целое число, не должно повторяться. Можно оставить пустым — например, у перерыва.'
		},
		{
			name: 'title',
			description: 'Название выступления.'
		},
		{
			name: 'duration',
			description:
				'Длительность в секундах. Целое число: 900 — это 15 минут, а 45 — короткий номер меньше минуты.'
		},
		{
			name: 'nomination_title',
			description: 'Номинация, например «Одиночное дефиле».'
		},
		{
			name: 'block_title',
			description: 'Блок программы, например «Косплей».'
		}
	];
</script>

<Card class="mx-auto mb-4 w-full max-w-2xl rounded-2xl p-4 sm:mb-6 sm:p-6">
	<div class="mb-3 flex items-center gap-2">
		<InfoCircleOutline class="h-5 w-5 shrink-0 text-gray-500 dark:text-gray-400" />
		<h2 class="text-base leading-snug font-semibold text-gray-900 sm:text-lg dark:text-white">
			Каким должен быть файл
		</h2>
	</div>

	<p class="text-sm leading-relaxed text-gray-600 sm:text-base dark:text-gray-300">
		Программа берётся с первого листа книги. В первой строке — заголовки колонок, ниже по строке на
		каждое выступление. Названия колонок пишутся латиницей ровно так, как в списке ниже; порядок
		колонок любой.
	</p>

	<dl class="mt-4 space-y-2">
		{#each columns as column (column.name)}
			<div class="rounded-lg bg-gray-50 p-3 sm:flex sm:items-baseline sm:gap-3 dark:bg-gray-700/40">
				<dt
					class="font-mono text-sm font-semibold text-gray-900 sm:w-44 sm:shrink-0 dark:text-white"
				>
					{column.name}
				</dt>
				<dd class="mt-1 text-sm leading-relaxed text-gray-600 sm:mt-0 dark:text-gray-300">
					{column.description}
				</dd>
			</div>
		{/each}
	</dl>

	<p class="mt-3 text-xs leading-relaxed text-gray-500 dark:text-gray-400">
		Все пять колонок обязательны. Пустой может быть только ячейка в колонке <span class="font-mono"
			>number</span
		>. Лишние колонки игнорируются.
	</p>

	<Alert color="yellow" class="mt-4 rounded-lg">
		{#snippet icon()}
			<ExclamationCircleOutline class="h-5 w-5 shrink-0" />
		{/snippet}
		<span class="font-semibold">Файл полностью заменяет программу.</span>
		Выступления сопоставляются по колонке <span class="font-mono">number</span>: совпавшие
		обновятся, а те, которых в файле нет, будут удалены. Строки без номера сопоставить не с чем —
		они каждый раз добавляются заново. Порядок строк задаёт порядок в программе.
	</Alert>

	<!-- Card lays its children out as a flex column, so sm:w-auto alone would still
		stretch the button to full width; sm:self-start is what shrinks it. -->
	<Button
		href="{base}/schedule-template.xlsx"
		download="schedule-template.xlsx"
		color="alternative"
		class="mt-4 min-h-11 w-full justify-center rounded-xl sm:w-auto sm:self-start"
	>
		<DownloadOutline class="me-2 h-5 w-5" />
		Скачать шаблон
	</Button>
</Card>
