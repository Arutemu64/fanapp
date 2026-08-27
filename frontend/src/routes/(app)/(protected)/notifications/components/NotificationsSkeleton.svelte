<script lang="ts">
	// Placeholder that mirrors the notifications feed — an intro line then a stack
	// of list-item cards (round bell avatar, title line, timestamp) — so the layout
	// doesn't jump when the loaded page replaces it. Shown by the app shell during a
	// navigation whose load runs longer than the delay gate; the feed blocks on a
	// network fetch (fetchWithCache), so that load can outlast it. Pulse is CSS-only,
	// so app.css's prefers-reduced-motion rule stills it.

	// Uneven title widths so the placeholder reads as content, not a repeating grid.
	// Index keys are fine — these rows are static and never reorder.
	const rows = ['w-3/4', 'w-1/2', 'w-5/6', 'w-2/3', 'w-3/5'];
</script>

<div role="status" aria-live="polite">
	<span class="sr-only">Загрузка уведомлений…</span>

	<!-- Intro line (the real page shows an unread-count summary here) -->
	<div class="mb-4 h-4 w-40 animate-pulse rounded-full bg-gray-200 dark:bg-gray-700"></div>

	<div class="space-y-3">
		{#each rows as titleWidth, rowIndex (rowIndex)}
			<div
				class="flex items-start gap-3 rounded-xl border border-gray-200 bg-white p-4 shadow-sm dark:border-gray-700 dark:bg-gray-800"
			>
				<!-- Round bell avatar -->
				<div
					class="h-10 w-10 shrink-0 animate-pulse rounded-full bg-gray-200 dark:bg-gray-700"
				></div>
				<!-- Title line + timestamp -->
				<div class="w-full min-w-0 space-y-2 pt-1">
					<div
						class="h-3.5 {titleWidth} animate-pulse rounded-full bg-gray-200 dark:bg-gray-700"
					></div>
					<div class="h-3 w-20 animate-pulse rounded-full bg-gray-200 dark:bg-gray-700"></div>
				</div>
			</div>
		{/each}
	</div>
</div>
