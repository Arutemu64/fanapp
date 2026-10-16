<script lang="ts">
	import type { Path } from '$app/types';
	import type { Component } from 'svelte';

	import { ChevronRight } from '@lucide/svelte';

	import * as Item from '#lib/components/ui/item/index.js';
	import { resolvePath } from '#lib/utils/paths.js';

	interface Props {
		title: string;
		description: string;
		icon: Component;
		href: Path;
	}

	let { title, description, icon: Icon, href }: Props = $props();
</script>

<!-- Same row shape as the /profile hub's MenuLink, so the toolbox reads as the next
     level of that menu rather than a separate dashboard. -->
<Item.Root class="rounded-none">
	{#snippet child({ props })}
		<a href={resolvePath(href)} {...props}>
			<Item.Media class="size-9 rounded-lg bg-muted text-muted-foreground">
				<Icon class="size-5" aria-hidden="true" />
			</Item.Media>
			<Item.Content>
				<Item.Title class="text-base">{title}</Item.Title>
				<Item.Description>{description}</Item.Description>
			</Item.Content>
			<Item.Actions>
				<ChevronRight class="size-4 text-muted-foreground" aria-hidden="true" />
			</Item.Actions>
		</a>
	{/snippet}
</Item.Root>
