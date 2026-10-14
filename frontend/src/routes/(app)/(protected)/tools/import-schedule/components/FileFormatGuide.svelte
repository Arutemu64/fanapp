<script lang="ts">
	import { asset } from '$app/paths';
	import { AlertCircle, Download, Info } from '@lucide/svelte';

	import RichText from '#lib/components/RichText.svelte';
	import * as Alert from '#lib/components/ui/alert/index.js';
	import { Button } from '#lib/components/ui/button/index.js';
	import { m } from '#lib/paraglide/messages.js';

	// The header names are literal file content, not UI copy — they must stay
	// exactly as the parser expects them (REQUIRED_COLUMNS in
	// backend/src/fanfan/adapters/parsers/schedule.py).
	const columns = [
		{ name: 'type', description: m.guide_type },
		{ name: 'number', description: m.guide_number },
		{ name: 'title', description: m.guide_title },
		{ name: 'duration', description: m.guide_duration },
		{ name: 'nomination_title', description: m.guide_nomination }
	];
</script>

{#snippet code(text: string)}
	<span class="font-mono">{text}</span>
{/snippet}

<section class="mb-6 flex flex-col">
	<div class="mb-3 flex items-center gap-2">
		<Info class="size-5 shrink-0 text-muted-foreground" />
		<h2 class="text-base leading-snug font-semibold text-foreground sm:text-lg">
			{m.guide_heading()}
		</h2>
	</div>

	<p class="text-sm leading-relaxed text-muted-foreground sm:text-base">
		{m.guide_intro()}
	</p>

	<dl class="mt-4 divide-y divide-border overflow-hidden rounded-xl border border-border bg-card">
		{#each columns as column (column.name)}
			<div class="p-3 sm:flex sm:items-baseline sm:gap-3">
				<dt class="font-mono text-sm font-semibold text-foreground sm:w-44 sm:shrink-0">
					{column.name}
				</dt>
				<dd class="mt-1 text-sm leading-relaxed text-muted-foreground sm:mt-0">
					{column.description()}
				</dd>
			</div>
		{/each}
	</dl>

	<p class="mt-3 text-xs leading-relaxed text-muted-foreground">
		<RichText text={m.guide_required()} tags={{ code }} />
	</p>

	<Alert.Root variant="warning" class="mt-4">
		<AlertCircle class="size-5 shrink-0" />
		<Alert.Description>
			<span class="font-semibold">{m.guide_replaces_title()}</span>
			<RichText text={m.guide_replaces()} tags={{ code }} />
		</Alert.Description>
	</Alert.Root>

	<Button
		href={asset('schedule-template.xlsx')}
		download="schedule-template.xlsx"
		variant="outline"
		class="mt-4 w-full sm:w-auto sm:self-start"
	>
		<Download data-icon="inline-start" />
		{m.guide_download_template()}
	</Button>
</section>
