<script lang="ts">
	import { asset } from '$app/paths';
	import { AlertCircle, Download, Info } from '@lucide/svelte';

	import * as Alert from '#lib/components/ui/alert/index.js';
	import { Button } from '#lib/components/ui/button/index.js';

	// The header names are literal file content, not UI copy — they must stay
	// exactly as the parser expects them (REQUIRED_COLUMNS in
	// backend/src/fanfan/adapters/parsers/schedule.py).
	const columns = [
		{
			name: 'type',
			description:
				'Что это за строка. Пусто или event — выступление, block — начало блока программы. Все выступления ниже, до следующего блока, входят в этот блок.'
		},
		{
			name: 'number',
			description:
				'Номер выступления. Целое число, не должно повторяться. Можно оставить пустым — например, у перерыва.'
		},
		{
			name: 'title',
			description: 'Название выступления, а в строке блока — название блока, например «Косплей».'
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
		}
	];
</script>

<section class="mb-6 flex flex-col">
	<div class="mb-3 flex items-center gap-2">
		<Info class="size-5 shrink-0 text-muted-foreground" />
		<h2 class="text-base leading-snug font-semibold text-foreground sm:text-lg">
			Каким должен быть файл
		</h2>
	</div>

	<p class="text-sm leading-relaxed text-muted-foreground sm:text-base">
		Программа берётся с первого листа книги. В первой строке — заголовки колонок, ниже по строке на
		каждое выступление и на начало каждого блока. Названия колонок пишутся латиницей ровно так, как
		в списке ниже; порядок колонок любой.
	</p>

	<dl class="mt-4 divide-y divide-border overflow-hidden rounded-xl border border-border bg-card">
		{#each columns as column (column.name)}
			<div class="p-3 sm:flex sm:items-baseline sm:gap-3">
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
		Все пять колонок обязательны, но ячейки в <span class="font-mono">type</span>,
		<span class="font-mono">number</span> и <span class="font-mono">nomination_title</span> можно
		оставлять пустыми. В строке выступления обязательны только
		<span class="font-mono">title</span> и <span class="font-mono">duration</span>, в строке блока —
		<span class="font-mono">type</span> и <span class="font-mono">title</span>. Лишние колонки
		игнорируются.
	</p>

	<Alert.Root variant="warning" class="mt-4">
		<AlertCircle class="size-5 shrink-0" />
		<Alert.Description>
			<span class="font-semibold">Файл полностью заменяет программу.</span>
			Выступления сопоставляются по колонке <span class="font-mono">number</span>: совпавшие
			обновятся, а те, которых в файле нет, будут удалены. Строки без номера сопоставить не с чем —
			они каждый раз добавляются заново. Блоки сопоставляются по названию. Порядок строк задаёт
			порядок в программе.
		</Alert.Description>
	</Alert.Root>

	<Button
		href={asset('schedule-template.xlsx')}
		download="schedule-template.xlsx"
		variant="outline"
		class="mt-4 w-full sm:w-auto sm:self-start"
	>
		<Download data-icon="inline-start" />
		Скачать шаблон
	</Button>
</section>
