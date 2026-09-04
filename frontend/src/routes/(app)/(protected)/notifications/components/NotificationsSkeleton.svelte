<script lang="ts">
	import { Skeleton } from '$lib/components/ui/skeleton';

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
	<Skeleton class="mb-4 h-4 w-40 rounded-full" />

	<div class="flex flex-col gap-3">
		{#each rows as titleWidth, rowIndex (rowIndex)}
			<div class="flex items-start gap-3 rounded-xl border bg-card p-4 shadow-sm">
				<!-- Round bell avatar -->
				<Skeleton class="size-10 shrink-0 rounded-full" />
				<!-- Title line + timestamp -->
				<div class="flex w-full min-w-0 flex-col gap-2 pt-1">
					<Skeleton class="h-3.5 {titleWidth} rounded-full" />
					<Skeleton class="h-3 w-20 rounded-full" />
				</div>
			</div>
		{/each}
	</div>
</div>
