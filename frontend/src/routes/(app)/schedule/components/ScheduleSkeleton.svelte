<script lang="ts">
	import { Skeleton } from '$lib/components/ui/skeleton';

	// Placeholder that mirrors the schedule's real structure — filter bar, then
	// block sections of card rows (leading number box, two text lines, trailing
	// bell) — so the layout doesn't jump when the loaded page replaces it. Shown
	// by the app shell during a navigation whose load runs longer than the delay
	// gate. Pulse is CSS-only, so app.css's prefers-reduced-motion rule stills it.

	// Faux blocks, each an array of row indices. Uneven counts so the placeholder
	// reads as content, not a repeating grid. Index keys are fine — these rows are
	// static and never reorder.
	const blocks = [4, 3].map((rowCount) => Array.from({ length: rowCount }, (_, i) => i));
</script>

<div class="flex flex-col gap-4" role="status" aria-live="polite">
	<span class="sr-only">Загрузка программы…</span>

	<!-- Filter bar: search field + toggle row -->
	<div class="rounded-2xl border bg-card p-3">
		<div class="flex flex-col gap-3">
			<Skeleton class="h-9 w-full rounded-xl" />
			<div class="flex items-center justify-between">
				<Skeleton class="h-6 w-28 rounded-full" />
				<Skeleton class="h-3 w-24 rounded-full" />
			</div>
		</div>
	</div>

	<div class="flex flex-col gap-6">
		{#each blocks as rows, blockIndex (blockIndex)}
			<section class="flex flex-col gap-2">
				<!-- Block header chip -->
				<div
					class="flex min-h-11 items-center justify-between gap-3 rounded-xl border bg-card px-3 py-2 shadow-sm"
				>
					<Skeleton class="h-4 w-40 rounded-full" />
					<Skeleton class="h-5 w-6 rounded-full" />
				</div>

				<!-- Card of event rows -->
				<div class="divide-y divide-border overflow-clip rounded-xl border bg-card">
					{#each rows as rowIndex (rowIndex)}
						<div class="flex items-start gap-3 px-3 py-4 sm:px-4">
							<!-- Leading number box -->
							<Skeleton class="size-12 shrink-0 rounded-lg" />
							<!-- Title + meta lines -->
							<div class="flex min-w-0 flex-1 flex-col gap-2 pt-1">
								<Skeleton class="h-3.5 w-3/4 rounded-full" />
								<Skeleton class="h-3 w-1/2 rounded-full" />
							</div>
							<!-- Trailing bell -->
							<Skeleton class="size-11 shrink-0 rounded-lg" />
						</div>
					{/each}
				</div>
			</section>
		{/each}
	</div>
</div>
