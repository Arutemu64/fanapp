<script lang="ts">
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

<div class="space-y-4" role="status" aria-live="polite">
	<span class="sr-only">Загрузка программы…</span>

	<!-- Filter bar: search field + toggle row -->
	<div
		class="rounded-2xl border border-gray-200 bg-white p-3 dark:border-gray-700 dark:bg-gray-800"
	>
		<div class="flex flex-col gap-3">
			<div class="h-9 w-full animate-pulse rounded-xl bg-gray-200 dark:bg-gray-700"></div>
			<div class="flex items-center justify-between">
				<div class="h-6 w-28 animate-pulse rounded-full bg-gray-200 dark:bg-gray-700"></div>
				<div class="h-3 w-24 animate-pulse rounded-full bg-gray-200 dark:bg-gray-700"></div>
			</div>
		</div>
	</div>

	<div class="space-y-6">
		{#each blocks as rows, blockIndex (blockIndex)}
			<section class="space-y-2">
				<!-- Block header chip -->
				<div
					class="flex min-h-11 items-center justify-between gap-3 rounded-xl border border-gray-200 bg-white px-3 py-2 shadow-sm dark:border-gray-700 dark:bg-gray-900"
				>
					<div class="h-4 w-40 animate-pulse rounded-full bg-gray-200 dark:bg-gray-700"></div>
					<div class="h-5 w-6 animate-pulse rounded-full bg-gray-200 dark:bg-gray-700"></div>
				</div>

				<!-- Card of event rows -->
				<div
					class="divide-y divide-gray-200 overflow-clip rounded-xl border border-gray-200 bg-white dark:divide-gray-700 dark:border-gray-700 dark:bg-gray-800"
				>
					{#each rows as rowIndex (rowIndex)}
						<div class="flex items-start gap-3 px-3 py-4 sm:px-4">
							<!-- Leading number box -->
							<div
								class="h-12 w-12 shrink-0 animate-pulse rounded-lg bg-gray-200 dark:bg-gray-700"
							></div>
							<!-- Title + meta lines -->
							<div class="min-w-0 flex-1 space-y-2 pt-1">
								<div
									class="h-3.5 w-3/4 animate-pulse rounded-full bg-gray-200 dark:bg-gray-700"
								></div>
								<div
									class="h-3 w-1/2 animate-pulse rounded-full bg-gray-200 dark:bg-gray-700"
								></div>
							</div>
							<!-- Trailing bell -->
							<div
								class="h-11 w-11 shrink-0 animate-pulse rounded-lg bg-gray-200 dark:bg-gray-700"
							></div>
						</div>
					{/each}
				</div>
			</section>
		{/each}
	</div>
</div>
