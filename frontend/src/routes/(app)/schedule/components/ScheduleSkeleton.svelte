<script lang="ts">
	import { Skeleton } from '#lib/components/ui/skeleton/index.js';
	import { m } from '#lib/paraglide/messages.js';

	const blocks = [4, 3].map((rowCount) => Array.from({ length: rowCount }, (_, i) => i));
</script>

<div class="flex flex-col gap-4" role="status" aria-live="polite">
	<span class="sr-only">{m.schedule_loading()}</span>

	<div class="flex flex-col gap-3">
		<Skeleton class="h-9 w-full rounded-xl" />
		<Skeleton class="h-8 w-44 rounded-md" />
	</div>

	<div class="flex flex-col gap-6">
		{#each blocks as rows, blockIndex (blockIndex)}
			<section class="flex flex-col gap-2">
				<div class="flex min-h-11 items-center justify-between gap-3 px-1">
					<Skeleton class="h-4 w-24 rounded-full" />
					<Skeleton class="h-3 w-4 rounded-full" />
				</div>

				<div class="divide-y divide-border overflow-clip rounded-xl border bg-card">
					{#each rows as rowIndex (rowIndex)}
						<div class="flex items-start gap-3 px-3 py-4 sm:px-4">
							<Skeleton class="size-12 shrink-0 rounded-lg" />
							<div class="flex min-w-0 flex-1 flex-col gap-2 pt-1">
								<Skeleton class="h-3.5 w-3/4 rounded-full" />
								<Skeleton class="h-3 w-1/2 rounded-full" />
							</div>
							<Skeleton class="size-11 shrink-0 rounded-lg" />
						</div>
					{/each}
				</div>
			</section>
		{/each}
	</div>
</div>
