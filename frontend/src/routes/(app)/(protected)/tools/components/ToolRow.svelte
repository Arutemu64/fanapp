<script lang="ts">
	import type { Path } from '$app/types';
	import type { Component } from 'svelte';

	import { resolve } from '$app/paths';
	import { ChevronRight, Lock } from '@lucide/svelte';

	import * as Item from '#lib/components/ui/item/index.js';

	interface Props {
		title: string;
		description: string;
		icon: Component;
		href: Path;
		/** No permission for this tool: the row becomes a non-navigable, muted state. */
		locked?: boolean;
	}

	let { title, description, icon: Icon, href, locked = false }: Props = $props();

	let titleClass = $derived(locked ? 'text-base text-muted-foreground' : 'text-base');
</script>

<!-- Same row shape as the /profile hub's MenuLink, so the toolbox reads as the next
     level of that menu rather than a separate dashboard. -->
{#snippet body()}
	<Item.Media class="size-9 rounded-lg bg-muted text-muted-foreground">
		<Icon class="size-5" aria-hidden="true" />
	</Item.Media>
	<Item.Content>
		<Item.Title class={titleClass}>{title}</Item.Title>
		<Item.Description>{description}</Item.Description>
	</Item.Content>
	<Item.Actions>
		{#if locked}
			<span class="inline-flex items-center gap-1 text-xs font-medium text-muted-foreground">
				<Lock class="size-3.5" aria-hidden="true" />
				Нет доступа
			</span>
		{:else}
			<ChevronRight class="size-4 text-muted-foreground" aria-hidden="true" />
		{/if}
	</Item.Actions>
{/snippet}

{#if locked}
	<!-- Non-navigable on purpose; the title explains the state on hover/focus without
	     inventing a channel to request access, which the app's admin model doesn't define. -->
	<Item.Root class="cursor-not-allowed rounded-none" title="Права на этот инструмент не выданы">
		{@render body()}
	</Item.Root>
{:else}
	<Item.Root class="rounded-none">
		{#snippet child({ props })}
			<a href={resolve(href)} {...props}>
				{@render body()}
			</a>
		{/snippet}
	</Item.Root>
{/if}
