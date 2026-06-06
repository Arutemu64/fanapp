<script lang="ts">
	import type { Snippet } from 'svelte';
	import { Card } from 'flowbite-svelte';

	interface Props {
		title: string;
		description?: string;
		icon?: Snippet;
		children: Snippet;
	}

	let { title, description, icon, children }: Props = $props();
</script>

<Card class="w-full max-w-none rounded-2xl bg-white shadow-sm dark:bg-gray-800">
	<div class="p-5 sm:p-6">
		<div class="flex flex-col gap-4">
			<!-- Shared header keeps all profile cards visually aligned. -->
			<div class="flex items-center gap-3">
				{#if icon}
					<div
						class="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300"
					>
						{@render icon()}
					</div>
				{/if}

				<div class="min-w-0">
					<h3 class="text-lg font-bold text-gray-900 dark:text-white">{title}</h3>

					{#if description}
						<p class="mt-1 text-sm leading-5 text-gray-500 dark:text-gray-400">{description}</p>
					{/if}
				</div>
			</div>

			<div class="space-y-4">
				{@render children()}
			</div>
		</div>
	</div>
</Card>
