<script lang="ts">
	import type { Component, Snippet } from 'svelte';

	import * as Empty from '$lib/components/ui/empty';

	interface Props {
		// Optional leading icon (e.g. for richer empty states like voting lists).
		icon?: Component<{ class?: string }>;
		// When set, renders a bold heading above the message (two-line variant).
		title?: string;
		message: string;
		// Optional trailing action, e.g. a "clear search" button.
		children?: Snippet;
	}

	let { icon: Icon, title, message, children }: Props = $props();
</script>

<!-- App-wide empty state: shadcn Empty on the app's card surface (solid border +
	bg-card + calm p-6), understated per DESIGN.md — a teaching state, not "nothing
	here". The icon stays bare and muted (default media variant) rather than a
	filled tile, keeping color for action and semantic state only. -->
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
