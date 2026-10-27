<script lang="ts">
	import { Skeleton } from '#lib/components/ui/skeleton/index.js';
	import { m } from '#lib/paraglide/messages.js';

	const rows = ['w-3/4', 'w-1/2', 'w-5/6', 'w-2/3', 'w-3/5'];
</script>

<div role="status" aria-live="polite">
	<span class="sr-only">{m.notifications_loading()}</span>

	<Skeleton class="mb-4 h-4 w-40 rounded-full" />
	<Skeleton class="mb-3 h-3.5 w-20 rounded-full" />

	<div class="flex flex-col gap-3">
		{#each rows as titleWidth, rowIndex (rowIndex)}
			<div class="flex items-start gap-3 rounded-xl border bg-card p-4 shadow-sm">
				<Skeleton class="size-10 shrink-0 rounded-full" />
				<div class="flex w-full min-w-0 flex-col gap-2 pt-1">
					<Skeleton class="h-3.5 {titleWidth} rounded-full" />
					<Skeleton class="h-3 w-20 rounded-full" />
				</div>
			</div>
		{/each}
	</div>
</div>
