<script lang="ts">
	import type { Path } from '$app/types';
	import type { Component } from 'svelte';

	import { ChevronRight } from '@lucide/svelte';

	import * as Item from '#lib/components/ui/item/index.js';
	import { resolvePath } from '#lib/utils/paths.js';

	interface Props {
		href: Path;
		label: string;
		/** A line under the label, for rows whose title alone doesn't say what is behind them. */
		description?: string;
		icon: Component;
		/** Current state shown before the chevron, so it reads without opening the page. */
		value?: string;
	}

	let { href, label, description, icon: Icon, value }: Props = $props();
</script>

<Item.Root class="rounded-none">
	{#snippet child({ props })}
		<a href={resolvePath(href)} {...props}>
			<Item.Media class="size-9 rounded-lg bg-muted text-muted-foreground">
				<Icon class="size-5" aria-hidden="true" />
			</Item.Media>
			<Item.Content>
				<Item.Title class="text-base">{label}</Item.Title>
				{#if description}
					<Item.Description>{description}</Item.Description>
				{/if}
			</Item.Content>
			<Item.Actions>
				{#if value}
					<span class="text-sm text-muted-foreground">{value}</span>
				{/if}
				<ChevronRight class="size-4 text-muted-foreground" aria-hidden="true" />
			</Item.Actions>
		</a>
	{/snippet}
</Item.Root>
