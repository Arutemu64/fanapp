<script lang="ts">
	import type { Component, Snippet } from 'svelte';

	import * as Empty from '#lib/components/ui/empty/index.js';

	interface Props {
		icon?: Component<{ class?: string }>;
		title?: string;
		message: string;
		children?: Snippet;
	}

	let { icon: Icon, title, message, children }: Props = $props();
</script>

<Empty.Root class="border border-solid bg-card p-6">
	<Empty.Header>
		{#if Icon}
			<Empty.Media class="mb-0 text-muted-foreground">
				<Icon class="size-10 sm:size-12" />
			</Empty.Media>
		{/if}
		{#if title}
			<Empty.Title class="text-base font-bold">{title}</Empty.Title>
		{/if}
		<Empty.Description>{message}</Empty.Description>
	</Empty.Header>
	{#if children}
		<Empty.Content>
			{@render children()}
		</Empty.Content>
	{/if}
</Empty.Root>
