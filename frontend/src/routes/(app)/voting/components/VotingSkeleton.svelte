<script lang="ts">
	import { Skeleton } from '#lib/components/ui/skeleton/index.js';
	import { m } from '#lib/paraglide/messages.js';

	const cards = Array.from({ length: 6 }, (_, i) => i);
</script>

<div role="status" aria-live="polite">
	<span class="sr-only">{m.voting_nominations_loading()}</span>

	<Skeleton class="mb-4 h-12 w-full rounded-xl" />

	<div class="grid grid-cols-1 gap-3 sm:grid-cols-2 sm:gap-4 lg:grid-cols-3">
		{#each cards as cardIndex (cardIndex)}
			<div class="flex flex-col rounded-xl border bg-card p-4 shadow-sm">
				<div class="mb-2 flex min-h-6 items-center">
					<Skeleton class="h-3 w-20 rounded-full" />
				</div>

				<div class="flex flex-1 flex-col gap-2">
					<Skeleton class="h-4 w-full rounded-full" />
					<Skeleton class="h-4 w-2/3 rounded-full" />
				</div>

				<div class="mt-3 flex justify-end border-t pt-3">
					<Skeleton class="h-4 w-24 rounded-full" />
				</div>
			</div>
		{/each}
	</div>
</div>
