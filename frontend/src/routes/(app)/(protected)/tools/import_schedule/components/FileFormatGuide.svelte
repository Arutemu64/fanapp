<script lang="ts">
	import { base } from '$app/paths';
	import * as Alert from '$lib/components/ui/alert';
	import { Button } from '$lib/components/ui/button';
	import * as Card from '$lib/components/ui/card';
	import { AlertCircle, Download, Info } from '@lucide/svelte';

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
			description:
				'Номинация, например «Одиночное дефиле». Можно оставить пустой — у перерыва, открытия и закрытия номинации нет.'
		},
		{
			name: 'block_title',
			description:
				'Блок программы, например «Косплей». Можно оставить пустым — строка без блока (перерыв, открытие, закрытие) встаёт между блоками.'
		}
	];
</script>

<Card.Root class="mx-auto mb-4 w-full max-w-2xl rounded-2xl p-4 sm:mb-6 sm:p-6">
	<div class="mb-3 flex items-center gap-2">
		<Info class="size-5 shrink-0 text-muted-foreground" />
		<h2 class="text-base leading-snug font-semibold text-foreground sm:text-lg">
			Каким должен быть файл
		</h2>
	</div>

	<p class="text-sm leading-relaxed text-muted-foreground sm:text-base">
		Программа берётся с первого листа книги. В первой строке — заголовки колонок, ниже по строке на
		каждое выступление. Названия колонок пишутся латиницей ровно так, как в списке ниже; порядок
		колонок любой.
	</p>

	<dl class="mt-4 flex flex-col gap-2">
		{#each columns as column (column.name)}
			<div class="rounded-lg bg-muted/50 p-3 sm:flex sm:items-baseline sm:gap-3">
				<dt class="font-mono text-sm font-semibold text-foreground sm:w-44 sm:shrink-0">
					{column.name}
				</dt>
				<dd class="mt-1 text-sm leading-relaxed text-muted-foreground sm:mt-0">
					{column.description}
				</dd>
			</div>
		{/each}
	</dl>

	<p class="mt-3 text-xs leading-relaxed text-muted-foreground">
		Все пять колонок обязательны, но ячейки в <span class="font-mono">number</span>,
		<span class="font-mono">nomination_title</span> и <span class="font-mono">block_title</span>
		можно оставлять пустыми. В каждой строке обязательны только <span class="font-mono">title</span>
		и
		<span class="font-mono">duration</span>. Лишние колонки игнорируются.
	</p>

	<Alert.Root variant="warning" class="mt-4">
		<AlertCircle class="size-5 shrink-0" />
		<Alert.Description>
			<span class="font-semibold">Файл полностью заменяет программу.</span>
			Выступления сопоставляются по колонке <span class="font-mono">number</span>: совпавшие
			обновятся, а те, которых в файле нет, будут удалены. Строки без номера сопоставить не с чем —
			они каждый раз добавляются заново. Порядок строк задаёт порядок в программе.
		</Alert.Description>
	</Alert.Root>

	<Button
		href="{base}/schedule-template.xlsx"
		download="schedule-template.xlsx"
		variant="outline"
		class="mt-4 min-h-11 w-full justify-center sm:w-auto sm:self-start"
	>
		<Download data-icon="inline-start" />
		Скачать шаблон
	</Button>
</Card.Root>
