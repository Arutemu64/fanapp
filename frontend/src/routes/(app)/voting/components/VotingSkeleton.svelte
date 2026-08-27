<script lang="ts">
	// Placeholder that mirrors the voting grid — a status bar then a responsive
	// grid of nomination cards (count line, title, footer action) — so the layout
	// doesn't jump when the loaded page replaces it. Voting is online-only and
	// uncached, so its load is the most likely to outlast the shell's delay gate.
	// Pulse is CSS-only, so app.css's prefers-reduced-motion rule stills it.

	// Six cards fill the 1/2/3-column grid evenly at every breakpoint.
	const cards = Array.from({ length: 6 }, (_, i) => i);
</script>

<div role="status" aria-live="polite">
	<span class="sr-only">Загрузка номинаций…</span>

	<!-- Voting status bar -->
	<div class="mb-4 h-12 w-full animate-pulse rounded-xl bg-gray-200 dark:bg-gray-700"></div>

	<div class="grid grid-cols-1 gap-3 sm:grid-cols-2 sm:gap-4 lg:grid-cols-3">
		{#each cards as cardIndex (cardIndex)}
			<div
				class="flex flex-col rounded-xl border border-gray-200 bg-white p-4 shadow-sm dark:border-gray-700 dark:bg-gray-800"
			>
				<!-- Header row: participant count -->
				<div class="mb-2 flex min-h-6 items-center">
					<div class="h-3 w-20 animate-pulse rounded-full bg-gray-200 dark:bg-gray-700"></div>
				</div>

				<!-- Title, two lines -->
				<div class="flex-1 space-y-2">
					<div class="h-4 w-full animate-pulse rounded-full bg-gray-200 dark:bg-gray-700"></div>
					<div class="h-4 w-2/3 animate-pulse rounded-full bg-gray-200 dark:bg-gray-700"></div>
				</div>

				<!-- Footer action row -->
				<div class="mt-3 flex justify-end border-t border-gray-100 pt-3 dark:border-gray-700">
					<div class="h-4 w-24 animate-pulse rounded-full bg-gray-200 dark:bg-gray-700"></div>
				</div>
			</div>
		{/each}
	</div>
</div>
