<script lang="ts">
	import type { Pathname } from '$app/types';
	import type { Component } from 'svelte';

	import { resolve } from '$app/paths';
	import * as Item from '$lib/components/ui/item';
	import { ChevronRight } from '@lucide/svelte';

	interface Props {
		href: Pathname;
		label: string;
		icon: Component;
		/** Current state shown before the chevron, so it reads without opening the page. */
		value?: string;
	}

	let { href, label, icon: Icon, value }: Props = $props();
</script>

<Item.Root class="rounded-none">
	{#snippet child({ props })}
		<a href={resolve(href)} {...props}>
			<Item.Media class="size-9 rounded-lg bg-muted text-muted-foreground">
				<Icon class="size-5" aria-hidden="true" />
			</Item.Media>
			<Item.Content>
				<Item.Title class="text-base">{label}</Item.Title>
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
