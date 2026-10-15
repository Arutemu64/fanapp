<script lang="ts">
	import { asset } from '$app/paths';
	import { AlertCircle, Download, Info } from '@lucide/svelte';

	import * as Alert from '#lib/components/ui/alert/index.js';
	import { Button } from '#lib/components/ui/button/index.js';
	import { m } from '#lib/paraglide/messages.js';

	// The header names are literal file content, not UI copy — they must stay
	// exactly as the parser expects them (REQUIRED_COLUMNS in
	// backend/src/fanfan/adapters/parsers/schedule.py).
	const columns = [
		{
			name: 'type',
			description: m.import_column_type_description()
		},
		{
			name: 'number',
			description: m.import_column_number_description()
		},
		{
			name: 'title',
			description: m.import_column_title_description()
		},
		{
			name: 'duration',
			description: m.import_column_duration_description()
		},
		{
			name: 'nomination_title',
			description: m.import_column_nomination_description()
		}
	];
</script>

<section class="mb-6 flex flex-col">
	<div class="mb-3 flex items-center gap-2">
		<Info class="size-5 shrink-0 text-muted-foreground" />
		<h2 class="text-base leading-snug font-semibold text-foreground sm:text-lg">
			{m.import_guide_title()}
		</h2>
	</div>

	<p class="text-sm leading-relaxed text-muted-foreground sm:text-base">
		{m.import_guide_intro()}
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
		{m.import_guide_required_prefix()} <span class="font-mono">type</span>,
		<span class="font-mono">number</span>
		{m.import_guide_and()} <span class="font-mono">nomination_title</span>
		{m.import_guide_event_required()}
		<span class="font-mono">title</span>
		{m.import_guide_and()} <span class="font-mono">duration</span>{m.import_guide_block_required()}
		<span class="font-mono">type</span>
		{m.import_guide_and()} <span class="font-mono">title</span>{m.import_guide_extra_columns()}
	</p>

	<Alert.Root variant="warning" class="mt-4">
		<AlertCircle class="size-5 shrink-0" />
		<Alert.Description>
			<span class="font-semibold">{m.import_guide_replaces_title()}</span>
			{m.import_guide_match_prefix()}
			<span class="font-mono">number</span>{m.import_guide_match_suffix()}
		</Alert.Description>
	</Alert.Root>

	<Button
		href={asset('schedule-template.xlsx')}
		download="schedule-template.xlsx"
		variant="outline"
		class="mt-4 w-full sm:w-auto sm:self-start"
	>
		<Download data-icon="inline-start" />
		{m.import_guide_download_template()}
	</Button>
</section>
