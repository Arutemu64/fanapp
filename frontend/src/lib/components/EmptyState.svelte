<script lang="ts">
	import type { Component, Snippet } from 'svelte';

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

<div
	class="rounded-lg border border-gray-200 bg-white p-6 text-center dark:border-gray-700 dark:bg-gray-800"
>
	{#if Icon}
		<Icon class="mx-auto h-10 w-10 text-gray-300 sm:h-12 sm:w-12 dark:text-gray-600" />
	{/if}
	{#if title}
		<p class="text-base font-bold text-gray-900 dark:text-white">{title}</p>
		<p class="mt-1 text-sm text-gray-500 dark:text-gray-400">{message}</p>
	{:else}
		<p class={['text-gray-500 dark:text-gray-400', Icon && 'mt-2 text-sm']}>{message}</p>
	{/if}
	{#if children}
		{@render children()}
	{/if}
</div>
