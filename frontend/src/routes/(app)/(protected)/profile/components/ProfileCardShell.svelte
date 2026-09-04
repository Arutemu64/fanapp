<script lang="ts">
	import type { Snippet } from 'svelte';

	import * as Card from '$lib/components/ui/card';

	interface Props {
		title: string;
		description?: string;
		icon?: Snippet;
		children: Snippet;
	}

	let { title, description, icon, children }: Props = $props();
</script>

<!-- rounded-2xl opts up from the standard tier for this large settings card. -->
<Card.Root class="w-full max-w-none rounded-2xl">
	<!-- Only horizontal padding here: Card.Root already supplies vertical padding
	     via py-(--card-spacing), so re-adding p-* would double the top/bottom gap. -->
	<div class="px-5 sm:px-6">
		<div class="flex flex-col gap-4">
			<!-- Shared header keeps all profile cards visually aligned. -->
			<div class="flex items-start gap-3">
				{#if icon}
					<div
						class="mt-0.5 flex size-10 shrink-0 items-center justify-center rounded-lg bg-muted text-muted-foreground"
					>
						{@render icon()}
					</div>
				{/if}

				<div class="min-w-0">
					<h3 class="text-lg font-bold text-foreground">{title}</h3>

					{#if description}
						<p class="mt-1 text-sm leading-5 text-muted-foreground">{description}</p>
					{/if}
				</div>
			</div>

			<div class="flex flex-col gap-4">
				{@render children()}
			</div>
		</div>
	</div>
</Card.Root>
