<script lang="ts">
	// Placeholder that mirrors the home layout — the hero card (key art, title,
	// countdown box, info row, social links) then the "get ready" section (heading,
	// featured card, compact grid) — so the layout doesn't jump when the loaded page
	// replaces it. Shown by the app shell during a navigation whose load runs longer
	// than the delay gate; the config load is network-first (fetchWithCache), so it
	// can outlast the gate even for a returning user. Pulse is CSS-only, so app.css's
	// prefers-reduced-motion rule stills it.

	// Four countdown cells and three compact "get ready" cards fill their grids
	// evenly. Index keys are fine — these are static and never reorder.
	const countdownCells = Array.from({ length: 4 }, (_, i) => i);
	const compactCards = Array.from({ length: 3 }, (_, i) => i);
</script>

<div class="space-y-5 sm:space-y-6" role="status" aria-live="polite">
	<span class="sr-only">Загрузка…</span>

	<!-- Hero card: key art beside a text column (stacked on mobile). -->
	<section
		class="overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-sm dark:border-gray-800 dark:bg-gray-900"
	>
		<div class="grid lg:grid-cols-2 lg:items-stretch">
			<!-- Key art block -->
			<div
				class="aspect-[16/9] w-full animate-pulse bg-gray-200 sm:aspect-[4/3] lg:order-2 lg:aspect-auto dark:bg-gray-700"
			></div>

			<div class="space-y-4 p-5 sm:p-7 lg:order-1 lg:p-9">
				<!-- Title + lead paragraph -->
				<div class="space-y-2">
					<div class="h-8 w-3/5 animate-pulse rounded-lg bg-gray-200 dark:bg-gray-700"></div>
					<div class="h-4 w-full animate-pulse rounded-full bg-gray-200 dark:bg-gray-700"></div>
					<div class="h-4 w-4/5 animate-pulse rounded-full bg-gray-200 dark:bg-gray-700"></div>
				</div>

				<!-- Countdown box -->
				<div class="rounded-xl border border-gray-200 p-3 dark:border-gray-700">
					<div
						class="mb-2.5 h-3 w-32 animate-pulse rounded-full bg-gray-200 dark:bg-gray-700"
					></div>
					<div class="grid grid-cols-4 gap-2">
						{#each countdownCells as cell (cell)}
							<div class="h-14 animate-pulse rounded-lg bg-gray-200 dark:bg-gray-700"></div>
						{/each}
					</div>
				</div>

				<!-- Venue info row -->
				<div class="flex items-center gap-3">
					<div class="h-9 w-9 shrink-0 animate-pulse rounded-xl bg-gray-200 dark:bg-gray-700"></div>
					<div class="h-4 w-2/3 animate-pulse rounded-full bg-gray-200 dark:bg-gray-700"></div>
				</div>

				<!-- Social links -->
				<div class="flex flex-wrap items-center gap-2 pt-1">
					{#each countdownCells as social (social)}
						<div class="h-11 w-11 animate-pulse rounded-xl bg-gray-200 dark:bg-gray-700"></div>
					{/each}
				</div>
			</div>
		</div>
	</section>

	<!-- Get-ready section: heading, featured card, then a compact grid. -->
	<div class="space-y-3">
		<div class="max-w-3xl space-y-1">
			<div class="h-6 w-56 animate-pulse rounded-full bg-gray-200 dark:bg-gray-700"></div>
			<div class="h-4 w-3/4 animate-pulse rounded-full bg-gray-200 dark:bg-gray-700"></div>
		</div>

		<div class="space-y-3">
			<!-- Featured card -->
			<div
				class="flex items-center gap-4 rounded-2xl border border-gray-200 bg-white p-4 shadow-sm sm:p-5 dark:border-gray-800 dark:bg-gray-900"
			>
				<div
					class="h-12 w-12 shrink-0 animate-pulse rounded-xl bg-gray-200 sm:h-14 sm:w-14 dark:bg-gray-700"
				></div>
				<div class="min-w-0 flex-1 space-y-2">
					<div class="h-5 w-1/2 animate-pulse rounded-full bg-gray-200 dark:bg-gray-700"></div>
					<div class="h-3.5 w-4/5 animate-pulse rounded-full bg-gray-200 dark:bg-gray-700"></div>
				</div>
			</div>

			<!-- Compact card grid -->
			<div class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
				{#each compactCards as card (card)}
					<div
						class="flex flex-col gap-3 rounded-2xl border border-gray-200 bg-white p-4 shadow-sm dark:border-gray-800 dark:bg-gray-900"
					>
						<div class="h-11 w-11 animate-pulse rounded-xl bg-gray-200 dark:bg-gray-700"></div>
						<div class="h-4 w-2/3 animate-pulse rounded-full bg-gray-200 dark:bg-gray-700"></div>
						<div class="h-3 w-full animate-pulse rounded-full bg-gray-200 dark:bg-gray-700"></div>
					</div>
				{/each}
			</div>
		</div>
	</div>
</div>
